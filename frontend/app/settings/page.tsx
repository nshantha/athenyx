'use client'

import { CiSettings } from 'react-icons/ci'

export default function SettingsPage() {
  return (
    <div className="container max-w-4xl py-8">
      <div className="flex items-center mb-6">
        <CiSettings className="h-6 w-6 mr-2" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>
      
      <div className="grid gap-6">
        <div className="rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Profile Settings</h2>
          <p className="text-sm text-gray-500 mb-6">
            Manage your personal information and account details
          </p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Full Name</label>
              <input 
                type="text" 
                className="w-full px-3 py-2 border rounded-md"
                placeholder="Your name"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input 
                type="email" 
                className="w-full px-3 py-2 border rounded-md"
                placeholder="you@example.com"
              />
              <p className="text-xs text-gray-500 mt-1">
                This is the email associated with your account
              </p>
            </div>
            
            <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              Save Changes
            </button>
          </div>
        </div>
        
        <div className="rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Appearance</h2>
          <p className="text-sm text-gray-500 mb-6">
            Customize the look and feel of the application
          </p>
          
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div>
              <h3 className="text-sm font-medium">Dark Mode</h3>
              <p className="text-xs text-gray-500">
                Enable dark mode for a better experience in low light
              </p>
            </div>
            <div className="h-6 w-11 rounded-full bg-gray-200 p-1 transition-colors duration-200">
              <div className="h-4 w-4 rounded-full bg-white shadow-sm transform translate-x-0 transition-transform duration-200"></div>
            </div>
          </div>
        </div>
        
        <div className="rounded-lg border p-6">
          <h2 className="text-xl font-semibold mb-4">Security Settings</h2>
          <p className="text-sm text-gray-500 mb-6">
            Manage your account's security settings
          </p>
          
          <div className="space-y-4">
            <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
              Change Password
            </button>
            <button className="ml-2 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
              Enable Two-Factor Authentication
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
