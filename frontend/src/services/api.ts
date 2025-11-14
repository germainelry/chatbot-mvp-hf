/**
 * API service for backend communication.
 * Centralized API calls with error handling.
 */
import axios from 'axios';

// Get API base URL from environment variable, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Get API key from environment variable (optional - only if intentionally exposing to browser)
// WARNING: Only use VITE_API_KEY if the API key is meant to be public (e.g., for demo/public APIs)
// For production, consider using a proxy or server-side authentication instead
const API_KEY = import.meta.env.VITE_API_KEY;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add API key and tenant ID to requests
api.interceptors.request.use((config) => {
  // Add API key if provided (required for write operations in production)
  if (API_KEY) {
    config.headers['X-API-Key'] = API_KEY;
  } else {
    console.warn('VITE_API_KEY not set. Some API calls may fail.');
  }
  
  return config;
});

// Add response interceptor for error handling and logging
api.interceptors.response.use(
  (response) => {
    // Log successful responses in development
    if (import.meta.env.DEV) {
      console.log(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
    }
    return response;
  },
  (error) => {
    // Log errors with details
    if (error.response) {
      // Server responded with error status
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${error.response.status}:`, {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data,
        headers: error.response.headers
      });
    } else if (error.request) {
      // Request made but no response received
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url} - No response:`, error.message);
    } else {
      // Error setting up request
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, error.message);
    }
    return Promise.reject(error);
  }
);

// Types
export interface Conversation {
  id: number;
  customer_id: string;
  status: 'active' | 'resolved' | 'escalated';
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  message_count: number;
  last_message?: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  content: string;
  message_type: 'customer' | 'ai_draft' | 'agent_edited' | 'final' | 'agent_only';
  confidence_score?: number;
  created_at: string;
  original_ai_content?: string;
}

export interface AIResponse {
  response: string;
  confidence_score: number;
  matched_articles: any[];
  reasoning?: string;
  auto_send_threshold?: number;
  should_auto_send?: boolean;
}

export interface KnowledgeArticle {
  id: number;
  title: string;
  content: string;
  category: string;
  tags: string;
  created_at: string;
  updated_at: string;
}

export interface Metrics {
  total_conversations: number;
  active_conversations: number;
  resolved_conversations: number;
  escalated_conversations: number;
  resolution_rate: number;
  escalation_rate: number;
  avg_confidence_score: number;
  total_feedback: number;
  helpful_feedback: number;
  not_helpful_feedback: number;
  feedback_sentiment: number;
}

export interface FeedbackHistory {
  id: number;
  conversation_id: number;
  rating: string;
  agent_correction: string;
  notes: string;
  created_at: string;
}

export interface DailyMetrics {
  date: string;
  total_conversations: number;
  resolved_conversations: number;
  escalated_conversations: number;
  avg_confidence_score: number;
  helpful_feedback: number;
  not_helpful_feedback: number;
  needs_improvement_feedback: number;
}

export interface TimeSeriesResponse {
  metrics: DailyMetrics[];
}

export interface EvaluationMetrics {
  avg_bleu_score: number | null;
  avg_semantic_similarity: number | null;
  avg_csat: number | null;
  deflection_rate: number;
  total_evaluations: number;
  total_csat_responses: number;
}

export interface AgentPerformance {
  total_actions: number;
  approval_rate: number;
  correction_frequency: number;
  action_breakdown: Record<string, number>;
}

// API Functions

// Conversations
export const createConversation = async (customerId: string): Promise<Conversation> => {
  const response = await api.post('/conversations', { customer_id: customerId });
  return response.data;
};

export const getConversations = async (status?: string, customer_id?: string): Promise<Conversation[]> => {
  const params: any = {};
  if (status) params.status = status;
  if (customer_id) params.customer_id = customer_id;
  const response = await api.get('/conversations', { params });
  return response.data;
};

export const getConversation = async (id: number): Promise<Conversation> => {
  const response = await api.get(`/conversations/${id}`);
  return response.data;
};

export const updateConversation = async (id: number, status: string, csat_score?: number | null): Promise<Conversation> => {
  const response = await api.patch(`/conversations/${id}`, { 
    status,
    ...(csat_score !== undefined && csat_score !== null && { csat_score })
  });
  return response.data;
};

export const getConversationMessages = async (conversationId: number): Promise<Message[]> => {
  const response = await api.get(`/conversations/${conversationId}/messages`);
  return response.data;
};

// Messages
export const sendMessage = async (data: {
  conversation_id: number;
  content: string;
  message_type: string;
  confidence_score?: number;
  original_ai_content?: string;
}): Promise<Message> => {
  const response = await api.post('/messages', data);
  return response.data;
};

export const updateMessage = async (
  messageId: number,
  data: {
    content?: string;
    message_type?: string;
    confidence_score?: number;
    original_ai_content?: string;
  }
): Promise<Message> => {
  const response = await api.patch(`/messages/${messageId}`, data);
  return response.data;
};

export const deleteMessage = async (messageId: number): Promise<{ message: string; message_id: number }> => {
  // Get admin token from localStorage
  const adminToken = localStorage.getItem('admin_token');

  if (!adminToken) {
    throw new Error('Admin authentication required. Please login as admin to delete messages.');
  }

  const response = await api.delete(`/messages/${messageId}`, {
    headers: {
      'X-Admin-Token': adminToken
    }
  });
  return response.data;
};

// AI
export const generateAIResponse = async (
  conversationId: number,
  userMessage: string
): Promise<AIResponse> => {
  const response = await api.post('/ai/generate', {
    conversation_id: conversationId,
    user_message: userMessage,
  });
  return response.data;
};

// Feedback
export const submitFeedback = async (data: {
  conversation_id: number;
  message_id?: number;
  rating: string;
  agent_correction?: string;
  notes?: string;
}): Promise<any> => {
  const response = await api.post('/feedback', data);
  return response.data;
};

// Knowledge Base
export const getKnowledgeArticles = async (category?: string, search?: string): Promise<KnowledgeArticle[]> => {
  const response = await api.get('/knowledge-base', { params: { category, search } });
  return response.data;
};

export const createKnowledgeArticle = async (data: {
  title: string;
  content: string;
  category: string;
  tags: string;
}): Promise<KnowledgeArticle> => {
  const response = await api.post('/knowledge-base', data);
  return response.data;
};

export const updateKnowledgeArticle = async (
  id: number,
  data: Partial<KnowledgeArticle>
): Promise<KnowledgeArticle> => {
  const response = await api.put(`/knowledge-base/${id}`, data);
  return response.data;
};

export const deleteKnowledgeArticle = async (id: number): Promise<void> => {
  // Get admin token from localStorage
  const adminToken = localStorage.getItem('admin_token');

  if (!adminToken) {
    throw new Error('Admin authentication required. Please login as admin to delete articles.');
  }

  await api.delete(`/knowledge-base/${id}`, {
    headers: {
      'X-Admin-Token': adminToken
    }
  });
};

// Analytics
export const getMetrics = async (): Promise<Metrics> => {
  const response = await api.get('/analytics/metrics');
  return response.data;
};

export const getFeedbackHistory = async (): Promise<FeedbackHistory[]> => {
  const response = await api.get('/analytics/feedback-history');
  return response.data;
};

export const getTimeSeriesMetrics = async (days: number = 30): Promise<TimeSeriesResponse> => {
  const response = await api.get('/analytics/time-series', { params: { days } });
  return response.data;
};

export const getEvaluationMetrics = async (days: number = 30): Promise<EvaluationMetrics> => {
  const response = await api.get('/analytics/evaluation', { params: { days } });
  return response.data;
};

export const getAgentPerformance = async (days: number = 30): Promise<AgentPerformance> => {
  const response = await api.get('/analytics/agent-performance', { params: { days } });
  return response.data;
};

export const logAgentAction = async (data: {
  action_type: string;
  conversation_id?: number;
  message_id?: number;
  action_data?: Record<string, any>;
}): Promise<any> => {
  const response = await api.post('/agent-actions', data);
  return response.data;
};

// Configuration Types
export interface TenantConfiguration {
  tenant_id: number;
  llm_provider: string;
  llm_model_name: string;
  llm_config?: Record<string, any>;
  embedding_model: string;
  tone: string;
  auto_send_threshold: number;
  ui_config?: {
    brand_name?: string;
    logo_url?: string;
    primary_color?: string;
  };
}

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  is_active: number;
  created_at: string;
  updated_at: string;
}

// Configuration API (global configuration)
export const getConfiguration = async (): Promise<TenantConfiguration> => {
  const response = await api.get(`/config`);
  return response.data;
};

export const updateConfiguration = async (
  config: Partial<TenantConfiguration>
): Promise<TenantConfiguration> => {
  const response = await api.put(`/config`, config);
  return response.data;
};

// Backward compatibility aliases
export const getTenantConfiguration = async (_tenantId?: number): Promise<TenantConfiguration> => {
  return getConfiguration();
};

export const updateTenantConfiguration = async (
  _tenantId: number,
  config: Partial<TenantConfiguration>
): Promise<TenantConfiguration> => {
  return updateConfiguration(config);
};

export const listLLMProviders = async (): Promise<{ providers: string[] }> => {
  const response = await api.get('/config/llm-providers');
  return response.data;
};

export const listLLMModels = async (provider: string): Promise<{ models: string[] }> => {
  const response = await api.get(`/config/llm-models/${provider}`);
  return response.data;
};

export interface EnvironmentInfo {
  default_provider: string;
  default_model: string;
}

export const detectEnvironment = async (): Promise<EnvironmentInfo> => {
  const response = await api.get('/config/environment');
  return response.data;
};

export interface ProviderMetadata {
  display_name: string;
  description: string;
  cost: string;
  environments: string[];
  requires_api_key: boolean;
  setup_complexity: string;
  setup_steps: string[];
  signup_url?: string;
  paid_models?: string[];
}

export const getLLMProviderInfo = async (provider: string): Promise<ProviderMetadata> => {
  const response = await api.get(`/config/llm-provider-info/${provider}`);
  return response.data;
};


export const testLLMConnection = async (data: {
  provider: string;
  model: string;
  config?: Record<string, any>;
}): Promise<{ success: boolean; message: string; test_response?: string }> => {
  const response = await api.post('/config/test-llm', data);
  return response.data;
};

export interface EmbeddingModel {
  name: string;
  description: string;
  use_case: string;
}

export const listEmbeddingModels = async (): Promise<{ models: EmbeddingModel[] }> => {
  const response = await api.get('/config/embedding-models');
  return response.data;
};

// Knowledge Base Ingestion
export const uploadPDF = async (file: File): Promise<{ message: string; articles_created: number; source_id: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/knowledge-base/upload/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const uploadCSV = async (file: File): Promise<{ message: string; articles_created: number; source_id: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/knowledge-base/upload/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const uploadDocument = async (file: File): Promise<{ message: string; articles_created: number; source_id: number }> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/knowledge-base/upload/document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// Tenant Management - REMOVED (no longer needed)

export default api;

