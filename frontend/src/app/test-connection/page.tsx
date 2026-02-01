'use client';

import { useState } from 'react';
import { fetchWithAuth } from '@/services/api';

export default function TestConnectionPage() {
  const [status, setStatus] = useState<string>('Idle');
  const [response, setResponse] = useState<any>(null);

  const testConnection = async () => {
    setStatus('Testing...');
    setResponse(null);
    try {
      // The backend mounts A2A at /a2a/pikar_ai
      // We try to fetch the agent card
      const res = await fetchWithAuth('/a2a/pikar_ai/.well-known/agent.json');
      const data = await res.json();
      setResponse(data);
      setStatus('Success');
    } catch (error: any) {
      console.error(error);
      setStatus(`Error: ${error.message}`);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Backend Connection Test</h1>
      
      <p className="mb-4 text-gray-600">
        This page tests the connection between the Next.js Frontend and the FastAPI Backend.
        It attempts to fetch the Agent Card from <code>/a2a/pikar_ai/.well-known/agent.json</code>.
      </p>

      <div className="mb-4">
        <button 
          onClick={testConnection}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition cursor-pointer"
        >
          Ping Backend Agent
        </button>
      </div>

      <div className="border p-4 rounded bg-gray-50 dark:bg-gray-900">
        <p className="font-semibold">Status: <span className={status === 'Success' ? 'text-green-600' : status.startsWith('Error') ? 'text-red-600' : 'text-gray-600'}>{status}</span></p>
        
        {response && (
          <div className="mt-4">
            <h2 className="text-sm font-semibold mb-2">Response Data:</h2>
            <pre className="bg-black text-green-400 p-4 rounded overflow-auto text-xs font-mono">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
