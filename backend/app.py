from flask import Flask, request, jsonify
from flask_cors import CORS
from repository import InMemoryChannelRepository
from service import (
    ChannelAllocationService, 
    ValidationException, 
    ConflictException, 
    ResourceExhaustedException, 
    CancelWindowExpiredException
)

app = Flask(__name__)
CORS(app)

# Initialize our architecture layers
repo = InMemoryChannelRepository()
service = ChannelAllocationService(repo)

# Helper function to return consistent error messages
def handle_error(message, status_code):
    return jsonify({"error": str(message)}), status_code

# API Endpoints (Controllers)

@app.route('/api/allocate', methods=['POST'])
def allocate_channel():
    """Handles channel allocation requests."""
    data = request.get_json(silent=True) or {}
    ad_id = data.get('ad_id')
    platform = data.get('platform')

    try:
        allocation = service.allocate(ad_id, platform)
        return jsonify({
            "ad_id": allocation.ad_id,
            "platform": allocation.platform.value,
            "channel": allocation.channel_id,
            "allocated_at": allocation.allocated_at.isoformat()
        }), 201
        
    except ValidationException as e:
        return handle_error(e, 400) # Bad Request
    except ConflictException as e:
        return handle_error(e, 409) # Conflict (duplicate active)
    except ResourceExhaustedException as e:
        return handle_error(e, 404) # Not Found (no free channels left)

@app.route('/api/free', methods=['POST'])
def free_channel():
    """Handles freeing an active channel to start its 24h cooldown."""
    data = request.get_json(silent=True) or {}
    channel = data.get('channel')

    try:
        allocation = service.free(channel)
        return jsonify({
            "channel": allocation.channel_id,
            "freed_at": service.get_now().isoformat(),
            "available_at": allocation.available_at.isoformat()
        }), 200
        
    except ValidationException as e:
        return handle_error(e, 400)

@app.route('/api/cancel', methods=['POST'])
def cancel_allocation():
    """Handles canceling an allocation if it's within the 5-minute window."""
    data = request.get_json(silent=True) or {}
    channel = data.get('channel')

    try:
        allocation = service.cancel(channel)
        return jsonify({"message": f"Allocation for {allocation.channel_id} canceled successfully"}), 200
        
    except ValidationException as e:
        return handle_error(e, 400)
    except CancelWindowExpiredException as e:
        return handle_error(e, 400) # Bad Request for expired window

@app.route('/api/allocations/active', methods=['GET'])
def get_active_allocations():
    """Returns a list of all currently active allocations."""
    active_allocations = service.get_active_allocations()
    
    # Map objects to JSON dictionaries
    result = [{
        "ad_id": a.ad_id,
        "platform": a.platform.value,
        "channel": a.channel_id,
        "allocated_at": a.allocated_at.isoformat()
    } for a in active_allocations]
    
    return jsonify({"active_allocations": result}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)