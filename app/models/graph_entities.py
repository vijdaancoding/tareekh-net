from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PartyMembership:
    name: str
    abbreviation: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    role: Optional[str] = None


@dataclass
class PositionHeld:
    title: str
    level: str  # federal | provincial
    branch: str  # executive | legislative | judicial
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    constituency: Optional[str] = None


@dataclass
class ExtractedEntities:
    politician_id: str
    name: str
    born: Optional[str]
    bio: str
    embedding: list[float] = field(default_factory=list)
    parties: list[PartyMembership] = field(default_factory=list)
    positions: list[PositionHeld] = field(default_factory=list)
    source_url: str = ""
