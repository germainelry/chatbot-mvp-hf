/**
 * Customer Chat Interface
 * Simple chat UI for customers to interact with AI support assistant.
 * Includes conversation history to allow customers to return to previous chats.
 */
import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, History, Plus, MessageSquare } from 'lucide-react';
import { createConversation, sendMessage, generateAIResponse, Message, getConversations, getConversationMessages } from '../services/api';

export default function CustomerChat() {
  const [customerId, setCustomerId] = useState<string>('');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize customer ID from localStorage or create new one
  useEffect(() => {
    let storedCustomerId = localStorage.getItem('customer_id');
    if (!storedCustomerId) {
      storedCustomerId = `customer_${Date.now()}`;
      localStorage.setItem('customer_id', storedCustomerId);
    }
    setCustomerId(storedCustomerId);
    loadConversationHistory(storedCustomerId);
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversationHistory = async (custId: string) => {
    try {
      const allConversations = await getConversations();
      // Filter conversations for this customer
      const customerConvs = allConversations.filter(
        (conv: any) => conv.customer_id === custId
      );
      setConversationHistory(customerConvs);
      
      // Load most recent active conversation if exists
      const activeConv = customerConvs.find((c: any) => c.status === 'active');
      if (activeConv) {
        loadConversation(activeConv.id);
      }
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    }
  };

  const loadConversation = async (convId: number) => {
    try {
      const msgs = await getConversationMessages(convId);
      setMessages(msgs);
      setConversationId(convId);
      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages([]);
    setShowHistory(false);
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Create conversation on first message (lazy initialization)
    let activeConversationId = conversationId;
    if (!activeConversationId) {
      try {
        const conversation = await createConversation(customerId);
        activeConversationId = conversation.id;
        setConversationId(activeConversationId);
        // Reload history to show new conversation
        loadConversationHistory(customerId);
      } catch (error) {
        console.error('Failed to create conversation:', error);
        return;
      }
    }

    const userMessageContent = inputMessage;
    setInputMessage('');
    setIsLoading(true);

    try {
      // Send customer message
      const customerMsg = await sendMessage({
        conversation_id: activeConversationId,
        content: userMessageContent,
        message_type: 'customer',
      });

      setMessages(prev => [...prev, customerMsg]);

      // Generate AI response
      const aiResponse = await generateAIResponse(activeConversationId, userMessageContent);

      // For customer view, auto-send responses above confidence threshold (65%)
      // Lower confidence responses are queued for agent review
      if (aiResponse.confidence_score >= 0.65) {
        // Auto-send to customer
        const aiMsg = await sendMessage({
          conversation_id: activeConversationId,
          content: aiResponse.response,
          message_type: 'final',
          confidence_score: aiResponse.confidence_score,
        });
        setMessages(prev => [...prev, aiMsg]);
      } else {
        // Low confidence - show pending message for agent review
        const pendingMsg = {
          id: Date.now(),
          conversation_id: activeConversationId,
          content: 'Your message has been received and is being reviewed by our team. We\'ll respond shortly.',
          message_type: 'final' as const,
          confidence_score: 0,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, pendingMsg]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 h-[calc(100vh-4rem)]">
      <div className="bg-white rounded-lg shadow-lg h-full flex flex-col">
        {/* Header */}
        <div className="bg-primary-600 text-white p-4 rounded-t-lg flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Customer Support Chat</h2>
            <p className="text-sm text-primary-100">We're here to help!</p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="p-2 hover:bg-primary-700 rounded-lg transition-colors"
              title="Conversation History"
            >
              <History className="h-5 w-5" />
            </button>
            <button
              onClick={startNewConversation}
              className="p-2 hover:bg-primary-700 rounded-lg transition-colors"
              title="New Conversation"
            >
              <Plus className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Conversation History Sidebar */}
        {showHistory && (
          <div className="border-b p-4 bg-gray-50">
            <h3 className="font-semibold text-gray-900 mb-3">Conversation History</h3>
            {conversationHistory.length === 0 ? (
              <p className="text-sm text-gray-500">No previous conversations</p>
            ) : (
              <div className="space-y-2">
                {conversationHistory.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      conv.id === conversationId
                        ? 'bg-primary-50 border-primary-300'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        <MessageSquare className="h-4 w-4 inline mr-1" />
                        Conversation #{conv.id}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          conv.status === 'active'
                            ? 'bg-blue-100 text-blue-800'
                            : conv.status === 'resolved'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {conv.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 truncate">
                      {conv.last_message || 'No messages yet'}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(conv.created_at).toLocaleDateString()} at{' '}
                      {new Date(conv.created_at).toLocaleTimeString()}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !showHistory && (
            <div className="text-center text-gray-500 mt-8">
              <Bot className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>Start a conversation with our AI assistant</p>
              <p className="text-sm mt-1">Ask about returns, shipping, products, or account help</p>
              {conversationHistory.length > 0 && (
                <button
                  onClick={() => setShowHistory(true)}
                  className="mt-4 text-primary-600 hover:text-primary-700 text-sm font-medium"
                >
                  <History className="h-4 w-4 inline mr-1" />
                  View conversation history
                </button>
              )}
            </div>
          )}

          {messages
            .filter((message) => message.message_type !== 'ai_draft') // Filter out drafts - customers should never see them
            .map((message) => {
            const isCustomer = message.message_type === 'customer';
            return (
              <div
                key={message.id}
                className={`flex ${isCustomer ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`flex max-w-[70%] ${
                    isCustomer ? 'flex-row-reverse' : 'flex-row'
                  }`}
                >
                  <div
                    className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                      isCustomer ? 'bg-primary-600 ml-2' : 'bg-gray-300 mr-2'
                    }`}
                  >
                    {isCustomer ? (
                      <User className="h-5 w-5 text-white" />
                    ) : (
                      <Bot className="h-5 w-5 text-gray-600" />
                    )}
                  </div>
                  <div
                    className={`rounded-lg p-3 ${
                      isCustomer
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs mt-1 opacity-70">
                      {new Date(message.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex max-w-[70%]">
                <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-300 mr-2 flex items-center justify-center">
                  <Bot className="h-5 w-5 text-gray-600" />
                </div>
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <div className="flex space-x-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

