from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Using Enums to avoid magic strings and ensure type safety
class Platform(Enum):
    FB = 'fb'
    OB = 'ob'
    SNP = 'snp'
    GTAG = 'gtag'

class Status(Enum):
    ACTIVE = 'ACTIVE'
    FREED = 'FREED'
    CANCELED = 'CANCELED'

@dataclass
class Allocation:
    """
    Represents a single channel allocation record.
    Using dataclass for clean and readable entity definition.
    """
    channel_id: str
    ad_id: str
    platform: Platform
    status: Status
    allocated_at: datetime
    available_at: Optional[datetime] = None