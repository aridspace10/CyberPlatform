"""Run the API against the isolated working directory supplied by Playwright."""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from db import seed  # noqa: E402

seed.CONFIG_FOLDER = str(BACKEND / "game" / "configs")
os.environ["CYBERPLATFORM_CORS_ORIGINS"] = "http://127.0.0.1:5174"
os.environ["CYBERPLATFORM_JWT_SECRET"] = "e2e-only-local-secret-not-for-deployment"

from main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
