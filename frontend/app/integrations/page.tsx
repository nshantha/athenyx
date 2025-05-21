'use client'

import { useState } from 'react'
import { BsPlug, BsMicrosoft } from 'react-icons/bs'
import { FaSlack, FaConfluence, FaJira, FaGithub, FaGitlab } from 'react-icons/fa'

export default function IntegrationsPage() {
  const [integrations] = useState([
    {
      id: 1,
      name: 'GitHub',
      description: 'Connect to GitHub repositories',
      status: 'connected',
      icon: FaGithub,
      color: 'text-black',
      accounts: ['actuamind-org']
    },
    {
      id: 2,
      name: 'Slack',
      description: 'Integrate with Slack channels',
      status: 'connected',
      icon: FaSlack,
      color: 'text-purple-500',
      accounts: ['actuamind-workspace']
    },
    {
      id: 3,
      name: 'Confluence',
      description: 'Connect to Confluence spaces',
      status: 'disconnected',
      icon: FaConfluence,
      color: 'text-blue-500',
      accounts: []
    },
    {
      id: 4,
      name: 'Jira',
      description: 'Integrate with Jira projects',
      status: 'disconnected',
      icon: FaJira,
      color: 'text-blue-600',
      accounts: []
    },
    {
      id: 5,
      name: 'GitLab',
      description: 'Connect to GitLab repositories',
      status: 'disconnected',
      icon: FaGitlab,
      color: 'text-orange-600',
      accounts: []
    },
    {
      id: 6,
      name: 'Microsoft Teams',
      description: 'Integrate with Teams channels',
      status: 'disconnected',
      icon: BsMicrosoft,
      color: 'text-blue-700',
      accounts: []
    }
  ])
  
  const getStatusBadge = (status) => {
    const colors = {
      connected: 'bg-green-100 text-green-800',
      disconnected: 'bg-gray-100 text-gray-800',
      pending: 'bg-yellow-100 text-yellow-800'
    }
    
    return (
      <span className={`${colors[status]} text-xs px-2 py-1 rounded-full font-medium`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }
  
  return (
    <div className="container max-w-5xl py-8">
      <div className="flex items-center mb-8">
        <BsPlug className="h-6 w-6 mr-2" />
        <h1 className="text-2xl font-bold">Integrations</h1>
      </div>
      
      <p className="text-gray-500 mb-6">
        Connect Actuamind with your favorite tools and services to enhance your workflow.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {integrations.map(integration => {
          const Icon = integration.icon
          return (
            <div key={integration.id} className="border rounded-lg shadow-sm overflow-hidden">
              <div className="p-6">
                <div className="flex items-center gap-4">
                  <Icon className={`h-8 w-8 ${integration.color}`} />
                  <div>
                    <h3 className="text-lg font-semibold">{integration.name}</h3>
                    <p className="text-sm text-gray-500">{integration.description}</p>
                  </div>
                </div>
                
                <div className="mt-4 flex justify-between items-center">
                  <span className="text-sm text-gray-500">
                    {integration.status === 'connected' 
                      ? `Connected to ${integration.accounts.join(', ')}` 
                      : 'Not connected'}
                  </span>
                  {getStatusBadge(integration.status)}
                </div>
                
                <div className="mt-4 flex items-center justify-between space-x-2">
                  <span className="text-sm font-medium">Enabled</span>
                  <div className={`h-6 w-11 rounded-full ${integration.status === 'connected' ? 'bg-blue-600' : 'bg-gray-200'} p-1 transition-colors duration-200`}>
                    <div className={`h-4 w-4 rounded-full bg-white shadow-sm transform ${integration.status === 'connected' ? 'translate-x-5' : 'translate-x-0'} transition-transform duration-200`}></div>
                  </div>
                </div>
                
                <div className="mt-6 flex justify-end">
                  {integration.status === 'connected' ? (
                    <button 
                      className="px-3 py-1 border rounded-md text-sm"
                    >
                      Disconnect
                    </button>
                  ) : (
                    <button 
                      className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm"
                    >
                      Connect
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
