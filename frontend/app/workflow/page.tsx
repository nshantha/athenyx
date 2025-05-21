'use client'

import { useState } from 'react'
import { RiRobot2Line } from 'react-icons/ri'

export default function WorkflowPage() {
  const [workflows] = useState([
    {
      id: 1,
      name: 'Code Review Assistant',
      description: 'Automatically reviews PRs and suggests improvements',
      status: 'active',
      lastRun: '2 hours ago',
      type: 'code-review'
    },
    {
      id: 2,
      name: 'Documentation Generator',
      description: 'Creates and updates documentation from code',
      status: 'idle',
      lastRun: '3 days ago',
      type: 'documentation'
    },
    {
      id: 3,
      name: 'Requirements Analyzer',
      description: 'Links requirements to existing code',
      status: 'disabled',
      lastRun: 'Never',
      type: 'requirements'
    }
  ])
  
  const getStatusBadge = (status) => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      idle: 'bg-yellow-100 text-yellow-800',
      disabled: 'bg-gray-100 text-gray-800'
    }
    
    return (
      <span className={`${colors[status]} text-xs px-2 py-1 rounded-full font-medium`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }
  
  const getWorkflowIcon = (type) => {
    const colors = {
      'code-review': 'text-blue-500',
      'documentation': 'text-purple-500',
      'requirements': 'text-green-500',
      'security': 'text-red-500',
      'deploy': 'text-orange-500'
    }
    
    return <RiRobot2Line className={`h-8 w-8 ${colors[type] || 'text-gray-500'}`} />
  }
  
  return (
    <div className="container max-w-5xl py-8">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <RiRobot2Line className="h-6 w-6 mr-2" />
          <h1 className="text-2xl font-bold">Workflows</h1>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          Create Workflow
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {workflows.map(workflow => (
          <div key={workflow.id} className="border rounded-lg shadow-sm overflow-hidden">
            <div className="p-6">
              <div className="flex items-center gap-4">
                {getWorkflowIcon(workflow.type)}
                <div>
                  <h3 className="text-lg font-semibold">{workflow.name}</h3>
                  <p className="text-sm text-gray-500">{workflow.description}</p>
                </div>
              </div>
              
              <div className="mt-4 flex justify-between items-center">
                <span className="text-sm text-gray-500">Last run: {workflow.lastRun}</span>
                {getStatusBadge(workflow.status)}
              </div>
              
              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Type:</span>
                  <span className="font-medium">
                    {workflow.type.split('-').map(word => 
                      word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ')}
                  </span>
                </div>
              </div>
              
              <div className="mt-6 flex justify-between">
                <button className="px-3 py-1 border rounded-md text-sm">
                  Configure
                </button>
                <button className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm">
                  {workflow.status === 'active' ? 'View Results' : 'Run Now'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
