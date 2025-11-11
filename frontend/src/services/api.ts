/**
 * API service for backend communication.
 * Centralized API calls with error handling.
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

export const getConversations = async (status?: string): Promise<Conversation[]> => {
  const response = await api.get('/conversations', { params: { status } });
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
  await api.delete(`/knowledge-base/${id}`);
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

export default api;

