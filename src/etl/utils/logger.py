import logging
from prefect import get_run_logger

def _get_logger():
    try:
        return get_run_logger()
    except Exception:
        return logging.getLogger(__name__)
