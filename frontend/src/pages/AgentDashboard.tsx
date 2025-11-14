/**
 * Agent Supervision Dashboard
 * Modern Human-in-the-Loop interface for agents to review, edit, and approve AI responses.
 * Demonstrates both pre-send and post-send HITL workflows.
 */
import { useState, useEffect, useRef } from 'react';
import { AlertCircle, CheckCircle, XCircle, Edit2, Send, AlertTriangle, ThumbsDown, ThumbsUp, Trash2, RefreshCw } from 'lucide-react';
import { AdminLogin, useIsAdmin } from '../components/AdminLogin';
import {
  getConversations,
  getConversationMessages,
  sendMessage,
  updateMessage,
  deleteMessage,
  generateAIResponse,
  updateConversation,
  submitFeedback,
  logAgentAction,
  Conversation,
  Message,
} from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import { Label } from '../components/ui/label';
import { Avatar, AvatarFallback } from '../components/ui/avatar';
import { cn } from '../components/ui/utils';

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
  const [finalMessageId, setFinalMessageId] = useState<number | null>(null);
  const [agentCorrection, setAgentCorrection] = useState('');
  const [csatScore, setCsatScore] = useState<number | null>(null);
  const [wasResponseEdited, setWasResponseEdited] = useState(false);
  const [finalResponseContent, setFinalResponseContent] = useState('');

  // Admin authentication state
  const [isAdmin, setIsAdmin] = useState(useIsAdmin());

  // Track in-flight requests to prevent duplicates
  const loadingConversationsRef = useRef(false);
  const loadingMessagesRef = useRef<number | null>(null);

  useEffect(() => {
    loadConversations();
    // Reduce polling frequency to 30 seconds to prevent flickering and reduce load
    // Only poll if there are active conversations to avoid unnecessary requests
    const interval = setInterval(() => {
      if (conversations.length > 0) {
        loadConversations();
      }
    }, 30000); // Refresh every 30s instead of 5s
    return () => clearInterval(interval);
  }, [conversations.length]);

  useEffect(() => {
    if (selectedConvId) {
      loadMessages(selectedConvId);
    }
  }, [selectedConvId]);

  const loadConversations = async () => {
    // Prevent duplicate requests
    if (loadingConversationsRef.current) {
      return;
    }
    loadingConversationsRef.current = true;

    try {
      const convs = await getConversations();
      console.log('Loaded conversations:', convs);

      // Only update state if data has changed to prevent unnecessary re-renders
      setConversations((prevConvs) => {
        const hasChanged = JSON.stringify(prevConvs) !== JSON.stringify(convs || []);
        return hasChanged ? (convs || []) : prevConvs;
      });
    } catch (error: any) {
      console.error('Failed to load conversations:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
      });
      // Show error to user
      if (error.response?.status === 401) {
        console.error('Authentication failed. Check if VITE_API_KEY is set in .env.local and restart the dev server.');
      } else if (error.response?.status === 400) {
        console.error('Bad request. Check if X-Tenant-ID header is being sent correctly.');
      } else if (error.message === 'Network Error' || error.code === 'ECONNREFUSED') {
        console.error('Cannot connect to backend. Ensure backend server is running on http://localhost:8000');
      }
      setConversations([]);
    } finally {
      loadingConversationsRef.current = false;
    }
  };

  const loadMessages = async (convId: number) => {
    // Prevent duplicate requests for the same conversation
    if (loadingMessagesRef.current === convId) {
      return;
    }
    loadingMessagesRef.current = convId;
    
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
    } finally {
      if (loadingMessagesRef.current === convId) {
        loadingMessagesRef.current = null;
      }
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
      let messageId: number | null = null;
      if (aiDraftId) {
        const updatedMessage = await updateMessage(aiDraftId, {
          content: editedResponse,
          message_type: messageType,
          confidence_score: aiConfidence,
          original_ai_content: originalContent,
        });
        messageId = updatedMessage.id;
      } else {
        // Fallback: create new message if no draft exists (shouldn't happen normally)
        const newMessage = await sendMessage({
          conversation_id: selectedConvId,
          content: editedResponse,
          message_type: messageType,
          confidence_score: aiConfidence,
          original_ai_content: originalContent,
        });
        messageId = newMessage.id;
      }

      // Store message ID, editing state, and final content for feedback submission
      setFinalMessageId(messageId);
      setWasResponseEdited(wasEdited);
      setFinalResponseContent(editedResponse); // Store final response before clearing

      // Log agent action
      try {
        await logAgentAction({
          action_type: wasEdited ? 'edit' : 'approve',
          conversation_id: selectedConvId,
          message_id: messageId,
          action_data: {
            was_edited: wasEdited,
            confidence_score: aiConfidence
          }
        });
      } catch (error) {
        console.error('Failed to log agent action:', error);
        // Don't block the flow if logging fails
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
      
      // Log escalate action
      try {
        await logAgentAction({
          action_type: 'escalate',
          conversation_id: selectedConvId,
          message_id: aiDraftId || undefined,
        });
      } catch (error) {
        console.error('Failed to log escalate action:', error);
      }
      
      setAiDraft('');
      setAiDraftId(null);
      setEditedResponse('');
      loadConversations();
      loadMessages(selectedConvId);
    } catch (error) {
      console.error('Failed to escalate:', error);
    }
  };

  const handleResolve = async (csat?: number | null) => {
    if (!selectedConvId) return;

    try {
      await updateConversation(selectedConvId, 'resolved', csat || csatScore);
      loadConversations();
      setShowFeedback(false);
      setCsatScore(null);
    } catch (error) {
      console.error('Failed to resolve:', error);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!selectedConvId || !feedbackRating) return;

    try {
      // Use agent_correction from form if provided, otherwise use final response if it was edited
      const correction = agentCorrection || (wasResponseEdited ? finalResponseContent : undefined);

      await submitFeedback({
        conversation_id: selectedConvId,
        message_id: finalMessageId || undefined,
        rating: feedbackRating,
        agent_correction: correction,
        notes: feedbackNotes,
      });

      // Log reject action if feedback is negative
      if (feedbackRating === 'not_helpful') {
        try {
          await logAgentAction({
            action_type: 'reject',
            conversation_id: selectedConvId,
            message_id: finalMessageId || undefined,
            action_data: {
              rating: feedbackRating,
              has_correction: !!correction
            }
          });
        } catch (error) {
          console.error('Failed to log reject action:', error);
        }
      }

      setShowFeedback(false);
      setFeedbackRating('');
      setFeedbackNotes('');
      setAgentCorrection('');
      setFinalMessageId(null);
      setWasResponseEdited(false);
      setFinalResponseContent('');
      handleResolve(csatScore);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleDeleteMessage = async (messageId: number) => {
    if (!selectedConvId) return;

    // Check if admin
    if (!isAdmin) {
      alert('Admin authentication required. Please login as admin to delete messages.');
      return;
    }

    // Confirm deletion
    if (!window.confirm('Are you sure you want to delete this message? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteMessage(messageId);
      // Reload messages to reflect deletion
      loadMessages(selectedConvId);
      console.log(`✅ Message ${messageId} deleted successfully`);
    } catch (error: any) {
      console.error('Failed to delete message:', error);
      if (error.message?.includes('Admin authentication required')) {
        alert('Admin authentication required. Please login as admin to delete messages.');
        setIsAdmin(false); // Reset admin state to force re-login
      } else if (error.response?.status === 403) {
        alert('Cannot delete customer messages. Only AI-generated or agent messages can be deleted.');
      } else if (error.response?.status === 401) {
        alert('Your admin session has expired. Please login again.');
        setIsAdmin(false);
      } else {
        alert(`Failed to delete message: ${error.message || 'Please try again.'}`);
      }
    }
  };

  const getConfidenceBadge = (confidence: number) => {
    // Auto-send threshold is 65% - responses >= 65% are sent automatically
    if (confidence >= 0.8) {
      return (
        <Badge className="bg-green-600">
          <CheckCircle className="h-3 w-3 mr-1" />
          High Confidence ({(confidence * 100).toFixed(0)}%) - Auto-sent
        </Badge>
      );
    } else if (confidence >= 0.65) {
      return (
        <Badge>
          <CheckCircle className="h-3 w-3 mr-1" />
          Good Confidence ({(confidence * 100).toFixed(0)}%) - Auto-sent
        </Badge>
      );
    } else if (confidence >= 0.5) {
      return (
        <Badge className="bg-yellow-500">
          <AlertTriangle className="h-3 w-3 mr-1" />
          Medium Confidence ({(confidence * 100).toFixed(0)}%) - Needs Review
        </Badge>
      );
    } else {
      return (
        <Badge className="bg-destructive">
          <XCircle className="h-3 w-3 mr-1" />
          Low Confidence ({(confidence * 100).toFixed(0)}%) - Needs Review
        </Badge>
      );
    }
  };

  const selectedConversation = conversations.find(c => c.id === selectedConvId);

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] gap-4">
      {/* Header with Admin Login */}
      <div className="border rounded-lg bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Agent Dashboard</h1>
            <p className="text-sm text-muted-foreground">Review and approve AI responses</p>
          </div>
          <AdminLogin
            onLoginSuccess={(username) => {
              console.log(`Admin logged in: ${username}`);
              setIsAdmin(true);
            }}
            onLogout={() => {
              console.log('Admin logged out');
              setIsAdmin(false);
            }}
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Conversation Queue */}
        <Card className="w-80 flex flex-col overflow-hidden min-w-0">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Conversations</CardTitle>
                <CardDescription>
                  {conversations.length} total conversations
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={loadConversations}
                title="Refresh conversations"
                className="shrink-0"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
        <Separator />
        <ScrollArea className="flex-1 min-w-0">
          <div className="p-3 space-y-2 min-w-0">
            {conversations.map((conv, index) => (
              <button
                key={conv.id}
                onClick={() => setSelectedConvId(conv.id)}
                className={cn(
                  "w-full max-w-full text-left p-3 rounded-lg border transition-all min-w-0",
                  "hover:bg-accent hover:border-primary/50 hover:shadow-sm",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  selectedConvId === conv.id
                    ? "bg-primary/10 border-primary shadow-md ring-2 ring-primary/30"
                    : "bg-card border-border"
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-2 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-foreground shrink-0">
                      Chat #{index + 1}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      (ID: {conv.id})
                    </span>
                  </div>
                  <Badge
                    variant={conv.status === 'active' ? 'default' : conv.status === 'resolved' ? 'secondary' : 'destructive'}
                    className="text-xs shrink-0"
                  >
                    {conv.status}
                  </Badge>
                </div>
                <p
                  className="text-xs text-muted-foreground mb-2 leading-relaxed overflow-hidden min-w-0"
                  style={{
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    wordBreak: 'break-word'
                  }}
                >
                  {conv.last_message || 'No messages'}
                </p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>{new Date(conv.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </button>
            ))}
          </div>
        </ScrollArea>
      </Card>

      {/* Main Chat Area */}
      <Card className="flex-1 flex flex-col">
        {selectedConvId ? (
          <>
            {/* Header */}
            <CardHeader>
              <div className="flex items-center justify-between min-w-0">
                <div className="min-w-0 flex-1">
                  <CardTitle>
                    Chat #{conversations.findIndex(c => c.id === selectedConvId) + 1}
                    <span className="text-sm text-muted-foreground font-normal ml-2">(ID: {selectedConvId})</span>
                  </CardTitle>
                  <CardDescription>
                    Customer: {selectedConversation?.customer_id}
                  </CardDescription>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleEscalate}
                    className="border-red-500 text-red-600 hover:bg-red-50"
                  >
                    <AlertCircle className="h-4 w-4 mr-2" />
                    Escalate
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleResolve()}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Resolve
                  </Button>
                </div>
              </div>
            </CardHeader>

            {/* Messages */}
            <CardContent className="flex-1 p-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-6 space-y-4">
                  {messages.filter(m => m.message_type !== 'ai_draft').map((msg) => {
                    const isCustomer = msg.message_type === 'customer';
                    return (
                      <div
                        key={msg.id}
                        className={cn(
                          "flex gap-3 group",
                          isCustomer ? "justify-end" : "justify-start"
                        )}
                      >
                        {!isCustomer && (
                          <Avatar className="h-8 w-8">
                            <AvatarFallback className="bg-muted">
                              AI
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
                              "rounded-lg px-4 py-2 shadow-sm relative",
                              isCustomer
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted"
                            )}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">
                              {msg.content}
                            </p>
                            {!isCustomer && isAdmin && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="absolute -top-2 -right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                onClick={() => handleDeleteMessage(msg.id)}
                                title="Delete message (Admin only)"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                          <div className="flex items-center gap-2 px-1">
                            <p className="text-xs text-muted-foreground">
                              {new Date(msg.created_at).toLocaleTimeString()}
                            </p>
                            {msg.confidence_score !== undefined && msg.confidence_score !== null && (
                              <span className="text-xs text-muted-foreground">
                                {msg.message_type === 'agent_edited' ? '✏️ Edited' : ''}
                              </span>
                            )}
                          </div>
                        </div>
                        {isCustomer && (
                          <Avatar className="h-8 w-8">
                            <AvatarFallback className="bg-primary">
                              C
                            </AvatarFallback>
                          </Avatar>
                        )}
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </CardContent>

            {/* AI Draft Review Section */}
            {aiDraft && (
              <>
                <Separator />
                <CardContent className="p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">AI Draft Response</CardTitle>
                    {getConfidenceBadge(aiConfidence)}
                  </div>

                  {!isEditMode ? (
                    <Alert>
                      <AlertDescription className="whitespace-pre-wrap">
                        {editedResponse}
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Textarea
                      value={editedResponse}
                      onChange={(e) => setEditedResponse(e.target.value)}
                      rows={4}
                      className="resize-none"
                    />
                  )}

                  <div className="flex gap-2">
                    {!isEditMode ? (
                      <>
                        <Button
                          onClick={() => handleSendResponse(false)}
                          className="flex-1"
                        >
                          <Send className="h-4 w-4 mr-2" />
                          Send as-is
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => setIsEditMode(true)}
                          className="flex-1"
                        >
                          <Edit2 className="h-4 w-4 mr-2" />
                          Edit & Send
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          onClick={() => handleSendResponse(true)}
                          className="flex-1"
                        >
                          Send Edited Response
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setIsEditMode(false);
                            setEditedResponse(aiDraft);
                          }}
                        >
                          Cancel
                        </Button>
                      </>
                    )}
                  </div>
                </CardContent>
              </>
            )}

            {/* Feedback Dialog */}
            <Dialog open={showFeedback} onOpenChange={setShowFeedback}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Provide Feedback on AI Response</DialogTitle>
                  <DialogDescription>
                    Your feedback helps improve the AI model
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div>
                    <Label>Rating</Label>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant={feedbackRating === 'helpful' ? 'default' : 'outline'}
                        onClick={() => setFeedbackRating('helpful')}
                        className={cn(
                          feedbackRating === 'helpful' && 'bg-green-600 hover:bg-green-700'
                        )}
                      >
                        <ThumbsUp className="h-4 w-4 mr-2" />
                        Helpful
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setFeedbackRating('not_helpful')}
                        className={cn(
                          feedbackRating === 'not_helpful' && 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                        )}
                      >
                        <ThumbsDown className="h-4 w-4 mr-2" />
                        Not Helpful
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setFeedbackRating('needs_improvement')}
                        className={cn(
                          feedbackRating === 'needs_improvement' && 'bg-yellow-500 hover:bg-yellow-600'
                        )}
                      >
                        <AlertTriangle className="h-4 w-4 mr-2" />
                        Needs Improvement
                      </Button>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="agent-correction">Agent Correction (optional)</Label>
                    <Textarea
                      id="agent-correction"
                      value={agentCorrection}
                      onChange={(e) => setAgentCorrection(e.target.value)}
                      rows={3}
                      placeholder="What would you have said instead? (This helps calculate BLEU and semantic similarity)"
                      className="mt-2"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Provide your version of the response to help evaluate AI quality
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="notes">Additional Notes (optional)</Label>
                    <Textarea
                      id="notes"
                      value={feedbackNotes}
                      onChange={(e) => setFeedbackNotes(e.target.value)}
                      rows={3}
                      placeholder="What could be improved?"
                      className="mt-2"
                    />
                  </div>
                  <div>
                    <Label htmlFor="csat">Customer Satisfaction (CSAT) Score</Label>
                    <div className="flex gap-2 mt-2">
                      {[1, 2, 3, 4, 5].map((score) => (
                        <Button
                          key={score}
                          type="button"
                          variant={csatScore === score ? 'default' : 'outline'}
                          onClick={() => setCsatScore(score)}
                          className={cn(
                            csatScore === score && 'bg-yellow-500 hover:bg-yellow-600'
                          )}
                        >
                          {score}
                        </Button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Rate customer satisfaction (1-5 scale)
                    </p>
                  </div>
                </div>
                <DialogFooter className="gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowFeedback(false);
                      handleResolve(csatScore);
                    }}
                  >
                    Skip Feedback
                  </Button>
                  <Button
                    onClick={handleSubmitFeedback}
                    disabled={!feedbackRating || !csatScore}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Submit Feedback
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        ) : (
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-2">
              <p className="text-muted-foreground">Select a conversation to view</p>
            </div>
          </CardContent>
        )}
      </Card>
      </div>
    </div>
  );
}
