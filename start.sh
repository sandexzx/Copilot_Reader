#!/usr/bin/env bash
# start.sh — Launch script for Copilot Reader
# Usage:
#   ./start.sh          Production mode: build frontend, serve via FastAPI
#   ./start.sh dev      Dev mode: Vite HMR + uvicorn --reload
#   ./start.sh --dev    Same as above
set -euo pipefail

# ─── Colour helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

open_chrome() {
    local url="$1"
    for browser in google-chrome google-chrome-stable chromium chromium-browser; do
        if command -v "$browser" &>/dev/null; then
            "$browser" "$url" &>/dev/null &
            info "Opening $url in Chrome …"
            return
        fi
    done
    warn "Chrome not found — open $url manually"
}

wait_and_open() {
    local url="$1"
    (until curl -s -o /dev/null "$url"; do sleep 1; done; open_chrome "$url") &
}

# ─── Resolve project root (directory containing this script) ─────────────────
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# ─── Dependency checks ──────────────────────────────────────────────────────
check_python() {
    local py=""
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            py="$candidate"
            break
        fi
    done
    if [[ -z "$py" ]]; then
        error "Python 3 is not installed. Please install Python 3.12 or later."
        exit 1
    fi

    local version
    version=$("$py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if (( major < 3 || (major == 3 && minor < 12) )); then
        error "Python 3.12+ is required (found $version). Please upgrade."
        exit 1
    fi
    info "Python $version ✓"
    PYTHON="$py"
}

check_bun() {
    # Bun is often installed in ~/.bun/bin and may not be in PATH
    if ! command -v bun &>/dev/null; then
        if [[ -x "$HOME/.bun/bin/bun" ]]; then
            export PATH="$HOME/.bun/bin:$PATH"
        else
            error "Bun is not installed. Install it from https://bun.sh"
            exit 1
        fi
    fi
    local bun_ver
    bun_ver=$(bun --version 2>/dev/null || echo "unknown")
    info "Bun $bun_ver ✓"
}

check_python
check_bun

# ─── Determine mode ─────────────────────────────────────────────────────────
MODE="production"
if [[ "${1:-}" == "dev" || "${1:-}" == "--dev" ]]; then
    MODE="dev"
fi

PORT="${COPILOT_READER_PORT:-8000}"
VITE_PORT=5173

# ─── Virtual environment setup ──────────────────────────────────────────────
VENV_DIR="$PROJECT_ROOT/.venv"

setup_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        info "Creating virtual environment in .venv …"
        "$PYTHON" -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    PYTHON="$VENV_DIR/bin/python"
    info "Virtual environment activated ✓"
}

setup_venv

# ─── Install Python dependencies ────────────────────────────────────────────
install_python_deps() {
    info "Installing Python dependencies …"
    if [[ -f backend/requirements.txt ]]; then
        "$PYTHON" -m pip install -q -r backend/requirements.txt
    elif [[ -f pyproject.toml ]]; then
        "$PYTHON" -m pip install -q -e .
    else
        warn "No requirements.txt or pyproject.toml found — skipping Python deps"
    fi
}

# ─── Install frontend dependencies ──────────────────────────────────────────
install_frontend_deps() {
    info "Installing frontend dependencies …"
    (cd frontend && bun install)
}

# ─── Build frontend ─────────────────────────────────────────────────────────
build_frontend() {
    info "Building frontend (SvelteKit static) …"
    (cd frontend && bun run build)
    if [[ ! -d frontend/build ]]; then
        error "Frontend build directory 'frontend/build' not found after build."
        exit 1
    fi
    info "Frontend build complete ✓"
}

# ═════════════════════════════════════════════════════════════════════════════
# DEV MODE
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$MODE" == "dev" ]]; then
    info "Starting in DEVELOPMENT mode …"

    install_python_deps
    install_frontend_deps

    # Kill all child processes on exit
    trap 'kill 0 2>/dev/null; exit 0' EXIT INT TERM

    # Start Vite dev server
    info "Starting Vite dev server on port $VITE_PORT …"
    (cd frontend && bun run dev --port "$VITE_PORT") &
    VITE_PID=$!

    # Start uvicorn with --reload
    info "Starting uvicorn (reload) on port $PORT …"
    "$PYTHON" -m uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --reload \
        --reload-dir backend &
    UVICORN_PID=$!

    info "──────────────────────────────────────────"
    info "  Frontend (Vite):  http://localhost:$VITE_PORT"
    info "  Backend  (API):   http://localhost:$PORT"
    info "  Press Ctrl+C to stop both servers"
    info "──────────────────────────────────────────"

    wait_and_open "http://localhost:$VITE_PORT"
    wait

# ═════════════════════════════════════════════════════════════════════════════
# PRODUCTION MODE
# ═════════════════════════════════════════════════════════════════════════════
else
    info "Starting in PRODUCTION mode …"

    install_python_deps
    install_frontend_deps
    build_frontend

    info "Starting uvicorn on port $PORT …"
    info "App available at http://localhost:$PORT"
    wait_and_open "http://localhost:$PORT"
    exec "$PYTHON" -m uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port "$PORT"
fi
