"""AI proxy endpoints for AITunnel integration."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ai", tags=["ai"])

AITUNNEL_BASE = "https://api.aitunnel.ru"
MODELS_URL = f"{AITUNNEL_BASE}/public/aitunnel/models/chat"
CHAT_URL = f"{AITUNNEL_BASE}/v1/chat/completions"

TRANSLATION_PROMPT = (
    "Ты — профессиональный технический переводчик. "
    "Переведи следующий текст на русский язык. "
    "Сохрани форматирование, переносы строк и структуру. "
    "Технические термины (имена функций, переменных, путей к файлам, команды) оставь без перевода. "
    "Не добавляй пояснений, просто выдай перевод."
)


class TranslateRequest(BaseModel):
    text: str
    api_key: str
    model: str = "gpt-4.1"


@router.get("/models")
async def get_models():
    """Fetch available chat models from AITunnel."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(MODELS_URL)
            resp.raise_for_status()
            data = resp.json()
            models = [
                {"id": model_id, "provider": info.get("provider", "")}
                for model_id, info in data.items()
                if isinstance(info, dict)
            ]
            models.sort(key=lambda m: m["id"])
            return {"models": models}
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Failed to fetch models: {e}") from e


@router.post("/translate")
async def translate(req: TranslateRequest):
    """Translate text using AITunnel chat completion."""
    if not req.api_key:
        raise HTTPException(400, "API key is required")

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                CHAT_URL,
                headers={
                    "Authorization": f"Bearer {req.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": req.model,
                    "messages": [
                        {"role": "system", "content": TRANSLATION_PROMPT},
                        {"role": "user", "content": req.text},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "translation": content,
                "cost_rub": usage.get("cost_rub"),
                "balance": usage.get("balance"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            }
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:300] if e.response else str(e)
            raise HTTPException(e.response.status_code, f"AITunnel error: {detail}") from e
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Request failed: {e}") from e
