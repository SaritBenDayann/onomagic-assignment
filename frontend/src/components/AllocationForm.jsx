// src/components/AllocationForm.jsx
import React, { useState } from 'react';
import { apiClient } from '../apiClient';

export default function AllocationForm({ onAllocationSuccess }) {
    const [adId, setAdId] = useState('');
    const [platform, setPlatform] = useState('fb');
    
    // UI States
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Basic required-field validation
        if (!adId.trim()) {
            setError("Ad ID is required.");
            return;
        }

        setIsLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const result = await apiClient.allocateChannel(adId, platform);
            setSuccessMessage(`Successfully allocated channel: ${result.channel}`);
            setAdId(''); // Reset form
            
            // Notify parent to refresh the active channels table
            if (onAllocationSuccess) {
                onAllocationSuccess();
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="card">
            <h2>Allocate Channel</h2>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label>Ad ID:</label>
                    <input 
                        type="text" 
                        value={adId} 
                        onChange={(e) => setAdId(e.target.value)} 
                        placeholder="Enter Ad ID"
                        disabled={isLoading}
                    />
                </div>
                <div className="form-group">
                    <label>Platform (fb, ob, snp, gtag):</label>
                    <input 
                        type="text" 
                        value={platform} 
                        onChange={(e) => setPlatform(e.target.value)} 
                        placeholder="e.g. fb"
                        disabled={isLoading}
                    />
                </div>
                
                <button type="submit" disabled={isLoading}>
                    {isLoading ? 'Allocating...' : 'Allocate'}
                </button>
            </form>

            {/* UI Feedback States */}
            {error && <div className="error-message">Error: {error}</div>}
            {successMessage && <div className="success-message">{successMessage}</div>}
        </div>
    );
}