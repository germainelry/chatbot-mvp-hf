/**
 * Knowledge Base Management
 * Modern interface for agents to add/edit/delete knowledge base articles.
 * Simple RAG implementation for AI context.
 */
import { useState, useEffect, useRef } from 'react';
import { Plus, Edit2, Trash2, Search, BookOpen, Save, X, Lightbulb } from 'lucide-react';
import {
  getKnowledgeArticles,
  createKnowledgeArticle,
  updateKnowledgeArticle,
  deleteKnowledgeArticle,
  KnowledgeArticle,
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { PageHeader } from '../components/layout/PageHeader';

export default function KnowledgeBase() {
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);
  const [editingArticle, setEditingArticle] = useState<Partial<KnowledgeArticle>>({
    title: '',
    content: '',
    category: '',
    tags: '',
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [articleToDelete, setArticleToDelete] = useState<number | null>(null);
  const loadingRef = useRef(false);

  useEffect(() => {
    loadArticles();
  }, [selectedCategory, searchTerm]);

  const loadArticles = async () => {
    // Prevent duplicate requests
    if (loadingRef.current) {
      return;
    }
    loadingRef.current = true;
    
    try {
      const data = await getKnowledgeArticles(
        selectedCategory || undefined,
        searchTerm || undefined
      );
      setArticles(data);
    } catch (error) {
      console.error('Failed to load articles:', error);
    } finally {
      loadingRef.current = false;
    }
  };

  const handleSave = async () => {
    try {
      if (editingArticle.id) {
        // Update existing
        await updateKnowledgeArticle(editingArticle.id, editingArticle);
      } else {
        // Create new
        await createKnowledgeArticle({
          title: editingArticle.title!,
          content: editingArticle.content!,
          category: editingArticle.category!,
          tags: editingArticle.tags || '',
        });
      }
      setIsEditing(false);
      setEditingArticle({ title: '', content: '', category: '', tags: '' });
      loadArticles();
    } catch (error) {
      console.error('Failed to save article:', error);
    }
  };

  const handleEdit = (article: KnowledgeArticle) => {
    setEditingArticle(article);
    setIsEditing(true);
  };

  const handleDeleteClick = (id: number) => {
    setArticleToDelete(id);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!articleToDelete) return;
    
    try {
      await deleteKnowledgeArticle(articleToDelete);
      loadArticles();
      setDeleteDialogOpen(false);
      setArticleToDelete(null);
    } catch (error) {
      console.error('Failed to delete article:', error);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditingArticle({ title: '', content: '', category: '', tags: '' });
  };

  const categories = ['Returns', 'Shipping', 'Account', 'Products', 'Billing', 'Technical'];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Knowledge Base"
        description="Manage articles for AI reference"
      />

      {!isEditing ? (
        <>
          {/* Search and Filters */}
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            <div className="flex-1 relative w-full md:w-auto">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
              <Input
                type="text"
                placeholder="Search articles..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-full"
              />
            </div>
            <Select value={selectedCategory || "all"} onValueChange={(value) => setSelectedCategory(value === "all" ? "" : value)}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button onClick={() => setIsEditing(true)} className="w-full md:w-auto">
              <Plus className="h-4 w-4 mr-2" />
              New Article
            </Button>
          </div>

          {/* Articles Grid */}
          {articles.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No articles found. Add your first article!</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((article) => (
                <Card key={article.id} className="hover:shadow-lg transition-all duration-200 flex flex-col">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <CardTitle className="text-lg leading-tight flex-1">{article.title}</CardTitle>
                    </div>
                    <Badge variant="secondary" className="w-fit text-xs">
                      {article.category}
                    </Badge>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <p 
                      className="text-sm text-muted-foreground mb-3 flex-1"
                      style={{
                        display: '-webkit-box',
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        wordBreak: 'break-word'
                      }}
                    >
                      {article.content}
                    </p>
                    {article.tags && (
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {article.tags.split(',').slice(0, 5).map((tag, i) => (
                          <Badge key={i} variant="outline" className="text-xs font-normal">
                            {tag.trim()}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center justify-between pt-2 border-t">
                      <p className="text-xs text-muted-foreground">
                        {new Date(article.updated_at).toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' })}
                      </p>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(article)}
                          className="h-7 w-7"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteClick(article.id)}
                          className="h-7 w-7 text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      ) : (
        /* Edit/Create Form */
        <Card>
          <CardHeader>
            <CardTitle>
              {editingArticle.id ? 'Edit Article' : 'New Article'}
            </CardTitle>
            <CardDescription>
              {editingArticle.id 
                ? 'Update the article content and metadata'
                : 'Create a new knowledge base article'}
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                type="text"
                value={editingArticle.title}
                onChange={(e) =>
                  setEditingArticle({ ...editingArticle, title: e.target.value })
                }
                placeholder="e.g., Return & Refund Policy"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category *</Label>
              <Select
                value={editingArticle.category}
                onValueChange={(value) =>
                  setEditingArticle({ ...editingArticle, category: value })
                }
              >
                <SelectTrigger id="category">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="content">Content *</Label>
              <Textarea
                id="content"
                value={editingArticle.content}
                onChange={(e) =>
                  setEditingArticle({ ...editingArticle, content: e.target.value })
                }
                rows={12}
                placeholder="Article content..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                type="text"
                value={editingArticle.tags}
                onChange={(e) =>
                  setEditingArticle({ ...editingArticle, tags: e.target.value })
                }
                placeholder="return, refund, policy, 30 days"
              />
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleSave}
                disabled={
                  !editingArticle.title ||
                  !editingArticle.content ||
                  !editingArticle.category
                }
                className="flex-1"
              >
                <Save className="h-4 w-4 mr-2" />
                Save Article
              </Button>
              <Button variant="outline" onClick={handleCancel}>
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Info Box */}
      {!isEditing && (
        <Alert>
          <BookOpen className="h-4 w-4" />
          <AlertTitle className="flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            Knowledge Base Tips
          </AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside space-y-1 mt-2">
              <li>Articles are used by AI to generate contextual responses</li>
              <li>Use descriptive tags for better keyword matching</li>
              <li>Keep content clear and concise for optimal AI comprehension</li>
              <li>Review and update articles based on agent feedback</li>
              <li>In production, would use vector embeddings for semantic search</li>
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the article
              from the knowledge base.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
