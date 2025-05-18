export interface Repository {
  id: string;
  name: string;
  description: string;
  path: string;
  url?: string;
  service_name?: string;
  last_indexed?: string;
  created_at: string;
  updated_at: string;
  status: RepositoryStatus;
  size?: number;
  language?: string;
  stars?: number;
  forks?: number;
}

export enum RepositoryStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed"
}

export interface IngestionProgress {
  repository_id: string;
  status: RepositoryStatus;
  progress: number;
  total_files?: number;
  processed_files?: number;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface RepositoryResponse {
  repositories: Repository[];
}

export interface RepositoryCreateRequest {
  url: string;
  branch?: string;
  description?: string;
}

export interface RepositoryCreateResponse {
  repository: Repository;
}

export interface RepositoryDeleteResponse {
  success: boolean;
  message?: string;
}

export interface RepositoryStatusResponse {
  status: IngestionProgress;
} 