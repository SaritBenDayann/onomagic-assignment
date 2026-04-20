from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from models import Allocation, Status, Platform
from datetime import datetime

class ChannelRepository(ABC):
    """
    Abstract Class (Interface).
    """
    @abstractmethod
    def save(self, allocation: Allocation) -> None:
        pass

    @abstractmethod
    def get_by_channel(self, channel_id: str) -> Optional[Allocation]:
        pass
        
    @abstractmethod
    def get_active_by_ad_and_platform(self, ad_id: str, platform: Platform) -> Optional[Allocation]:
        pass
        
    @abstractmethod
    def get_all_active(self) -> List[Allocation]:
        pass

    @abstractmethod
    def get_available_channel_from_pool(self, current_time: datetime) -> Optional[str]:
        pass


class InMemoryChannelRepository(ChannelRepository):
    """
    In-memory implementation using dictionaries.
    Provides O(1) access time for channel lookups.
    """
    def __init__(self):
        # The main data store: channel_id -> Allocation object
        self._storage: Dict[str, Allocation] = {}
        # Simple counter to track the next available 'onoX' ID
        self._next_channel_num = 1
        self._max_channels = 99999

    def save(self, allocation: Allocation) -> None:
        """Saves or updates an allocation in the dictionary."""
        self._storage[allocation.channel_id] = allocation

    def get_by_channel(self, channel_id: str) -> Optional[Allocation]:
        """Returns the allocation if it exists, otherwise None."""
        return self._storage.get(channel_id)
        
    def get_active_by_ad_and_platform(self, ad_id: str, platform: Platform) -> Optional[Allocation]:
        """
        An (ad_id, platform) pair can have at most one active allocation.
        Iterates through storage to find a match.
        """
        for alloc in self._storage.values():
            if alloc.status == Status.ACTIVE and \
               alloc.ad_id == ad_id and \
               alloc.platform == platform:
                return alloc
        return None
        
    def get_all_active(self) -> List[Allocation]:
        """Returns a list of all currently active allocations."""
        return [alloc for alloc in self._storage.values() if alloc.status == Status.ACTIVE]
        
    def get_available_channel_from_pool(self, current_time: datetime) -> Optional[str]:
        """
        Strategy:
        1. Look for a FREED channel that finished its 24h cooldown.
        2. If none, generate a new 'onoX' ID if within limits.
        """

        # 1. Search for reusable channels
        for ch_id, alloc in self._storage.items():
            if alloc.status == Status.FREED and \
               alloc.available_at and \
               alloc.available_at <= current_time:
                return ch_id

        # 2. Generate new channel if possible
        if self._next_channel_num <= self._max_channels:
            new_id = f"ono{self._next_channel_num}"
            self._next_channel_num += 1
            return new_id

        return None