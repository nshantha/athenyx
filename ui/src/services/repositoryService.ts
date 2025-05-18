import axios from 'axios';
import { 
  Repository, 
  RepositoryResponse, 
  RepositoryCreateRequest,
  RepositoryCreateResponse,
  RepositoryDeleteResponse,
  RepositoryStatusResponse,
  RepositoryStatus
} from '../types/repository';

const API_URL = process.env.REACT_APP_BACKEND_API_URL || 'http://localhost:8000/api';

// Get all repositories
export const getRepositories = async (): Promise<RepositoryResponse> => {
  const response = await axios.get(`${API_URL}/repositories`);
  
  // Map backend response to frontend Repository interface
  const repositories = response.data.repositories.map((repo: any) => ({
    id: repo.url, // Use URL as ID since backend doesn't provide an ID
    name: repo.service_name || 'Unknown',
    description: repo.description || '',
    path: repo.url, // Use URL as path
    url: repo.url,
    service_name: repo.service_name,
    last_indexed: repo.last_indexed,
    created_at: new Date().toISOString(), // Backend doesn't provide this
    updated_at: new Date().toISOString(), // Backend doesn't provide this
    status: repo.last_indexed ? RepositoryStatus.COMPLETED : RepositoryStatus.PENDING,
  }));
  
  return { repositories };
};

// Get a specific repository by ID
export const getRepository = async (id: string): Promise<Repository> => {
  const response = await axios.get(`${API_URL}/repositories/${id}`);
  return response.data.repository;
};

// Create a new repository
export const createRepository = async (data: RepositoryCreateRequest): Promise<RepositoryCreateResponse> => {
  const response = await axios.post(`${API_URL}/repositories`, data);
  return response.data;
};

// Delete a repository
export const deleteRepository = async (id: string): Promise<RepositoryDeleteResponse> => {
  const response = await axios.delete(`${API_URL}/repositories/${id}`);
  return response.data;
};

// Get repository ingestion status
export const getRepositoryStatus = async (id: string): Promise<RepositoryStatusResponse> => {
  const response = await axios.get(`${API_URL}/repositories/${id}/status`);
  return response.data;
};
