import logging
import os

def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Reduce noisy logs if desired
    if os.getenv("HTTPX_LOG_LEVEL"):
        logging.getLogger("httpx").setLevel(os.getenv("HTTPX_LOG_LEVEL"))
