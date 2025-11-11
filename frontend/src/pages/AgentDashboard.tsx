/**
 * Agent Supervision Dashboard
 * Modern Human-in-the-Loop interface for agents to review, edit, and approve AI responses.
 * Demonstrates both pre-send and post-send HITL workflows.
 */
import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, XCircle, Edit2, Send, AlertTriangle, ThumbsDown, ThumbsUp } from 'lucide-react';
import {
  getConversations,
  getConversationMessages,
  sendMessage,
  updateMessage,
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
          message_id: aiDraftId || null,
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
    <div className="h-[calc(100vh-8rem)] flex gap-4">
      {/* Conversation Queue */}
      <Card className="w-80 flex flex-col overflow-hidden min-w-0">
        <CardHeader className="pb-3">
          <CardTitle>Conversations</CardTitle>
          <CardDescription>
            {conversations.length} total conversations
          </CardDescription>
        </CardHeader>
        <Separator />
        <ScrollArea className="flex-1 min-w-0">
          <div className="p-3 space-y-2 min-w-0">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setSelectedConvId(conv.id)}
                className={cn(
                  "w-full max-w-full text-left p-3 rounded-lg border transition-all min-w-0",
                  "hover:bg-accent hover:border-primary/50",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  selectedConvId === conv.id
                    ? "bg-primary/5 border-primary shadow-sm ring-1 ring-primary/20"
                    : "bg-card border-border"
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-2 min-w-0">
                  <span className="font-semibold text-sm text-foreground shrink-0">#{conv.id}</span>
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
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
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
                  <CardTitle>Conversation #{selectedConvId}</CardTitle>
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
                    onClick={handleResolve}
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
                          "flex gap-3",
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
                              "rounded-lg px-4 py-2 shadow-sm",
                              isCustomer
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted"
                            )}
                          >
                            <p className="text-sm whitespace-pre-wrap break-words">
                              {msg.content}
                            </p>
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
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowFeedback(false);
                      handleResolve(csatScore);
                    }}
                  >
                    Skip
                  </Button>
                  <Button
                    onClick={handleSubmitFeedback}
                    disabled={!feedbackRating}
                  >
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
  );
}
