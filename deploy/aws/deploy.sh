#!/usr/bin/env bash
# Deploy on the EC2 instance. Replaces Railway's build, preDeployCommand and
# health check. Usage, on the server:  ~/career-platform/deploy/aws/deploy.sh [git-ref]
set -euo pipefail
cd "$(dirname "$0")/../.."

ref="${1:-$(git rev-parse --abbrev-ref HEAD)}"
git fetch --prune origin
git checkout "$ref"
git pull --ff-only origin "$ref"

~/.local/bin/uv sync --frozen --no-dev
.venv/bin/python -m scripts.init_db
sudo systemctl restart career-platform

# /health proves the process is up; / proves it can read the database (503 if not).
for _ in $(seq 1 20); do
  health=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health || true)
  home=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/ || true)
  if [ "$health" = 200 ] && [ "$home" = 200 ]; then
    echo "Deployed $(git rev-parse --short HEAD): /health 200, / 200"
    exit 0
  fi
  sleep 1
done
echo "Deploy check failed: /health $health, / $home. Recent logs:" >&2
sudo journalctl -u career-platform -n 30 --no-pager >&2
exit 1
