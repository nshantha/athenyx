import axios from 'axios';

// Get the Backend API URL from environment variable
// Use a default for local running if the env var isn't set
const BACKEND_API_URL = process.env.REACT_APP_BACKEND_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: BACKEND_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Define API endpoints
export const ENDPOINTS = {
  QUERY: '/api/query',
  REPOSITORIES: '/api/repositories',
};

export default api;
