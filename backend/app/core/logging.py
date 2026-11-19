import logging


def setup_logging(level: str) -> None:
    """Configure root logging once, at application start."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
