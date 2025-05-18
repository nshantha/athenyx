import React, { useState } from 'react';
import { useRepositories } from '../../hooks/useRepositories';
import { validateRepositoryUrl } from '../../utils/validators';

interface ValidationState {
  url: { valid: boolean; message: string };
}

const AddRepositoryForm: React.FC = () => {
  const { addRepository, addRepoStatus } = useRepositories();
  
  const [formState, setFormState] = useState({
    url: '',
    branch: '',
    description: ''
  });
  
  const [validation, setValidation] = useState<ValidationState>({
    url: { valid: true, message: '' }
  });
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormState(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear validation errors when typing
    if (name === 'url' && !validation.url.valid) {
      setValidation(prev => ({
        ...prev,
        url: { valid: true, message: '' }
      }));
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate URL
    const urlValidation = validateRepositoryUrl(formState.url);
    if (!urlValidation.valid) {
      setValidation(prev => ({
        ...prev,
        url: { valid: urlValidation.valid, message: urlValidation.message || 'Invalid URL' }
      }));
      return;
    }
    
    // Submit form
    const success = await addRepository(
      formState.url,
      formState.branch || undefined,
      formState.description || undefined
    );
    
    // Clear form on success
    if (success) {
      setFormState({
        url: '',
        branch: '',
        description: ''
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="repo-url" className="block text-sm font-medium text-gray-300">
          Repository URL <span className="text-red-500">*</span>
        </label>
        <input
          id="repo-url"
          name="url"
          type="text"
          value={formState.url}
          onChange={handleChange}
          placeholder="https://github.com/username/repository.git"
          className={`
            mt-1 block w-full rounded-md 
            bg-gray-800 border 
            ${!validation.url.valid ? 'border-red-500' : 'border-gray-700'} 
            text-gray-200 px-3 py-2
            focus:outline-none focus:ring-1 focus:ring-green-500
          `}
        />
        {!validation.url.valid && (
          <p className="mt-1 text-sm text-red-500">{validation.url.message}</p>
        )}
      </div>
      
      <div>
        <label htmlFor="repo-branch" className="block text-sm font-medium text-gray-300">
          Branch (optional)
        </label>
        <input
          id="repo-branch"
          name="branch"
          type="text"
          value={formState.branch}
          onChange={handleChange}
          placeholder="main"
          className="
            mt-1 block w-full rounded-md 
            bg-gray-800 border border-gray-700 
            text-gray-200 px-3 py-2
            focus:outline-none focus:ring-1 focus:ring-green-500
          "
        />
      </div>
      
      <div>
        <label htmlFor="repo-description" className="block text-sm font-medium text-gray-300">
          Description (optional)
        </label>
        <textarea
          id="repo-description"
          name="description"
          value={formState.description}
          onChange={handleChange}
          rows={2}
          placeholder="Description of this repository"
          className="
            mt-1 block w-full rounded-md 
            bg-gray-800 border border-gray-700 
            text-gray-200 px-3 py-2
            focus:outline-none focus:ring-1 focus:ring-green-500
            resize-none
          "
        />
      </div>
      
      <button
        type="submit"
        disabled={addRepoStatus.loading}
        className="
          w-full bg-green-600 hover:bg-green-700 
          disabled:bg-gray-700 disabled:cursor-not-allowed
          text-white font-medium py-2 px-4 rounded 
          transition-colors
        "
      >
        {addRepoStatus.loading ? 'Adding...' : 'Add Repository'}
      </button>
      
      {addRepoStatus.error && (
        <p className="mt-2 text-sm text-red-500">{addRepoStatus.error}</p>
      )}
      
      {addRepoStatus.success && (
        <p className="mt-2 text-sm text-green-500">Repository added successfully!</p>
      )}
    </form>
  );
};

export default AddRepositoryForm;
