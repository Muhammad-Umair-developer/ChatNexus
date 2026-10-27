import axios from 'axios';

export interface Message {
  id?: number;
  session_id?: number;
  role: 'user' | 'assistant';
  content: string;
  file_name?: string;
  created_at?: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  messages?: Message[];
}

export interface DocumentUploadResponse {
  filename: string;
  chunks_count: number;
  message: string;
}

// Configurable API base URL, defaulting to local FastAPI instance
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Note: Do NOT set a static global 'Content-Type': 'application/json' header.
// Axios automatically assigns 'application/json' for objects and 'multipart/form-data; boundary=...' for FormData.
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});