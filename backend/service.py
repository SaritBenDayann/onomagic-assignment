import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from models import Allocation, Status, Platform
from repository import ChannelRepository

# Custom Exceptions
class AllocationException(Exception): pass
class ValidationException(AllocationException): pass
class ConflictException(AllocationException): pass
class ResourceExhaustedException(AllocationException): pass
class CancelWindowExpiredException(AllocationException): pass

class ChannelAllocationService:
    def __init__(self, repository: ChannelRepository, get_time_func=None):
        self.repository = repository
        self.get_now = get_time_func if get_time_func else lambda: datetime.now(timezone.utc)
        
        # Lock to ensure atomic operations across read-modify-write transactions
        self._allocation_lock = threading.Lock()

    def allocate(self, ad_id: str, platform_str: str) -> Allocation:
        # Validation happens OUTSIDE the lock to avoid blocking other threads for bad requests
        if not ad_id or not isinstance(ad_id, str):
            raise ValidationException("Valid ad_id string is required")
            
        try:
            platform = Platform(platform_str)
        except ValueError:
            valid_platforms = [p.value for p in Platform]
            raise ValidationException(f"Invalid platform. Allowed values: {', '.join(valid_platforms)}")

        with self._allocation_lock:
            # Check for duplicate active allocation
            existing = self.repository.get_active_by_ad_and_platform(ad_id, platform)
            if existing:
                raise ConflictException("Active allocation already exists for this ad_id and platform")

            now = self.get_now()

            # Get available channel
            channel_id = self.repository.get_available_channel_from_pool(now)
            if not channel_id:
                raise ResourceExhaustedException("No available channels in the pool")

            # Create and save allocation within the same lock
            new_allocation = Allocation(
                channel_id=channel_id,
                ad_id=ad_id,
                platform=platform,
                status=Status.ACTIVE,
                allocated_at=now
            )
            self.repository.save(new_allocation)
            
        return new_allocation

    def free(self, channel_id: str) -> Allocation:
        if not channel_id:
            raise ValidationException("Channel parameter is required")

        # Wrapping free logic to prevent race conditions during state transitions
        with self._allocation_lock:
            allocation = self.repository.get_by_channel(channel_id)
            if not allocation or allocation.status != Status.ACTIVE:
                raise ValidationException("Channel is not currently active")

            now = self.get_now()
            available_at = now + timedelta(hours=24)
            
            allocation.status = Status.FREED
            allocation.available_at = available_at
            self.repository.save(allocation)
            
        return allocation

    def cancel(self, channel_id: str) -> Allocation:
        if not channel_id:
            raise ValidationException("Channel parameter is required")

        # Wrapping cancel logic
        with self._allocation_lock:
            allocation = self.repository.get_by_channel(channel_id)
            if not allocation or allocation.status != Status.ACTIVE:
                raise ValidationException("Channel is not currently active")

            now = self.get_now()
            
            if now - allocation.allocated_at > timedelta(minutes=5):
                raise CancelWindowExpiredException("Cancel window of 5 minutes has expired")

            allocation.status = Status.FREED
            allocation.available_at = now 
            self.repository.save(allocation)
            
        return allocation

    def get_active_allocations(self) -> List[Allocation]:
        with self._allocation_lock:
            return self.repository.get_all_active()