"""Convenience entry-point that reads APP_HOST / APP_PORT from .env.

Usage (from the server/ directory):

    python run.py              # honours APP_HOST and APP_PORT in .env
    python run.py --reload     # pass any extra uvicorn flags after --
"""
import sys

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    extra_args = sys.argv[1:]  # forward any extra flags (e.g. --reload)
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload="--reload" in extra_args,
        log_level=settings.log_level.lower(),
    )
