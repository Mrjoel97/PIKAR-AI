'use client';
import { usePersona } from '@/hooks/usePersona';

export default function SettingsPage() {
  const { persona } = usePersona();

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">User Settings</h1>
      
      <div className="bg-white p-6 rounded-lg shadow-sm border space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-4">Profile Information</h2>
          <div className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">Full Name</label>
              <input id="fullName" type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border" placeholder="John Doe" />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email Address</label>
              <input id="email" type="email" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border" placeholder="john@example.com" />
            </div>
          </div>
        </section>

        {persona === 'startup' && (
          <section className="pt-6 border-t">
            <h2 className="text-lg font-semibold mb-4">Startup Settings</h2>
            <div className="space-y-4">
               <div>
                  <label htmlFor="burnRate" className="block text-sm font-medium text-gray-700">Target Burn Rate</label>
                  <input id="burnRate" type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-2 border" placeholder="50000" />
               </div>
            </div>
          </section>
        )}

        {persona === 'enterprise' && (
          <section className="pt-6 border-t">
             <h2 className="text-lg font-semibold mb-4">Enterprise Compliance</h2>
             <div className="space-y-2">
               <div className="flex items-center space-x-2">
                 <input type="checkbox" id="auditLog" defaultChecked className="rounded text-indigo-600 focus:ring-indigo-500" />
                 <label htmlFor="auditLog" className="text-sm text-gray-700">Enable Detailed Audit Logs</label>
               </div>
             </div>
          </section>
        )}

        <section className="pt-6 border-t">
          <h2 className="text-lg font-semibold mb-4">Preferences</h2>
          <div className="flex items-center space-x-2">
             <input type="checkbox" id="notifications" className="rounded text-indigo-600 focus:ring-indigo-500" />
             <label htmlFor="notifications" className="text-sm text-gray-700">Receive email notifications</label>
          </div>
        </section>
        
        <div className="pt-6 border-t flex justify-end">
          <button className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}
