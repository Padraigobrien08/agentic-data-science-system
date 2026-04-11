"""Run ``python -m backend.worker`` to process queued analysis runs."""

from __future__ import annotations

import logging
import sys

from backend.config.settings import get_settings
from backend.db.session import SessionLocal
from backend.worker.loop import run_forever


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    settings = get_settings()
    run_forever(SessionLocal, poll_interval_s=settings.worker_poll_interval_s)


if __name__ == "__main__":
    main()
