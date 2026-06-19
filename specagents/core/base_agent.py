"""
Agent interface. Every source agent (Intel ARK today, others later) implements
the same two steps so the registry/UI can run them uniformly:

    fetch_raw()  -> list of raw source rows (dicts)
    to_records() -> list of flat SpecRecords (map + derive)

run() just chains them. Keeping the seam here means the unverified,
network-dependent part (fetch_raw) is swappable and testable in isolation.
"""

from abc import ABC, abstractmethod
from typing import List
from .schema import SpecRecord


class Agent(ABC):
    #: short, unique id used by the registry/UI (e.g. "intel_ark")
    name: str = "agent"

    @abstractmethod
    def fetch_raw(self, **kwargs) -> List[dict]:
        """Return raw source rows, one dict per product. No normalization here."""
        raise NotImplementedError

    @abstractmethod
    def to_records(self, raw_rows: List[dict]) -> List[SpecRecord]:
        """Map raw rows onto SpecRecord + apply derivation rules."""
        raise NotImplementedError

    def run(self, **kwargs) -> List[SpecRecord]:
        """Fetch then normalize. kwargs pass through to fetch_raw (e.g. sample=True)."""
        return self.to_records(self.fetch_raw(**kwargs))
