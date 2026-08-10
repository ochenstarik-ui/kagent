import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class EffectLedger:
    """
    In-memory effect ledger for idempotency (ADR-0010).
    A full implementation would persist this to a database,
    but this minimal version keeps it in memory per pipeline run.
    """
    def __init__(self):
        self._effects: dict[str, Any] = {}

    def record_effect(self, key: str, result: Any) -> None:
        """Records the result of a side effect."""
        logger.info(f"Recording effect for key: {key}")
        self._effects[key] = result

    def get_effect(self, key: str) -> Optional[Any]:
        """Retrieves a previously recorded side effect if it exists."""
        if key in self._effects:
            logger.info(f"Effect found for key: {key}")
            return self._effects[key]
        return None
