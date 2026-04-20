import pytest
from datetime import datetime, timezone, timedelta
from app import app, repo
from service import ChannelAllocationService, CancelWindowExpiredException, ConflictException, ValidationException, ResourceExhaustedException
from repository import InMemoryChannelRepository
import concurrent.futures

# TEST FIXTURES & MOCKS

class MockClock:
    """A fake clock to easily test 5-minute and 24-hour rules without waiting."""
    def __init__(self):
        # Start time is fixed to avoid random test failures
        self.current_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
    def __call__(self):
        return self.current_time
        
    def advance(self, minutes=0, hours=0, seconds=0):
        self.current_time += timedelta(minutes=minutes, hours=hours, seconds=seconds)

@pytest.fixture
def service_env():
    """Provides a fresh Service and Repository with a mocked clock for Unit Tests."""
    test_repo = InMemoryChannelRepository()
    # Limit max channels to 1 to test exhaustion and cooldown blocks
    test_repo._max_channels = 1 
    clock = MockClock()
    test_service = ChannelAllocationService(test_repo, get_time_func=clock)
    return test_service, clock

@pytest.fixture
def client():
    """Provides a Flask test client for API Integration Tests."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Reset the global in-memory DB before each API test
        repo._storage.clear()
        repo._next_channel_num = 1
        yield client

# UNIT TESTS (Service Layer & Business Rules)

def test_allocate_success_path(service_env):
    """Test: allocate success path"""
    service, clock = service_env
    allocation = service.allocate("ad_123", "fb")
    
    assert allocation.channel_id == "ono1"
    assert allocation.status.value == "ACTIVE"
    assert allocation.ad_id == "ad_123"

def test_duplicate_active_behavior(service_env):
    """Test: duplicate active (ad_id, platform) behavior blocks allocation"""
    service, clock = service_env
    # First allocation succeeds
    service.allocate("ad_123", "fb")
    
    # Second allocation with same pair should raise ConflictException
    with pytest.raises(ConflictException):
        service.allocate("ad_123", "fb")

def test_free_starts_cooldown_and_blocks_reallocation(service_env):
    """Test: free starts cooldown and sets available_at. Reallocation blocked during cooldown."""
    service, clock = service_env
    allocation = service.allocate("ad_123", "fb")
    
    # Free the channel
    freed_allocation = service.free(allocation.channel_id)
    assert freed_allocation.status.value == "FREED"
    
    # Verify available_at is exactly 24 hours from now
    expected_available = clock() + timedelta(hours=24)
    assert freed_allocation.available_at == expected_available
    
    # Try to reallocate immediately (pool is exhausted because _max_channels is 1)
    from service import ResourceExhaustedException
    with pytest.raises(ResourceExhaustedException):
        service.allocate("ad_999", "ob")
        
    # Advance clock by 24 hours + 1 minute (cooldown passed)
    clock.advance(hours=24, minutes=1)
    
    # Now reallocation should succeed and reuse 'ono1'
    new_allocation = service.allocate("ad_999", "ob")
    assert new_allocation.channel_id == "ono1"

def test_cancel_within_5_minutes_succeeds(service_env):
    """Test: cancel within 5 minutes succeeds and frees immediately without cooldown."""
    service, clock = service_env
    allocation = service.allocate("ad_123", "fb")
    
    # Advance clock by 4 minutes
    clock.advance(minutes=4)
    
    canceled_allocation = service.cancel(allocation.channel_id)
    assert canceled_allocation.status.value == "FREED"
    # Available time should be the EXACT time of cancellation (immediate)
    assert canceled_allocation.available_at == clock()

def test_cancel_after_5_minutes_fails(service_env):
    """Test: cancel after 5 minutes fails with Window Expired Error."""
    service, clock = service_env
    allocation = service.allocate("ad_123", "fb")
    
    # Advance clock by 6 minutes
    clock.advance(minutes=6)
    
    with pytest.raises(CancelWindowExpiredException):
        service.cancel(allocation.channel_id)

# INTEGRATION TESTS (API Layer & Status Codes)

def test_api_platform_validation_failure(client):
    """Test: platform validation failure returns 400 Bad Request."""
    response = client.post('/api/allocate', json={
        "ad_id": "ad_123",
        "platform": "twitter"  # Invalid platform
    })
    assert response.status_code == 400
    assert "Invalid platform" in response.get_json()['error']

def test_api_allocate_and_get_active(client):
    """Integration: Test creating an allocation and retrieving it."""
    # 1. Allocate
    post_res = client.post('/api/allocate', json={"ad_id": "ad_1", "platform": "ob"})
    assert post_res.status_code == 201
    
    # 2. Get Active
    get_res = client.get('/api/allocations/active')
    assert get_res.status_code == 200
    data = get_res.get_json()
    
    assert len(data['active_allocations']) == 1
    assert data['active_allocations'][0]['ad_id'] == "ad_1"
    assert data['active_allocations'][0]['platform'] == "ob"

# EDGE CASES & BOUNDARY TESTS

def test_cancel_exact_boundary_5_minutes(service_env):
    """Cancel at 5 minutes (inclusive) should succeed."""
    service, clock = service_env
    allocation = service.allocate("ad_boundary", "fb")
    
    # Advance exactly 5 minutes (0 to 5 is inclusive according to requirements)
    clock.advance(minutes=5)
    
    canceled = service.cancel(allocation.channel_id)
    assert canceled.status.value == "FREED"

def test_free_inactive_channel_fails(service_env):
    """Trying to free a channel that doesn't exist or is already freed."""
    service, clock = service_env
    
    # Non-existent channel
    with pytest.raises(ValidationException):
        service.free("ono_fake_999")
        
    # Already freed channel
    allocation = service.allocate("ad_123", "fb")
    service.free(allocation.channel_id)
    
    # Try to free it again
    with pytest.raises(ValidationException):
        service.free(allocation.channel_id)

def test_allocate_pool_exhaustion(service_env):
    """Pool exhaustion returns 404 (ResourceExhausted) immediately."""
    service, clock = service_env
    # The fixture sets _max_channels = 1
    service.allocate("ad_1", "gtag")
    
    # Pool is now full, trying to allocate should instantly fail
    with pytest.raises(ResourceExhaustedException):
        service.allocate("ad_2", "ob")

def test_api_missing_parameters_validation(client):
    """API gracefully handles missing JSON body parameters."""
    # Missing platform
    res1 = client.post('/api/allocate', json={"ad_id": "ad_1"})
    assert res1.status_code == 400
    
    # Missing ad_id
    res2 = client.post('/api/allocate', json={"platform": "fb"})
    assert res2.status_code == 400
    
    # Empty body
    res3 = client.post('/api/allocate', json={})
    assert res3.status_code == 400

def test_allocate_empty_ad_id(service_env):
    """Empty string for ad_id should be rejected."""
    service, clock = service_env
    with pytest.raises(ValidationException):
        service.allocate("", "fb")

def test_allocate_wrong_data_type(service_env):
    """Integer instead of string for ad_id should fail validation."""
    service, clock = service_env
    with pytest.raises(ValidationException):
        service.allocate(12345, "fb")

def test_platform_case_sensitivity(service_env):
    """Platform must be an exact match (lowercase)."""
    service, clock = service_env
    with pytest.raises(ValidationException):
        service.allocate("ad_1", "FB") # Uppercase should be rejected

def test_api_no_body(client):
    """API gracefully handles completely missing JSON body."""
    response = client.post('/api/allocate') # No json payload at all
    assert response.status_code == 400

def test_allocate_same_ad_different_platform(service_env):
    """Same ad_id can have multiple active channels IF platforms differ."""
    service, clock = service_env
    service.repository._max_channels = 10 # Increase pool for this specific test
    
    alloc1 = service.allocate("ad_1", "fb")
    alloc2 = service.allocate("ad_1", "ob")
    
    assert alloc1.channel_id != alloc2.channel_id
    assert alloc1.status.value == "ACTIVE"
    assert alloc2.status.value == "ACTIVE"

def test_allocate_after_quick_cancel(service_env):
    """Canceling an allocation allows immediate reallocation of the same pair."""
    service, clock = service_env
    
    alloc1 = service.allocate("ad_1", "gtag")
    
    # Cancel it immediately
    service.cancel(alloc1.channel_id)
    
    # Should NOT raise ConflictException because the previous one is FREED
    alloc2 = service.allocate("ad_1", "gtag")
    
    # It should seamlessly reuse the exact same channel
    assert alloc2.channel_id == alloc1.channel_id

# CONCURRENCY TESTS

def test_cooldown_exact_boundary(service_env):
    """Cooldown exact boundary validation (down to the second)."""
    service, clock = service_env
    service.repository._max_channels = 1
    
    alloc1 = service.allocate("ad_1", "fb")
    service.free(alloc1.channel_id)
    
    # Advance 23 hours, 59 minutes, 59 seconds (1 second BEFORE cooldown ends)
    clock.advance(hours=23, minutes=59, seconds=59)
    from service import ResourceExhaustedException
    with pytest.raises(ResourceExhaustedException):
        service.allocate("ad_2", "ob")
        
    # Advance 1 more second (Exactly 24h)
    clock.advance(seconds=1)
    alloc2 = service.allocate("ad_2", "ob")
    
    # Now it should succeed and reuse the channel
    assert alloc2.channel_id == alloc1.channel_id

def test_cancel_after_free_fails(service_env):
    """Cannot cancel a channel that has already been freed."""
    service, clock = service_env
    alloc = service.allocate("ad_1", "fb")
    
    service.free(alloc.channel_id)
    
    # Trying to cancel a freed channel should fail
    with pytest.raises(ValidationException, match="not currently active"):
        service.cancel(alloc.channel_id)

def test_get_active_empty(service_env):
    """Get active allocations returns empty list when none exist."""
    service, clock = service_env
    active = service.get_active_allocations()
    assert active == []

def test_get_active_filtered(service_env):
    """Get active allocations safely filters out FREED and CANCELED statuses."""
    service, clock = service_env
    service.repository._max_channels = 5
    
    alloc1 = service.allocate("ad_1", "fb")
    alloc2 = service.allocate("ad_2", "ob")
    alloc3 = service.allocate("ad_3", "gtag")
    
    # Remove two of them from active status
    service.free(alloc1.channel_id)
    service.cancel(alloc2.channel_id)
    
    active = service.get_active_allocations()
    
    # Only alloc3 should remain
    assert len(active) == 1
    assert active[0].channel_id == alloc3.channel_id

def test_stress_concurrency_allocation(service_env):
    """BONUS: Stress/Concurrency test to ensure no double-allocations under load."""
    service, clock = service_env
    service.repository._max_channels = 100 
    
    def allocate_worker(worker_id):
        # Each thread tries to allocate a channel simultaneously
        return service.allocate(f"ad_stress_{worker_id}", "fb")
        
    # Fire 50 threads at the exact same time
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        worker_ids = list(range(50))
        # list() forces the threads to execute and wait for results
        results = list(executor.map(allocate_worker, worker_ids))
        
    active_allocations = service.get_active_allocations()
    
    # Verify exactly 50 channels were created
    assert len(active_allocations) == 50
    
    # Verify uniqueness (no two threads grabbed 'ono1' at the same time)
    channel_ids = set(a.channel_id for a in active_allocations)
    assert len(channel_ids) == 50


def test_cooldown_during_dst_forward(service_env):
    """
    Edge Case: Cooldown during DST jump (Spring).
    Ensures 24h cooldown is based on UTC/Absolute time, not local wall clock.
    """
    service, clock = service_env
    # Set clock to just before a DST jump (Example: March 28th)
    clock.current_time = datetime(2026, 3, 28, 1, 59, tzinfo=timezone.utc)
    
    alloc = service.allocate("ad_dst", "fb")
    service.free(alloc.channel_id)
    
    # Advance 23 hours - even if local time jumped, UTC remains linear
    clock.advance(hours=23)
    with pytest.raises(ResourceExhaustedException):
        service.allocate("ad_next", "ob")
        
    clock.advance(hours=1)
    # Success after exactly 24 UTC hours
    assert service.allocate("ad_next", "ob").channel_id == alloc.channel_id

def test_cooldown_over_new_year_midnight(service_env):
    """
    Edge Case: Allocation starts on New Year's Eve and ends on New Year's Day.
    Ensures date transition doesn't affect the 24h delta calculation.
    """
    service, clock = service_env
    # Dec 31st, 23:30
    clock.current_time = datetime(2025, 12, 31, 23, 30, tzinfo=timezone.utc)
    
    alloc = service.allocate("ad_nye", "gtag")
    service.free(alloc.channel_id)
    
    # Advance to Jan 1st, 23:29 (23h 59m later)
    clock.advance(hours=23, minutes=59)
    with pytest.raises(ResourceExhaustedException):
        service.allocate("ad_new_year", "fb")
        
    clock.advance(minutes=2)
    assert service.allocate("ad_new_year", "fb").channel_id == alloc.channel_id


def test_cancel_window_crosses_midnight(service_env):
    """
    Edge Case: Allocation at 23:58, Cancellation at 00:02.
    Ensures 5-minute window works across different days.
    """
    service, clock = service_env
    clock.current_time = datetime(2026, 5, 1, 23, 58, tzinfo=timezone.utc)
    
    alloc = service.allocate("ad_midnight", "snp")
    
    # Move clock 4 minutes forward to next day 00:02
    clock.advance(minutes=4)
    
    # Should still succeed
    canceled = service.cancel(alloc.channel_id)
    assert canceled.status.value == "FREED"