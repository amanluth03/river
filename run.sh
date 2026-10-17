#!/usr/bin/env bash
# One command to set up and start the peer benchmark.
#   ./run.sh         install what's needed, then open the review page at http://127.0.0.1:8000
#   ./run.sh test    run the test suite (offline)
set -euo pipefail
cd "$(dirname "$0")"

# 1. uv installs the right Python and every dependency (https://docs.astral.sh/uv/).
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (Python package manager)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ "${1:-}" = "test" ]; then
  exec uv run pytest -q
fi

# 2. The SEC requires a name and contact email on every request (SEC_USER_AGENT in .env).
if [ ! -f .env ]; then
  cp .env.example .env
fi
if ! grep -Eq '^SEC_USER_AGENT=.*@' .env; then
  read -r -p "Your name and email for the SEC User-Agent (e.g. Jane Doe jane@firm.com): " agent
  printf 'SEC_USER_AGENT="%s"\n' "$agent" >> .env
fi

# 3. Port 8000 must be free.
if lsof -ti :8000 >/dev/null 2>&1; then
  echo "Port 8000 is already in use. Stop whatever is using it (or an earlier ./run.sh) and try again."
  exit 1
fi

# 4. Start the page. On the first visit press Run once; stop with Ctrl+C.
exec uv run benchmark
