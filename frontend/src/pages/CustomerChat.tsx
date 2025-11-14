/**
 * Customer Chat Interface
 * Modern chat UI for customers to interact with AI support assistant.
 * Includes conversation history to allow customers to return to previous chats.
 */
import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, History, Plus, MessageSquare } from 'lucide-react';
import { getTheme } from '../config/theme';
import { createConversation, sendMessage, generateAIResponse, Message, getConversations, getConversationMessages } from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '../components/ui/sheet';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { cn } from '../components/ui/utils';

export default function CustomerChat() {
  const [customerId, setCustomerId] = useState<string>('');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isSendingRef = useRef<boolean>(false); // Track if we're currently sending a message
  const loadingHistoryRef = useRef(false); // Prevent duplicate history loads
  const loadingMessagesRef = useRef(false); // Prevent duplicate message loads

  // Initialize customer ID from localStorage or create new one
  useEffect(() => {
    let storedCustomerId = localStorage.getItem('customer_id');
    if (!storedCustomerId) {
      storedCustomerId = `customer_${Date.now()}`;
      localStorage.setItem('customer_id', storedCustomerId);
    }
    setCustomerId(storedCustomerId);

    // Always load conversation history on mount (but don't auto-load conversation)
    loadConversationHistory(storedCustomerId, false).then(() => {
      // After history is loaded, restore last viewed conversation ID from localStorage
      // Verify the conversation_id is for this specific customer to prevent mixing
      const lastConversationId = localStorage.getItem(`last_conversation_id_${storedCustomerId}`);
      if (lastConversationId) {
        const convId = parseInt(lastConversationId, 10);
        if (!isNaN(convId)) {
          setConversationId(convId);
          // Load messages for restored conversation
          loadConversation(convId);
        }
      }
    });

    // Apply theme
    const theme = getTheme();
    if (theme) {
      document.title = theme.brandName;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load messages when conversationId changes (but not on initial mount if already loading)
  useEffect(() => {
    if (conversationId && customerId && !isLoading && !isSendingRef.current) {
      // Only load if we don't already have messages for this conversation
      const currentConvId = messages.length > 0 ? messages[0]?.conversation_id : null;
      if (currentConvId !== conversationId) {
        loadConversation(conversationId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // Reload conversation history when history sheet opens
  useEffect(() => {
    if (showHistory && customerId) {
      loadConversationHistory(customerId);
    }
  }, [showHistory, customerId]);

  const loadConversationHistory = async (custId: string, autoLoadConversation: boolean = true): Promise<void> => {
    if (!custId) {
      console.warn('No customer ID provided, cannot load conversation history');
      return;
    }
    
    // Prevent duplicate requests
    if (loadingHistoryRef.current) {
      return;
    }
    loadingHistoryRef.current = true;
    
    try {
      console.log('Loading conversation history for customer:', custId);
      // Use customer_id filter in API call for better performance
      const customerConvs = await getConversations(undefined, custId);
      console.log('Loaded conversations:', customerConvs);
      setConversationHistory(customerConvs || []);
      
      // Only auto-load conversation if explicitly requested and no conversation is currently selected
      // This prevents overriding messages that are already displayed
      if (autoLoadConversation && !conversationId && customerConvs && customerConvs.length > 0) {
        // Load most recent active conversation if exists
        const activeConv = customerConvs.find((c: any) => c.status === 'active');
        if (activeConv) {
          console.log('Loading active conversation:', activeConv.id);
          loadConversation(activeConv.id);
        } else {
          // If no active conversation, load the most recent one
          const mostRecent = customerConvs[0];
          console.log('Loading most recent conversation:', mostRecent.id);
          loadConversation(mostRecent.id);
        }
      }
    } catch (error: any) {
      console.error('Failed to load conversation history:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        customerId: custId
      });
      if (error.response?.status === 401) {
        console.error('Authentication failed. Check if VITE_API_KEY is set in .env.local and restart the dev server.');
      } else if (error.message === 'Network Error' || error.code === 'ECONNREFUSED') {
        console.error('Cannot connect to backend. Ensure backend server is running on http://localhost:8000');
      }
      setConversationHistory([]);
    } finally {
      loadingHistoryRef.current = false;
    }
  };

  const loadConversation = async (convId: number) => {
    // Prevent duplicate requests for the same conversation
    if (loadingMessagesRef.current) {
      return;
    }

    // Don't load if we're currently sending a message
    if (isSendingRef.current) {
      return;
    }

    // Don't load if we don't have a customer ID yet
    if (!customerId) {
      return;
    }

    loadingMessagesRef.current = true;

    try {
      const msgs = await getConversationMessages(convId);
      // Only update if we're still on the same conversation (prevent race conditions)
      // Use a ref check to avoid stale closure issues
      const currentConvId = conversationId;
      if (convId === currentConvId || currentConvId === null) {
        setMessages(msgs);
        setConversationId(convId);
        // Store last viewed conversation in localStorage with customer-specific key
        localStorage.setItem(`last_conversation_id_${customerId}`, convId.toString());
        setShowHistory(false);
      }
    } catch (error: any) {
      console.error('Failed to load conversation:', error);
      if (error.response?.status === 404) {
        console.error('Conversation not found. It may have been deleted.');
        // Clear invalid conversation ID from localStorage and state
        if (customerId) {
          localStorage.removeItem(`last_conversation_id_${customerId}`);
        }
        setConversationId(null);
        setMessages([]);
      } else if (error.message === 'Network Error' || error.code === 'ECONNREFUSED') {
        console.error('Cannot connect to backend. Ensure backend server is running on http://localhost:8000');
      }
    } finally {
      loadingMessagesRef.current = false;
    }
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages([]);
    setShowHistory(false);
    // Clear last conversation from localStorage with customer-specific key
    if (customerId) {
      localStorage.removeItem(`last_conversation_id_${customerId}`);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || isSendingRef.current) return;

    const userMessageContent = inputMessage.trim();
    
    // Mark that we're sending a message to prevent useEffect from clearing messages
    isSendingRef.current = true;
    
    // Optimistic UI update: Clear input and show message immediately
    setInputMessage('');
    setIsLoading(true);

    // Create optimistic message for immediate display
    const optimisticMessage: Message = {
      id: Date.now(), // Temporary ID
      conversation_id: conversationId || 0,
      content: userMessageContent,
      message_type: 'customer',
      created_at: new Date().toISOString(),
    };

    // Show message immediately (optimistic update)
    setMessages(prev => [...prev, optimisticMessage]);

    try {
      // Create conversation on first message (lazy initialization)
      let activeConversationId = conversationId;
      if (!activeConversationId) {
        try {
          const conversation = await createConversation(customerId);
          activeConversationId = conversation.id;
          setConversationId(activeConversationId);
          // Store conversation ID in localStorage with customer-specific key
          localStorage.setItem(`last_conversation_id_${customerId}`, activeConversationId.toString());
          // Update optimistic message with real conversation_id
          setMessages(prev => prev.map(msg =>
            msg.id === optimisticMessage.id
              ? { ...msg, conversation_id: activeConversationId! }
              : msg
          ));
          // Reload history to show new conversation (after a short delay to ensure DB is updated)
          // But don't auto-load the conversation since we already have messages
          setTimeout(() => {
            loadConversationHistory(customerId, false); // false = don't auto-load conversation
          }, 500);
        } catch (error) {
          console.error('Failed to create conversation:', error);
          // Remove optimistic message on error
          setMessages(prev => prev.filter(msg => msg.id !== optimisticMessage.id));
          setInputMessage(userMessageContent); // Restore input
          setIsLoading(false);
          isSendingRef.current = false;
          return;
        }
      }

      // Send customer message to backend (in background)
      const customerMsgPromise = sendMessage({
        conversation_id: activeConversationId,
        content: userMessageContent,
        message_type: 'customer',
      });

      // Generate AI response (in parallel)
      const aiResponsePromise = generateAIResponse(activeConversationId, userMessageContent);

      // Wait for both to complete
      const [customerMsg, aiResponse] = await Promise.all([
        customerMsgPromise,
        aiResponsePromise,
      ]);

      // Replace optimistic message with real message from backend
      setMessages(prev => prev.map(msg => 
        msg.id === optimisticMessage.id ? customerMsg : msg
      ));

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
        const pendingMsg: Message = {
          id: Date.now(),
          conversation_id: activeConversationId,
          content: 'Your message has been received and is being reviewed by our team. We\'ll respond shortly.',
          message_type: 'final',
          confidence_score: 0,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => [...prev, pendingMsg]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => msg.id !== optimisticMessage.id));
      setInputMessage(userMessageContent); // Restore input
    } finally {
      setIsLoading(false);
      isSendingRef.current = false; // Clear sending flag
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isDefaultPrevented()) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'default';
      case 'resolved':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <div className="max-w-5xl mx-auto h-[calc(100vh-8rem)]">
      <Card className="h-full flex flex-col">
        {/* Header */}
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="py-2 px-2">
              <CardTitle className="pb-1">{getTheme().brandName || 'Customer Support Chat'}</CardTitle>
              <CardDescription className="pt-1">
                We're here to help!
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Sheet open={showHistory} onOpenChange={setShowHistory}>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <SheetTrigger asChild>
                        <Button variant="ghost" size="icon" title="Conversation History">
                          <History className="h-5 w-5" />
                        </Button>
                      </SheetTrigger>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Conversation History</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <SheetContent side="left" className="w-full sm:w-[540px] max-w-[540px]">
                  <SheetHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <SheetTitle>Conversation History</SheetTitle>
                        <SheetDescription>
                          Select a conversation to view messages
                        </SheetDescription>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => customerId && loadConversationHistory(customerId)}
                        title="Refresh"
                      >
                        <History className="h-4 w-4" />
                      </Button>
                    </div>
                  </SheetHeader>
                  <Separator className="my-4" />
                  <ScrollArea className="h-[calc(100vh-8rem)]">
                    {conversationHistory.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
                        <p>No previous conversations</p>
                      </div>
                    ) : (
                      <div className="space-y-2 pr-4">
                        {conversationHistory.map((conv, index) => (
                          <Card
                            key={conv.id}
                            className={cn(
                              "cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02] w-full",
                              conv.id === conversationId && "ring-2 ring-primary shadow-lg scale-[1.02]"
                            )}
                            onClick={() => loadConversation(conv.id)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between mb-2 gap-2">
                                <div className="flex items-center gap-2 min-w-0 flex-1">
                                  <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
                                  <span className="text-sm font-medium">
                                    Chat #{index + 1}
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    (ID: {conv.id})
                                  </span>
                                </div>
                                <Badge variant={getStatusBadgeVariant(conv.status)} className="shrink-0">
                                  {conv.status}
                                </Badge>
                              </div>
                              <p
                                className="text-xs text-muted-foreground mb-2 break-words"
                                style={{
                                  display: '-webkit-box',
                                  WebkitLineClamp: 3,
                                  WebkitBoxOrient: 'vertical',
                                  overflow: 'hidden',
                                  wordBreak: 'break-word'
                                }}
                              >
                                {conv.last_message || 'No messages yet'}
                              </p>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{new Date(conv.created_at).toLocaleDateString()}</span>
                                <span>•</span>
                                <span>{new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </SheetContent>
              </Sheet>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={startNewConversation}
                    >
                      <Plus className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>New Conversation</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </CardHeader>

        {/* Messages */}
        <CardContent className="flex-1 p-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-6 space-y-4">
              {messages.length === 0 && !showHistory && (
                <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
                  <div className="rounded-full bg-primary/10 p-6 mb-4">
                    <Bot className="h-12 w-12 text-primary" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
                  <p className="text-muted-foreground mb-4 max-w-md">
                    Ask about returns, shipping, products, or account help
                  </p>
                  {conversationHistory.length > 0 && (
                    <Button
                      variant="outline"
                      onClick={() => setShowHistory(true)}
                      className="mt-2"
                    >
                      <History className="h-4 w-4 mr-2" />
                      View conversation history
                    </Button>
                  )}
                </div>
              )}

              {messages
                .filter((message) => message.message_type !== 'ai_draft')
                .map((message) => {
                  const isCustomer = message.message_type === 'customer';
                  return (
                    <div
                      key={message.id}
                      className={cn(
                        "flex gap-3",
                        isCustomer ? "justify-end" : "justify-start"
                      )}
                    >
                      {!isCustomer && (
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="bg-primary/10">
                            <Bot className="h-4 w-4 text-primary" />
                          </AvatarFallback>
                        </Avatar>
                      )}
                      <div
                        className={cn(
                          "flex flex-col gap-1 max-w-[70%]",
                          isCustomer && "items-end"
                        )}
                      >
                        <div
                          className={cn(
                            "rounded-lg px-4 py-2 shadow-sm",
                            isCustomer
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                          )}
                        >
                          <p className="text-sm whitespace-pre-wrap break-words">
                            {message.content}
                          </p>
                        </div>
                        <p className="text-xs text-muted-foreground px-1">
                          {new Date(message.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                      {isCustomer && (
                        <Avatar className="h-8 w-8">
                          <AvatarFallback className="bg-primary">
                            <User className="h-4 w-4 text-primary-foreground" />
                          </AvatarFallback>
                        </Avatar>
                      )}
                    </div>
                  );
                })}

              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary/10">
                      <Bot className="h-4 w-4 text-primary" />
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex flex-col gap-1 max-w-[70%]">
                    <div className="rounded-lg px-4 py-2.5 bg-muted shadow-sm">
                      <div className="flex gap-1.5 items-center">
                        <div 
                          className="h-2.5 w-2.5 rounded-full bg-foreground/80" 
                          style={{ 
                            animation: 'loading-dot 1.4s ease-in-out infinite',
                            animationDelay: '0ms'
                          }} 
                        />
                        <div 
                          className="h-2.5 w-2.5 rounded-full bg-foreground/80" 
                          style={{ 
                            animation: 'loading-dot 1.4s ease-in-out infinite',
                            animationDelay: '200ms'
                          }} 
                        />
                        <div 
                          className="h-2.5 w-2.5 rounded-full bg-foreground/80" 
                          style={{ 
                            animation: 'loading-dot 1.4s ease-in-out infinite',
                            animationDelay: '400ms'
                          }} 
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </CardContent>

        <Separator />

        {/* Input */}
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your message..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
