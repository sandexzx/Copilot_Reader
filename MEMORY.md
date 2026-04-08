# Copilot Reader — Project Memory

> Обновляется по мере хода разработки. При старте новой сессии — читай этот файл первым.

## 🎯 Цель проекта

Утилита для мониторинга сессий GitHub Copilot CLI в реальном времени.
Парсит `events.jsonl` из `~/.copilot/session-state/`, показывает все операции нейросети в красивом веб-интерфейсе.

## 🏗️ Стек

- **Backend**: Python 3.12 + FastAPI + WebSocket
- **Frontend**: SvelteKit + Svelte 5
- **Runtime**: Bun (для фронтенда)
- **File watching**: inotify (Linux) через watchdog или нативный Python
- **Дизайн**: Тёмная тема (стиль выбирается на этапе демо)

## 📁 Структура данных Copilot CLI

### Расположение
- Сессии: `~/.copilot/session-state/<UUID>/`
- Глобальная БД: `~/.copilot/session-store.db` (SQLite, 3.6MB)

### Файлы в каждой сессии
- `events.jsonl` — основной лог (append-only, 1.7KB-8MB, avg ~1.5MB)
- `workspace.yaml` — метадата (id, cwd, summary, created/updated_at)
- `session.db` — SQLite scratch (todos, custom tables)
- `vscode.metadata.json` — первое сообщение пользователя
- `inuse.<PID>.lock` — ТОЛЬКО у активных сессий (содержит PID)
- `checkpoints/` — снапшоты контекста
- `rewind-snapshots/` — git-снапшоты для отката

### Формат events.jsonl
Каждая строка — JSON:
```json
{
  "type": "event.type.name",
  "data": { /* payload */ },
  "id": "uuid-v4",
  "timestamp": "2026-03-30T16:31:41.820Z",
  "parentId": "uuid-v4 | null"
}
```

### 24 типа событий
| Тип | Описание |
|-----|----------|
| `session.start` | Старт сессии (sessionId, version, cwd) |
| `session.shutdown` | Завершение (токены, стоимость, изменённые файлы) |
| `session.resume` | Возобновление сессии |
| `session.model_change` | Смена модели |
| `session.info` | Инфо-сообщения |
| `session.error` | Ошибки сессии |
| `session.context_changed` | Смена cwd/branch |
| `session.plan_changed` | Изменение plan.md |
| `session.workspace_file_changed` | Изменение файла workspace |
| `session.compaction_start/complete` | Компрессия контекста |
| `user.message` | Сообщение пользователя (content + transformedContent) |
| `assistant.turn_start/end` | Начало/конец хода ассистента |
| `assistant.message` | Ответ ассистента (текст + toolRequests + reasoning) |
| `tool.execution_start` | Запуск инструмента (toolName, arguments) |
| `tool.execution_complete` | Результат инструмента (result, success) |
| `hook.start/end` | Пост-хуки (postToolUse) |
| `subagent.selected` | Маршрутизация к кастом-агенту |
| `subagent.started/completed/failed` | Жизненный цикл суб-агента |
| `system.notification` | Системные уведомления |
| `abort` | Прерывание пользователем |

### Определение активной сессии
1. **Lock-файл** `inuse.<PID>.lock` — 100% надёжность
2. Валидация PID через `kill -0 <PID>` или `/proc/<PID>/status`
3. Нет события `session.shutdown` ≠ активна (может быть crashed)

### Ключевые особенности
- `parentId` формирует linked list (не дерево), глубина до 427
- `turnId` — строка, сбрасывается в "0" при каждом `user.message`
- `tool.execution_complete` НЕ содержит `toolName` — нужна корреляция по `toolCallId`
- 34 tool calls начаты но не завершены (аборты/крэши)
- Burst-writes: до 7 событий в одну миллисекунду
- Timestamps: ISO 8601 UTC, миллисекундная точность

## 📊 Статистика (136 сессий)
- 114 с events.jsonl, 22 пустых
- Средний размер: 1.5MB, 576 строк
- Макс: 8MB, 3490 строк
- Всего данных: 167MB

## 🎨 Дизайн-решение

**Выбран: Demo A — IDE-стиль (VS Code/GitHub Dark)**
- Файл-референс: `demos/demo-a-ide/index.html`
- Лог-вьюер, монопространственный шрифт, цветные бейджи событий
- Дерево вложенности (Tree View), табы
- Анимации fade-in для событий, пульсирующий LIVE индикатор

**Фидбек на доработку:**
- Левый сайдбар с навигацией по сессиям — сделать визуально красивее
- Блоки статистики — сделать более стильными/современными

## 🔄 Текущий статус

### Фаза: Реализация
- [x] Создать два варианта тёмной темы (Demo A и Demo B)
- [x] Пользователь выбирает → **Demo A (IDE-стиль)**
- [x] Создать план (plan.yaml с DAG) — 18 задач, 30 зависимостей
- [ ] Реализация MVP (следующий шаг: task-001 + task-002 параллельно)

### Приоритетные фичи (от пользователя)
1. Realtime streaming событий (tail -f стиль)
2. Дерево вложенности (agent → tool → sub-agent)
3. Статистика по сессии (токены, модели, стоимость)
4. Список всех сессий с фильтрацией
5. Интерактивная навигация по истории событий

## 💡 Решения и заметки
- MEMORY.md обновляется по мере хода разработки
- При крэше контекста — начинай с чтения этого файла
- Rate limit 320K output tokens/day — константа захардкожена во фронтенде (`OUTPUT_RATE_LIMIT`), не приходит с бэкенда
- `dailyUsageStore` — singleton, polling каждые 30с + debounced 5с после WS-событий. Init идемпотентен.
- Процент rate limit теперь отображается в 3 местах: Header (badge), Sidebar DailyUsage (прогресс-бар), StatsPanel (Output bar + legend)

Закрыл 11 и 12 задачки.

## 📝 Session Log

### 2026-04-08
- Добавлен rate limit индикатор в Header (pill-badge с прогресс-баром, цветовая кодировка по порогам)
- Добавлен rate limit прогресс-бар в DailyUsage sidebar (полноширинная полоса с пульсирующим свечением при >80%)
- Коммит: `feat: add prominent rate limit indicators to header and sidebar`