from datetime import datetime, timezone, timedelta
from typing import List, Optional
from models import Allocation, Status, Platform
from repository import ChannelRepository

# Custom Exceptions for clean error handling
class AllocationException(Exception):
    pass

class ValidationException(AllocationException):
    pass

class ConflictException(AllocationException):
    pass

class ResourceExhaustedException(AllocationException):
    pass

class CancelWindowExpiredException(AllocationException):
    pass

class ChannelAllocationService:
    """
    Business Logic Layer (Domain).
    New business rules can be added here without touching the API or Repository.
    Takes the repository and a clock function as dependencies (Dependency Injection),
    making it extremely easy to mock time during testing.
    """
    def __init__(self, repository: ChannelRepository, get_time_func=None):
        self.repository = repository
        # Dependency Injection for time - crucial for testing 5min/24h rules
        self.get_now = get_time_func if get_time_func else lambda: datetime.now(timezone.utc)

    def allocate(self, ad_id: str, platform_str: str) -> Allocation:
        # 1. Validation
        if not ad_id or not isinstance(ad_id, str):
            raise ValidationException("Valid ad_id string is required")
            
        try:
            platform = Platform(platform_str)
        except ValueError:
            valid_platforms = [p.value for p in Platform]
            raise ValidationException(f"Invalid platform. Allowed values: {', '.join(valid_platforms)}")

        # 2. Check for duplicate active allocation
        existing = self.repository.get_active_by_ad_and_platform(ad_id, platform)
        if existing:
            raise ConflictException("Active allocation already exists for this ad_id and platform")

        # 3. Get available channel
        channel_id = self.repository.get_available_channel_from_pool()
        if not channel_id:
            raise ResourceExhaustedException("No available channels in the pool")

        # 4. Create and save allocation
        now = self.get_now()
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

        allocation = self.repository.get_by_channel(channel_id)
        if not allocation or allocation.status != Status.ACTIVE:
            raise ValidationException("Channel is not currently active")

        now = self.get_now()
        # Apply 24h cooldown rule
        available_at = now + timedelta(hours=24)
        
        allocation.status = Status.FREED
        allocation.available_at = available_at
        self.repository.save(allocation)
        
        return allocation

    def cancel(self, channel_id: str) -> Allocation:
        if not channel_id:
            raise ValidationException("Channel parameter is required")

        allocation = self.repository.get_by_channel(channel_id)
        if not allocation or allocation.status != Status.ACTIVE:
            raise ValidationException("Channel is not currently active")

        now = self.get_now()
        
        # Check cancel window (5 minutes inclusive)
        if now - allocation.allocated_at > timedelta(minutes=5):
            raise CancelWindowExpiredException("Cancel window of 5 minutes has expired")

        # Instant release rule
        allocation.status = Status.FREED
        allocation.available_at = now 
        self.repository.save(allocation)
        
        return allocation

    def get_active_allocations(self) -> List[Allocation]:
        return self.repository.get_all_active()