import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/layout/Header';
import Footer from '../components/layout/Footer';
import MainContent from '../components/layout/MainContent';
import { useRepositories } from '../hooks/useRepositories';
import { RepositoryCreateRequest } from '../types/repository';

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { repositories, addRepository, loading, error: repoError } = useRepositories();
  const [formData, setFormData] = useState<RepositoryCreateRequest>({
    url: '',
    branch: '',
    description: ''
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!formData.url.trim()) {
      setError('Repository URL is required');
      return;
    }

    try {
      const result = await addRepository(formData.url, formData.branch, formData.description);
      if (result) {
        setSuccess(`Repository "${formData.url}" added successfully`);
        setFormData({
          url: '',
          branch: '',
          description: ''
        });
      } else {
        setError('Failed to add repository');
      }
    } catch (err) {
      setError('An error occurred while adding the repository');
      console.error(err);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
      try {
        // Since we don't have a removeRepository function in our hooks yet,
        // we'll just show a message for now
        setError('Repository deletion not implemented yet');
      } catch (err) {
        setError('An error occurred while deleting the repository');
        console.error(err);
      }
    }
  };

  const handleBackToChat = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate('/');
  };

  return (
    <div className="flex flex-col h-screen bg-[#f8f5f0] text-[#3c3836]">
      <Header />
      
      <MainContent>
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center mb-6">
            <a 
              href="/"
              onClick={handleBackToChat}
              className="text-[#2c6694] hover:text-[#3d85c6] flex items-center transition-colors"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Chat
            </a>
            
            <h1 className="text-3xl font-bold ml-4 text-[#3c3836]">Settings</h1>
          </div>
          
          <div className="bg-[#fffaf0] border border-[#e8e1d9] rounded-lg p-6 shadow-sm mb-6">
            <h2 className="text-xl font-bold mb-4 text-[#2c6694]">Application Settings</h2>
            
            <div className="space-y-6">
              {/* API Configuration */}
              <div>
                <h3 className="text-lg font-medium mb-2 text-[#3c3836]">API Configuration</h3>
                <div className="space-y-3">
                  <div>
                    <label htmlFor="api-url" className="block text-sm font-medium text-[#5d5a58]">
                      Backend API URL
                    </label>
                    <input
                      id="api-url"
                      type="text"
                      defaultValue={process.env.REACT_APP_BACKEND_API_URL || 'http://localhost:8000'}
                      className="
                        mt-1 block w-full rounded-md 
                        bg-white border border-[#e8e1d9] 
                        text-[#3c3836] px-3 py-2
                        focus:outline-none focus:ring-1 focus:ring-[#2c6694]
                      "
                    />
                    <p className="mt-1 text-sm text-[#5d5a58]">
                      The URL of the backend API server
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Save Button */}
              <div className="pt-4">
                <button
                  type="button"
                  className="
                    bg-[#2c6694] hover:bg-[#3d85c6] 
                    text-white font-medium py-2 px-4 rounded 
                    transition-colors
                  "
                >
                  Save Settings
                </button>
              </div>
            </div>
          </div>
          
          <div className="mt-6 bg-[#fffaf0] border border-[#e8e1d9] rounded-lg p-6 shadow-sm mb-6">
            <h2 className="text-xl font-bold mb-4 text-[#2c6694]">About</h2>
            <p className="text-[#3c3836] mb-4">
              Actuamind is an Enterprise AI Knowledge Platform that helps you understand and navigate complex codebases through a natural language interface.
            </p>
            <p className="text-[#5d5a58]">
              Version: 1.0.0
            </p>
          </div>

          <div className="bg-[#fffaf0] border border-[#e8e1d9] p-6 rounded-lg shadow-sm mb-8">
            <h2 className="text-xl font-semibold mb-4 text-[#2c6694]">Add New Repository</h2>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4">
                {success}
              </div>
            )}
            
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="url" className="block text-[#3c3836] font-medium mb-2">
                  Repository URL *
                </label>
                <input
                  type="text"
                  id="url"
                  name="url"
                  value={formData.url}
                  onChange={handleChange}
                  className="w-full p-2 border border-[#e8e1d9] rounded focus:outline-none focus:ring-2 focus:ring-[#2c6694] bg-white"
                  placeholder="e.g., https://github.com/username/repo"
                  required
                />
              </div>
              
              <div className="mb-4">
                <label htmlFor="branch" className="block text-[#3c3836] font-medium mb-2">
                  Branch (optional)
                </label>
                <input
                  type="text"
                  id="branch"
                  name="branch"
                  value={formData.branch}
                  onChange={handleChange}
                  className="w-full p-2 border border-[#e8e1d9] rounded focus:outline-none focus:ring-2 focus:ring-[#2c6694] bg-white"
                  placeholder="e.g., main"
                />
              </div>
              
              <div className="mb-4">
                <label htmlFor="description" className="block text-[#3c3836] font-medium mb-2">
                  Description (optional)
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="w-full p-2 border border-[#e8e1d9] rounded focus:outline-none focus:ring-2 focus:ring-[#2c6694] bg-white"
                  placeholder="Brief description of the repository"
                  rows={3}
                />
              </div>
              
              <button
                type="submit"
                className="bg-[#2c6694] text-white py-2 px-4 rounded hover:bg-[#3d85c6] transition-colors"
                disabled={loading}
              >
                {loading ? 'Adding...' : 'Add Repository'}
              </button>
            </form>
          </div>

          <div className="bg-[#fffaf0] border border-[#e8e1d9] p-6 rounded-lg shadow-sm">
            <h2 className="text-xl font-semibold mb-4 text-[#2c6694]">Manage Repositories</h2>
            
            {repositories.length === 0 ? (
              <p className="text-[#5d5a58]">No repositories found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="bg-[#f1ede7]">
                    <tr>
                      <th className="py-2 px-4 text-left text-[#3c3836]">Name</th>
                      <th className="py-2 px-4 text-left text-[#3c3836]">Path</th>
                      <th className="py-2 px-4 text-left text-[#3c3836]">Status</th>
                      <th className="py-2 px-4 text-left text-[#3c3836]">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {repositories.map(repo => (
                      <tr key={repo.id} className="border-t border-[#e8e1d9]">
                        <td className="py-3 px-4">
                          <div className="font-medium text-[#3c3836]">{repo.name}</div>
                          {repo.description && (
                            <div className="text-sm text-[#5d5a58]">{repo.description}</div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-[#3c3836]">
                          <div className="max-w-xs truncate">{repo.path}</div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`
                            inline-block px-2 py-1 text-xs rounded
                            ${repo.status === 'completed' ? 'bg-green-50 text-green-800' : 
                              repo.status === 'processing' ? 'bg-yellow-50 text-yellow-800' :
                              repo.status === 'failed' ? 'bg-red-50 text-red-800' : 
                              'bg-gray-50 text-gray-800'}
                          `}>
                            {repo.status ? repo.status.charAt(0).toUpperCase() + repo.status.slice(1) : 'Unknown'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleDelete(repo.id, repo.name)}
                            className="text-red-600 hover:text-red-800 transition-colors"
                            disabled={loading}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </MainContent>
      
      <Footer />
    </div>
  );
};

export default Settings;
