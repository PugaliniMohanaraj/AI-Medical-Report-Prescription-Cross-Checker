"""Patient timeline merge service (stub)."""

from typing import Any


class TimelineService:
    """Merge multiple visit records into a chronological patient timeline. Logic deferred."""

    async def merge_visits(self, visits: list[dict[str, Any]]) -> dict[str, Any]:
        raise NotImplementedError("Timeline merge is not implemented yet")
