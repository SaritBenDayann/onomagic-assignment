// src/apiClient.js

const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Helper function to handle fetch responses and error parsing consistently.
 */
async function handleResponse(response) {
    const contentType = response.headers.get("content-type");
    let data;
    if (contentType && contentType.indexOf("application/json") !== -1) {
        data = await response.json();
    }
    
    if (!response.ok) {
        // Throw the error message returned from our Flask backend
        throw new Error((data && data.error) || `HTTP Error ${response.status}`);
    }
    return data;
}

export const apiClient = {
    /**
     * Allocates a new channel for a given ad and platform.
     */
    async allocateChannel(adId, platform) {
        const response = await fetch(`${API_BASE_URL}/allocate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ad_id: adId, platform })
        });
        return handleResponse(response);
    },

    /**
     * Frees an active channel and triggers the 24h cooldown.
     */
    async freeChannel(channel) {
        const response = await fetch(`${API_BASE_URL}/free`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel })
        });
        return handleResponse(response);
    },

    /**
     * Cancels an allocation if within the 5-minute window.
     */
    async cancelAllocation(channel) {
        const response = await fetch(`${API_BASE_URL}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel })
        });
        return handleResponse(response);
    },

    /**
     * Retrieves all currently active allocations.
     */
    async getActiveAllocations() {
        const response = await fetch(`${API_BASE_URL}/allocations/active`, {
            method: 'GET'
        });
        return handleResponse(response);
    }
};