/**
 * Customer Chat Interface
 * Modern chat UI for customers to interact with AI support assistant.
 * Includes conversation history to allow customers to return to previous chats.
 */
import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, History, Plus, MessageSquare } from 'lucide-react';
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
              <CardTitle className="pb-1">Customer Support Chat</CardTitle>
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
                    <SheetTitle>Conversation History</SheetTitle>
                    <SheetDescription>
                      Select a conversation to view messages
                    </SheetDescription>
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
                        {conversationHistory.map((conv) => (
                          <Card
                            key={conv.id}
                            className={cn(
                              "cursor-pointer transition-all hover:shadow-md w-full",
                              conv.id === conversationId && "ring-2 ring-primary"
                            )}
                            onClick={() => loadConversation(conv.id)}
                          >
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between mb-2 gap-2">
                                <div className="flex items-center gap-2 min-w-0 flex-1">
                                  <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
                                  <span className="text-sm font-medium">
                                    Conversation #{conv.id}
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
                              <p className="text-xs text-muted-foreground">
                                {new Date(conv.created_at).toLocaleDateString()} at{' '}
                                {new Date(conv.created_at).toLocaleTimeString()}
                              </p>
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
              onKeyPress={handleKeyPress}
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
