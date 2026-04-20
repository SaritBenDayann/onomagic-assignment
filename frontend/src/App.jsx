// src/App.jsx
import React, { useState, useEffect } from 'react';
import AllocationForm from "./components/AllocationForm.jsx";
import ActiveChannelsTable from "./components/ActiveChannelsTable.jsx";
import { apiClient } from "./apiClient.js";
import './App.css';

export default function App() {
    const [allocations, setAllocations] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchActiveAllocations = async () => {
        setIsLoading(true);
        try {
            const data = await apiClient.getActiveAllocations();
            setAllocations(data.active_allocations || []);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch data on initial mount
    useEffect(() => {
        fetchActiveAllocations();
    }, []);

    return (
        <div className="container">
            <h1>Channel Allocation Manager</h1>
            
            <div className="grid">
                <AllocationForm onAllocationSuccess={fetchActiveAllocations} />
                
                <div className="table-container">
                    {isLoading && allocations.length === 0 ? (
                        <p>Loading active allocations...</p>
                    ) : error ? (
                        <div className="error-message">Failed to load: {error}</div>
                    ) : (
                        <ActiveChannelsTable 
                            allocations={allocations} 
                            onRefresh={fetchActiveAllocations} 
                        />
                    )}
                </div>
            </div>
        </div>
    );
}