import axios from 'axios';

export interface Message {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});