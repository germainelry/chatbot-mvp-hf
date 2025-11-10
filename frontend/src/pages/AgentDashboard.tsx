/**
 * Agent Supervision Dashboard
 * Human-in-the-Loop interface for agents to review, edit, and approve AI responses.
 * Demonstrates both pre-send and post-send HITL workflows.
 */
import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, XCircle, Edit2, Send, AlertTriangle } from 'lucide-react';
import {
  getConversations,
  getConversationMessages,
  sendMessage,
  updateMessage,
  generateAIResponse,
  updateConversation,
  submitFeedback,
  Conversation,
  Message,
} from '../services/api';

export default function AgentDashboard() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [aiDraft, setAiDraft] = useState<string>('');
  const [aiDraftId, setAiDraftId] = useState<number | null>(null);
  const [aiConfidence, setAiConfidence] = useState<number>(0);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedResponse, setEditedResponse] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<string>('');
  const [feedbackNotes, setFeedbackNotes] = useState('');

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedConvId) {
      loadMessages(selectedConvId);
    }
  }, [selectedConvId]);

  const loadConversations = async () => {
    try {
      const convs = await getConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadMessages = async (convId: number) => {
    try {
      const msgs = await getConversationMessages(convId);
      setMessages(msgs);
      
      // Check if there's an AI draft pending review
      const lastMessage = msgs[msgs.length - 1];
      if (lastMessage && lastMessage.message_type === 'ai_draft') {
        setAiDraft(lastMessage.content);
        setAiDraftId(lastMessage.id);
        setEditedResponse(lastMessage.content);
        setAiConfidence(lastMessage.confidence_score || 0);
      } else {
        setAiDraftId(null);
        // Check if we need to generate an AI response for the last customer message
        const lastCustomerMsg = msgs.filter(m => m.message_type === 'customer').pop();
        const hasResponse = msgs.some(m => 
          m.message_type !== 'customer' && 
          new Date(m.created_at) > new Date(lastCustomerMsg?.created_at || 0)
        );
        
        if (lastCustomerMsg && !hasResponse) {
          generateDraft(convId, lastCustomerMsg.content);
        }
      }
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const generateDraft = async (convId: number, userMessage: string) => {
    try {
      const response = await generateAIResponse(convId, userMessage);
      setAiDraft(response.response);
      setEditedResponse(response.response);
      setAiConfidence(response.confidence_score);
      
      // Save as draft
      await sendMessage({
        conversation_id: convId,
        content: response.response,
        message_type: 'ai_draft',
        confidence_score: response.confidence_score,
      });
      
      loadMessages(convId);
    } catch (error) {
      console.error('Failed to generate AI draft:', error);
    }
  };

  const handleSendResponse = async (wasEdited: boolean) => {
    if (!selectedConvId) return;

    try {
      const messageType = wasEdited ? 'agent_edited' : 'final';
      const originalContent = wasEdited ? aiDraft : undefined;

      // If there's an existing ai_draft, update it instead of creating a new message
      // This prevents duplicate messages from appearing
      if (aiDraftId) {
        await updateMessage(aiDraftId, {
          content: editedResponse,
          message_type: messageType,
          confidence_score: aiConfidence,
          original_ai_content: originalContent,
        });
      } else {
        // Fallback: create new message if no draft exists (shouldn't happen normally)
        await sendMessage({
          conversation_id: selectedConvId,
          content: editedResponse,
          message_type: messageType,
          confidence_score: aiConfidence,
          original_ai_content: originalContent,
        });
      }

      // Clear draft
      setAiDraft('');
      setAiDraftId(null);
      setEditedResponse('');
      setIsEditMode(false);
      setShowFeedback(true);

      loadMessages(selectedConvId);
    } catch (error) {
      console.error('Failed to send response:', error);
    }
  };

  const handleEscalate = async () => {
    if (!selectedConvId) return;

    try {
      await updateConversation(selectedConvId, 'escalated');
      setAiDraft('');
      setAiDraftId(null);
      setEditedResponse('');
      loadConversations();
      loadMessages(selectedConvId);
    } catch (error) {
      console.error('Failed to escalate:', error);
    }
  };

  const handleResolve = async () => {
    if (!selectedConvId) return;

    try {
      await updateConversation(selectedConvId, 'resolved');
      loadConversations();
      setShowFeedback(false);
    } catch (error) {
      console.error('Failed to resolve:', error);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!selectedConvId || !feedbackRating) return;

    try {
      await submitFeedback({
        conversation_id: selectedConvId,
        rating: feedbackRating,
        agent_correction: editedResponse !== aiDraft ? editedResponse : undefined,
        notes: feedbackNotes,
      });

      setShowFeedback(false);
      setFeedbackRating('');
      setFeedbackNotes('');
      handleResolve();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const getConfidenceBadge = (confidence: number) => {
    // Auto-send threshold is 65% - responses >= 65% are sent automatically
    if (confidence >= 0.8) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle className="h-3 w-3 mr-1" />
          High Confidence ({(confidence * 100).toFixed(0)}%) - Auto-sent
        </span>
      );
    } else if (confidence >= 0.65) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          <CheckCircle className="h-3 w-3 mr-1" />
          Good Confidence ({(confidence * 100).toFixed(0)}%) - Auto-sent
        </span>
      );
    } else if (confidence >= 0.5) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <AlertTriangle className="h-3 w-3 mr-1" />
          Medium Confidence ({(confidence * 100).toFixed(0)}%) - Needs Review
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <XCircle className="h-3 w-3 mr-1" />
          Low Confidence ({(confidence * 100).toFixed(0)}%) - Needs Review
        </span>
      );
    }
  };

  const selectedConversation = conversations.find(c => c.id === selectedConvId);

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Conversation Queue */}
      <div className="w-80 bg-white border-r overflow-y-auto">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Conversations</h2>
        </div>
        <div className="divide-y">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => setSelectedConvId(conv.id)}
              className={`p-4 cursor-pointer hover:bg-gray-50 ${
                selectedConvId === conv.id ? 'bg-primary-50 border-l-4 border-primary-600' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">#{conv.id}</span>
                <span
                  className={`px-2 py-1 rounded-full text-xs ${
                    conv.status === 'active'
                      ? 'bg-blue-100 text-blue-800'
                      : conv.status === 'resolved'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {conv.status}
                </span>
              </div>
              <p className="text-xs text-gray-600 truncate">{conv.last_message || 'No messages'}</p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(conv.updated_at).toLocaleTimeString()}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedConvId ? (
          <>
            {/* Header */}
            <div className="bg-white border-b p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">
                    Conversation #{selectedConvId}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Customer: {selectedConversation?.customer_id}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={handleEscalate}
                    className="px-4 py-2 text-sm border border-red-500 text-red-600 rounded-lg hover:bg-red-50"
                  >
                    <AlertCircle className="h-4 w-4 inline mr-1" />
                    Escalate
                  </button>
                  <button
                    onClick={handleResolve}
                    className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    <CheckCircle className="h-4 w-4 inline mr-1" />
                    Resolve
                  </button>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
              {messages.filter(m => m.message_type !== 'ai_draft').map((msg) => (
                <div
                  key={msg.id}
                  className={`mb-4 ${
                    msg.message_type === 'customer' ? 'text-right' : 'text-left'
                  }`}
                >
                  <div
                    className={`inline-block max-w-[70%] rounded-lg p-3 ${
                      msg.message_type === 'customer'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white text-gray-900'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    <div className="flex items-center justify-between mt-2">
                      <p className="text-xs opacity-70">
                        {new Date(msg.created_at).toLocaleTimeString()}
                      </p>
                      {msg.confidence_score !== undefined && msg.confidence_score !== null && (
                        <span className="text-xs ml-2">
                          {msg.message_type === 'agent_edited' ? '✏️ Edited' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* AI Draft Review Section */}
            {aiDraft && (
              <div className="border-t bg-white p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="font-semibold">AI Draft Response</h4>
                  {getConfidenceBadge(aiConfidence)}
                </div>

                {!isEditMode ? (
                  <div className="bg-gray-50 p-3 rounded-lg mb-3">
                    <p className="text-sm whitespace-pre-wrap">{editedResponse}</p>
                  </div>
                ) : (
                  <textarea
                    value={editedResponse}
                    onChange={(e) => setEditedResponse(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg p-3 text-sm mb-3 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                    rows={4}
                  />
                )}

                <div className="flex space-x-2">
                  {!isEditMode ? (
                    <>
                      <button
                        onClick={() => handleSendResponse(false)}
                        className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center justify-center"
                      >
                        <Send className="h-4 w-4 mr-2" />
                        Send as-is
                      </button>
                      <button
                        onClick={() => setIsEditMode(true)}
                        className="flex-1 border border-gray-300 px-4 py-2 rounded-lg hover:bg-gray-50 flex items-center justify-center"
                      >
                        <Edit2 className="h-4 w-4 mr-2" />
                        Edit & Send
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleSendResponse(true)}
                        className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700"
                      >
                        Send Edited Response
                      </button>
                      <button
                        onClick={() => {
                          setIsEditMode(false);
                          setEditedResponse(aiDraft);
                        }}
                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Feedback Modal */}
            {showFeedback && (
              <div className="border-t bg-yellow-50 p-4">
                <h4 className="font-semibold mb-3">Provide Feedback on AI Response</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-2">Rating</label>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setFeedbackRating('helpful')}
                        className={`px-4 py-2 rounded-lg ${
                          feedbackRating === 'helpful'
                            ? 'bg-green-600 text-white'
                            : 'border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        👍 Helpful
                      </button>
                      <button
                        onClick={() => setFeedbackRating('not_helpful')}
                        className={`px-4 py-2 rounded-lg ${
                          feedbackRating === 'not_helpful'
                            ? 'bg-red-600 text-white'
                            : 'border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        👎 Not Helpful
                      </button>
                      <button
                        onClick={() => setFeedbackRating('needs_improvement')}
                        className={`px-4 py-2 rounded-lg ${
                          feedbackRating === 'needs_improvement'
                            ? 'bg-yellow-600 text-white'
                            : 'border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        ⚠️ Needs Improvement
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Additional Notes (optional)
                    </label>
                    <textarea
                      value={feedbackNotes}
                      onChange={(e) => setFeedbackNotes(e.target.value)}
                      className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
                      rows={3}
                      placeholder="What could be improved?"
                    />
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={handleSubmitFeedback}
                      disabled={!feedbackRating}
                      className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                    >
                      Submit Feedback
                    </button>
                    <button
                      onClick={() => {
                        setShowFeedback(false);
                        handleResolve();
                      }}
                      className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <p>Select a conversation to view</p>
          </div>
        )}
      </div>
    </div>
  );
}

