// src/components/ActiveChannelsTable.jsx
import React, { useState } from 'react';
import { apiClient } from '../apiClient';

export default function ActiveChannelsTable({ allocations, onRefresh }) {
    const [actionLoading, setActionLoading] = useState(null); // Tracks which channel is being modified
    const [actionError, setActionError] = useState(null);

    const handleAction = async (channelId, actionType) => {
        setActionLoading(channelId);
        setActionError(null);
        
        try {
            if (actionType === 'free') {
                await apiClient.freeChannel(channelId);
            } else if (actionType === 'cancel') {
                await apiClient.cancelAllocation(channelId);
            }
            // Refresh table data after successful action
            onRefresh();
        } catch (err) {
            setActionError(`Failed to ${actionType} ${channelId}: ${err.message}`);
        } finally {
            setActionLoading(null);
        }
    };

    if (allocations.length === 0) {
        return <p>No active allocations found.</p>;
    }

    return (
        <div className="card">
            <h2>Active Allocations</h2>
            {actionError && <div className="error-message">{actionError}</div>}
            
            <table className="data-table">
                <thead>
                    <tr>
                        <th>Channel</th>
                        <th>Ad ID</th>
                        <th>Platform</th>
                        <th>Allocated At</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {allocations.map((alloc) => (
                        <tr key={alloc.channel}>
                            <td><strong>{alloc.channel}</strong></td>
                            <td>{alloc.ad_id}</td>
                            <td>{alloc.platform}</td>
                            <td>{new Date(alloc.allocated_at).toLocaleString()}</td>
                            <td>
                                <button 
                                    onClick={() => handleAction(alloc.channel, 'free')}
                                    disabled={actionLoading === alloc.channel}
                                    className="btn-warning"
                                >
                                    Free
                                </button>
                                <button 
                                    onClick={() => handleAction(alloc.channel, 'cancel')}
                                    disabled={actionLoading === alloc.channel}
                                    className="btn-danger"
                                    style={{ marginLeft: '8px' }}
                                >
                                    Cancel
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}