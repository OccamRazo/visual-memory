#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements-egvqa-pilot.txt
.venv/bin/python - <<'PY'
import torch
print('torch', torch.__version__, 'CUDA', torch.version.cuda)
if not torch.cuda.is_available():
    raise SystemExit('CUDA unavailable: model validation not run')
print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory)
PY
