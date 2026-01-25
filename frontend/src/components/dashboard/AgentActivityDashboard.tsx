import React from 'react'

export function AgentActivityDashboard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="font-semibold mb-2">Active Agents</h3>
        <p className="text-2xl font-bold text-indigo-600" aria-label="Active Agents Count">3</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="font-semibold mb-2">Tasks Completed</h3>
        <p className="text-2xl font-bold text-emerald-600" aria-label="Tasks Completed Count">12</p>
      </div>
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <h3 className="font-semibold mb-2">Pending Actions</h3>
        <p className="text-2xl font-bold text-amber-600" aria-label="Pending Actions Count">5</p>
      </div>
    </div>
  )
}
