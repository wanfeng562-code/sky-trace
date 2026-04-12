import logging


def configure_logging(level: str) -> None:
    """Configure root logging once for the backend service."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
