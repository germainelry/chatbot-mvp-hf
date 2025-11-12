/**
 * Configuration Page
 * Manage tenant settings: LLM, Knowledge Base, UI customization, and advanced settings.
 */
import { useState, useEffect, useRef } from 'react';
import { Brain, Database, Palette, Sliders, Save, TestTube, Loader2, Upload, FileText, CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';
import { toast } from 'sonner';
import {
  getTenantConfiguration,
  updateTenantConfiguration,
  listLLMProviders,
  listLLMModels,
  testLLMConnection,
  listEmbeddingModels,
  EmbeddingModel,
  uploadPDF,
  uploadCSV,
  uploadDocument,
  createDatabaseConnection,
  listDatabaseConnections,
  getDatabaseTables,
  syncDatabaseTable,
  listTenants,
  TenantConfiguration as TenantConfigType,
  DatabaseConnection,
  TableInfo,
} from '../services/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { PageHeader } from '../components/layout/PageHeader';
import { applyTheme } from '../config/theme';
import { Progress } from '../components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';

const DEFAULT_TENANT_ID = 1; // Default tenant ID

export default function Configuration() {
  const [activeTab, setActiveTab] = useState('llm');
  const [selectedTenantId, setSelectedTenantId] = useState<number>(DEFAULT_TENANT_ID);
  const [tenants, setTenants] = useState<Array<{ id: number; name: string; slug: string }>>([]);
  const [config, setConfig] = useState<TenantConfigType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModel[]>([]);
  const [testingLLM, setTestingLLM] = useState(false);
  const [dbConnections, setDbConnections] = useState<DatabaseConnection[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<number | null>(null);
  const [tables, setTables] = useState<TableInfo[]>([]);
  
  // Enhanced upload state management
  const [uploadingPDF, setUploadingPDF] = useState(false);
  const [uploadingCSV, setUploadingCSV] = useState(false);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ pdf: number; csv: number; document: number }>({
    pdf: 0,
    csv: 0,
    document: 0,
  });
  const [uploadStatus, setUploadStatus] = useState<{ pdf: 'idle' | 'uploading' | 'success' | 'error'; csv: 'idle' | 'uploading' | 'success' | 'error'; document: 'idle' | 'uploading' | 'success' | 'error' }>({
    pdf: 'idle',
    csv: 'idle',
    document: 'idle',
  });
  const [selectedFiles, setSelectedFiles] = useState<{ pdf: File | null; csv: File | null; document: File | null }>({
    pdf: null,
    csv: null,
    document: null,
  });
  
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  // File input refs
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const documentInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadTenants();
    loadConfiguration();
    loadProviders();
    loadEmbeddingModels();
  }, []);

  useEffect(() => {
    if (selectedTenantId) {
      loadConfiguration();
    }
  }, [selectedTenantId]);

  useEffect(() => {
    if (config?.llm_provider) {
      loadModels(config.llm_provider);
    }
  }, [config?.llm_provider]);

  const loadTenants = async () => {
    try {
      const data = await listTenants();
      setTenants(data);
    } catch (error) {
      console.error('Failed to load tenants:', error);
    }
  };

  const loadConfiguration = async () => {
    try {
      const data = await getTenantConfiguration(selectedTenantId);
      setConfig(data);
      applyTheme(data);
    } catch (error) {
      console.error('Failed to load configuration:', error);
      setAlert({ type: 'error', message: 'Failed to load configuration' });
    } finally {
      setLoading(false);
    }
  };

  const loadProviders = async () => {
    try {
      const data = await listLLMProviders();
      setProviders(data.providers);
    } catch (error) {
      console.error('Failed to load providers:', error);
    }
  };

  const loadModels = async (provider: string) => {
    try {
      const data = await listLLMModels(provider);
      setModels(data.models);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadEmbeddingModels = async () => {
    try {
      const data = await listEmbeddingModels();
      setEmbeddingModels(data.models);
    } catch (error) {
      console.error('Failed to load embedding models:', error);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    
    setSaving(true);
    try {
      const updated = await updateTenantConfiguration(selectedTenantId, config);
      setConfig(updated);
      applyTheme(updated);
      setAlert({ type: 'success', message: 'Configuration saved successfully' });
      setTimeout(() => setAlert(null), 3000);
    } catch (error) {
      console.error('Failed to save configuration:', error);
      setAlert({ type: 'error', message: 'Failed to save configuration' });
      setTimeout(() => setAlert(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleTestLLM = async () => {
    if (!config) return;
    
    // Validate API key for cloud providers
    if ((config.llm_provider === 'openai' || config.llm_provider === 'anthropic') && !config.llm_config?.api_key) {
      setAlert({ type: 'error', message: 'API key is required for cloud providers' });
      setTimeout(() => setAlert(null), 3000);
      return;
    }
    
    setTestingLLM(true);
    try {
      const result = await testLLMConnection({
        provider: config.llm_provider,
        model: config.llm_model_name,
        config: config.llm_config,
      });
      
      setAlert({ type: result.success ? 'success' : 'error', message: result.message });
      setTimeout(() => setAlert(null), 3000);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to test LLM connection';
      setAlert({ type: 'error', message: errorMessage });
      setTimeout(() => setAlert(null), 3000);
    } finally {
      setTestingLLM(false);
    }
  };

  const handleFileSelect = (file: File, type: 'pdf' | 'csv' | 'document') => {
    setSelectedFiles(prev => ({ ...prev, [type]: file }));
    setUploadStatus(prev => ({ ...prev, [type]: 'idle' }));
    // Auto-upload on file selection
    handleFileUpload(file, type);
  };

  const handleFileUpload = async (file: File, type: 'pdf' | 'csv' | 'document') => {
    // Set uploading state for specific type
    if (type === 'pdf') {
      setUploadingPDF(true);
      setUploadStatus(prev => ({ ...prev, pdf: 'uploading' }));
    } else if (type === 'csv') {
      setUploadingCSV(true);
      setUploadStatus(prev => ({ ...prev, csv: 'uploading' }));
    } else {
      setUploadingDocument(true);
      setUploadStatus(prev => ({ ...prev, document: 'uploading' }));
    }
    
    // Simulate progress (since backend doesn't provide progress events)
    const progressInterval = setInterval(() => {
      setUploadProgress(prev => ({
        ...prev,
        [type]: Math.min(prev[type] + 10, 90),
      }));
    }, 200);
    
    try {
      let result;
      if (type === 'pdf') {
        result = await uploadPDF(file);
      } else if (type === 'csv') {
        result = await uploadCSV(file);
      } else {
        result = await uploadDocument(file);
      }
      
      // Complete progress
      setUploadProgress(prev => ({ ...prev, [type]: 100 }));
      clearInterval(progressInterval);
      
      // Set success state
      setUploadStatus(prev => ({ ...prev, [type]: 'success' }));
      
      // Show toast notification
      toast.success('Upload Successful', {
        description: `${result.articles_created} articles created from ${file.name}`,
      });
      
      // Reset after 2 seconds
      setTimeout(() => {
        setUploadStatus(prev => ({ ...prev, [type]: 'idle' }));
        setUploadProgress(prev => ({ ...prev, [type]: 0 }));
        setSelectedFiles(prev => ({ ...prev, [type]: null }));
        // Reset file input
        if (type === 'pdf' && pdfInputRef.current) {
          pdfInputRef.current.value = '';
        } else if (type === 'csv' && csvInputRef.current) {
          csvInputRef.current.value = '';
        } else if (type === 'document' && documentInputRef.current) {
          documentInputRef.current.value = '';
        }
      }, 2000);
    } catch (error: any) {
      clearInterval(progressInterval);
      setUploadProgress(prev => ({ ...prev, [type]: 0 }));
      setUploadStatus(prev => ({ ...prev, [type]: 'error' }));
      
      // Show error toast
      toast.error('Upload Failed', {
        description: error.response?.data?.detail || `Failed to upload ${file.name}`,
      });
      
      // Reset error state after 3 seconds
      setTimeout(() => {
        setUploadStatus(prev => ({ ...prev, [type]: 'idle' }));
        setSelectedFiles(prev => ({ ...prev, [type]: null }));
      }, 3000);
    } finally {
      if (type === 'pdf') {
        setUploadingPDF(false);
      } else if (type === 'csv') {
        setUploadingCSV(false);
      } else {
        setUploadingDocument(false);
      }
    }
  };
  
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const loadDatabaseConnections = async () => {
    try {
      const connections = await listDatabaseConnections();
      setDbConnections(connections);
    } catch (error) {
      console.error('Failed to load database connections:', error);
    }
  };

  const loadTables = async (connectionId: number) => {
    try {
      const tableList = await getDatabaseTables(connectionId);
      setTables(tableList);
    } catch (error) {
      console.error('Failed to load tables:', error);
    }
  };

  useEffect(() => {
    if (activeTab === 'database') {
      loadDatabaseConnections();
    }
  }, [activeTab]);

  useEffect(() => {
    if (selectedConnection) {
      loadTables(selectedConnection);
    }
  }, [selectedConnection]);

  if (loading || !config) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuration"
        description="Manage LLM, Knowledge Base, UI, and advanced settings"
      />

      {/* Tenant Selector */}
      {tenants.length > 1 && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              <Label htmlFor="tenant-select">Select Tenant</Label>
              <Select
                value={selectedTenantId.toString()}
                onValueChange={(value) => setSelectedTenantId(parseInt(value))}
              >
                <SelectTrigger id="tenant-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {tenants.map((tenant) => (
                    <SelectItem key={tenant.id} value={tenant.id.toString()}>
                      {tenant.name} ({tenant.slug})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      {alert && (
        <Alert variant={alert.type === 'error' ? 'destructive' : 'default'}>
          <AlertTitle>{alert.type === 'error' ? 'Error' : 'Success'}</AlertTitle>
          <AlertDescription>{alert.message}</AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="llm">
            <Brain className="h-4 w-4 mr-2" />
            LLM Configuration
          </TabsTrigger>
          <TabsTrigger value="knowledge">
            <Database className="h-4 w-4 mr-2" />
            Knowledge Base
          </TabsTrigger>
          <TabsTrigger value="ui">
            <Palette className="h-4 w-4 mr-2" />
            UI Customization
          </TabsTrigger>
          <TabsTrigger value="advanced">
            <Sliders className="h-4 w-4 mr-2" />
            Advanced
          </TabsTrigger>
        </TabsList>

        {/* LLM Configuration */}
        <TabsContent value="llm" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>LLM Provider Settings</CardTitle>
              <CardDescription>Configure the language model provider and model</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Select
                  value={config.llm_provider}
                  onValueChange={(value) => {
                    setConfig({ ...config, llm_provider: value });
                    loadModels(value);
                  }}
                >
                  <SelectTrigger id="provider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((provider) => (
                      <SelectItem key={provider} value={provider}>
                        <div className="flex items-center gap-2">
                          <span className="capitalize">{provider}</span>
                          {(provider === 'openai' || provider === 'anthropic') && (
                            <span className="text-xs text-muted-foreground">(Cloud)</span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Select
                  value={config.llm_model_name}
                  onValueChange={(value) => setConfig({ ...config, llm_model_name: value })}
                >
                  <SelectTrigger id="model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* API Key input for cloud providers */}
              {(config.llm_provider === 'openai' || config.llm_provider === 'anthropic') && (
                <div className="space-y-2">
                  <Label htmlFor="apiKey">
                    API Key {config.llm_provider === 'openai' ? '(OpenAI)' : '(Anthropic)'}
                  </Label>
                  <Input
                    id="apiKey"
                    type="password"
                    value={config.llm_config?.api_key || ''}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        llm_config: { ...config.llm_config, api_key: e.target.value },
                      })
                    }
                    placeholder={`Enter your ${config.llm_provider} API key`}
                  />
                  <p className="text-sm text-muted-foreground">
                    Your API key is stored securely and only used for LLM requests.
                  </p>
                </div>
              )}

              {/* Base URL for OpenAI (Azure support) */}
              {config.llm_provider === 'openai' && (
                <div className="space-y-2">
                  <Label htmlFor="baseUrl">Base URL (Optional)</Label>
                  <Input
                    id="baseUrl"
                    value={config.llm_config?.base_url || ''}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        llm_config: { ...config.llm_config, base_url: e.target.value },
                      })
                    }
                    placeholder="Leave empty for OpenAI, or enter Azure OpenAI endpoint"
                  />
                  <p className="text-sm text-muted-foreground">
                    Optional: For Azure OpenAI or custom endpoints.
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <Button onClick={handleTestLLM} disabled={testingLLM} variant="outline">
                  <TestTube className="h-4 w-4 mr-2" />
                  {testingLLM ? 'Testing...' : 'Test Connection'}
                </Button>
                <Button onClick={handleSave} disabled={saving}>
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Knowledge Base */}
        <TabsContent value="knowledge" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>File Upload</CardTitle>
              <CardDescription>
                Upload PDF, CSV, or documents to add to your knowledge base. Files are automatically processed and converted into searchable articles.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <TooltipProvider>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* PDF Upload */}
                  <div className="space-y-3 border rounded-lg p-4 transition-all hover:border-primary/50">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="pdf-upload" className="text-base font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4 text-red-500" />
                        Upload PDF
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            Upload PDF documents (manuals, guides, reports). The system will extract text and create searchable articles.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Best for: Manuals, guides, reports, and structured documents
                    </p>
                    <input
                      ref={pdfInputRef}
                      id="pdf-upload"
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileSelect(file, 'pdf');
                      }}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-label="Upload PDF file"
                    />
                    <Button
                      type="button"
                      variant={uploadStatus.pdf === 'success' ? 'default' : uploadStatus.pdf === 'error' ? 'destructive' : 'outline'}
                      className="w-full transition-all duration-300 relative overflow-hidden"
                      onClick={() => pdfInputRef.current?.click()}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-busy={uploadingPDF}
                      aria-disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                    >
                      {uploadingPDF ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : uploadStatus.pdf === 'success' ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          <span>Upload Complete</span>
                        </>
                      ) : uploadStatus.pdf === 'error' ? (
                        <>
                          <AlertCircle className="h-4 w-4 mr-2" />
                          <span>Upload Failed</span>
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          <span>Choose PDF File</span>
                        </>
                      )}
                    </Button>
                    {selectedFiles.pdf && (
                      <div className="text-sm text-muted-foreground animate-in fade-in-50">
                        <p className="truncate font-medium">{selectedFiles.pdf.name}</p>
                        <p className="text-xs">{formatFileSize(selectedFiles.pdf.size)}</p>
                      </div>
                    )}
                    {uploadingPDF && (
                      <div className="space-y-1 animate-in fade-in-50">
                        <Progress value={uploadProgress.pdf} className="h-2" />
                        <p className="text-xs text-muted-foreground text-center">{uploadProgress.pdf}%</p>
                      </div>
                    )}
                    <div 
                      className="text-xs text-muted-foreground"
                      aria-live="polite"
                      aria-atomic="true"
                    >
                      {uploadingPDF && 'Processing your PDF file...'}
                      {uploadStatus.pdf === 'success' && 'PDF processed successfully!'}
                      {uploadStatus.pdf === 'error' && 'Failed to process PDF. Please try again.'}
                    </div>
                  </div>

                  {/* CSV Upload */}
                  <div className="space-y-3 border rounded-lg p-4 transition-all hover:border-primary/50">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="csv-upload" className="text-base font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4 text-green-500" />
                        Upload CSV
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            Upload CSV files with structured data. Each row will be converted into a knowledge article. Ensure your CSV has headers.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Best for: Structured data, FAQs, product catalogs, and tabular information
                    </p>
                    <input
                      ref={csvInputRef}
                      id="csv-upload"
                      type="file"
                      accept=".csv"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileSelect(file, 'csv');
                      }}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-label="Upload CSV file"
                    />
                    <Button
                      type="button"
                      variant={uploadStatus.csv === 'success' ? 'default' : uploadStatus.csv === 'error' ? 'destructive' : 'outline'}
                      className="w-full transition-all duration-300 relative overflow-hidden"
                      onClick={() => csvInputRef.current?.click()}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-busy={uploadingCSV}
                      aria-disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                    >
                      {uploadingCSV ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : uploadStatus.csv === 'success' ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          <span>Upload Complete</span>
                        </>
                      ) : uploadStatus.csv === 'error' ? (
                        <>
                          <AlertCircle className="h-4 w-4 mr-2" />
                          <span>Upload Failed</span>
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          <span>Choose CSV File</span>
                        </>
                      )}
                    </Button>
                    {selectedFiles.csv && (
                      <div className="text-sm text-muted-foreground animate-in fade-in-50">
                        <p className="truncate font-medium">{selectedFiles.csv.name}</p>
                        <p className="text-xs">{formatFileSize(selectedFiles.csv.size)}</p>
                      </div>
                    )}
                    {uploadingCSV && (
                      <div className="space-y-1 animate-in fade-in-50">
                        <Progress value={uploadProgress.csv} className="h-2" />
                        <p className="text-xs text-muted-foreground text-center">{uploadProgress.csv}%</p>
                      </div>
                    )}
                    <div 
                      className="text-xs text-muted-foreground"
                      aria-live="polite"
                      aria-atomic="true"
                    >
                      {uploadingCSV && 'Processing your CSV file...'}
                      {uploadStatus.csv === 'success' && 'CSV processed successfully!'}
                      {uploadStatus.csv === 'error' && 'Failed to process CSV. Please try again.'}
                    </div>
                  </div>

                  {/* Document Upload */}
                  <div className="space-y-3 border rounded-lg p-4 transition-all hover:border-primary/50">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="document-upload" className="text-base font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-500" />
                        Upload Document
                      </Label>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            Upload text documents (.txt, .md, .docx). Markdown files are especially well-supported and preserve formatting.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Best for: Text files, markdown documents, and Word documents
                    </p>
                    <input
                      ref={documentInputRef}
                      id="document-upload"
                      type="file"
                      accept=".txt,.md,.markdown,.docx"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileSelect(file, 'document');
                      }}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-label="Upload document file"
                    />
                    <Button
                      type="button"
                      variant={uploadStatus.document === 'success' ? 'default' : uploadStatus.document === 'error' ? 'destructive' : 'outline'}
                      className="w-full transition-all duration-300 relative overflow-hidden"
                      onClick={() => documentInputRef.current?.click()}
                      disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                      aria-busy={uploadingDocument}
                      aria-disabled={uploadingPDF || uploadingCSV || uploadingDocument}
                    >
                      {uploadingDocument ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : uploadStatus.document === 'success' ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          <span>Upload Complete</span>
                        </>
                      ) : uploadStatus.document === 'error' ? (
                        <>
                          <AlertCircle className="h-4 w-4 mr-2" />
                          <span>Upload Failed</span>
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          <span>Choose Document</span>
                        </>
                      )}
                    </Button>
                    {selectedFiles.document && (
                      <div className="text-sm text-muted-foreground animate-in fade-in-50">
                        <p className="truncate font-medium">{selectedFiles.document.name}</p>
                        <p className="text-xs">{formatFileSize(selectedFiles.document.size)}</p>
                      </div>
                    )}
                    {uploadingDocument && (
                      <div className="space-y-1 animate-in fade-in-50">
                        <Progress value={uploadProgress.document} className="h-2" />
                        <p className="text-xs text-muted-foreground text-center">{uploadProgress.document}%</p>
                      </div>
                    )}
                    <div 
                      className="text-xs text-muted-foreground"
                      aria-live="polite"
                      aria-atomic="true"
                    >
                      {uploadingDocument && 'Processing your document...'}
                      {uploadStatus.document === 'success' && 'Document processed successfully!'}
                      {uploadStatus.document === 'error' && 'Failed to process document. Please try again.'}
                    </div>
                  </div>
                </div>
              </TooltipProvider>
              
              <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-dashed">
                <p className="text-sm font-medium mb-2">File Upload Guidelines:</p>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Maximum file size: 10MB per file (recommended)</li>
                  <li>PDF files should be text-based (not scanned images)</li>
                  <li>CSV files should include headers in the first row</li>
                  <li>Documents are automatically chunked into searchable articles</li>
                  <li>Processing time varies based on file size and complexity</li>
                </ul>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Database Connections</CardTitle>
              <CardDescription>
                Connect external databases to import data into your knowledge base. Select tables and columns to sync.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <DatabaseConnectionForm onSuccess={loadDatabaseConnections} />
              {dbConnections.length > 0 && (
                <div className="space-y-2">
                  <Label>Select Connection</Label>
                  <Select
                    value={selectedConnection?.toString() || ''}
                    onValueChange={(value) => setSelectedConnection(parseInt(value))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a connection" />
                    </SelectTrigger>
                    <SelectContent>
                      {dbConnections.map((conn) => (
                        <SelectItem key={conn.id} value={conn.id.toString()}>
                          {conn.connection_name} ({conn.db_type})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
              {selectedConnection && tables.length > 0 && (
                <div className="mt-4">
                  <DatabaseTableSync
                    connectionId={selectedConnection}
                    tables={tables}
                    onSync={loadDatabaseConnections}
                  />
                </div>
              )}
              {selectedConnection && tables.length === 0 && (
                <p className="text-sm text-muted-foreground">No tables found in this database.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* UI Customization */}
        <TabsContent value="ui" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Branding</CardTitle>
              <CardDescription>Customize the appearance of your chatbot</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="brandName">Brand Name</Label>
                <Input
                  id="brandName"
                  value={config.ui_config?.brand_name || ''}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ui_config: { ...config.ui_config, brand_name: e.target.value },
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="logoUrl">Logo URL</Label>
                <Input
                  id="logoUrl"
                  value={config.ui_config?.logo_url || ''}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ui_config: { ...config.ui_config, logo_url: e.target.value },
                    })
                  }
                  placeholder="https://example.com/logo.png"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="primaryColor">Primary Color</Label>
                <Input
                  id="primaryColor"
                  type="color"
                  value={config.ui_config?.primary_color || '#3b82f6'}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      ui_config: { ...config.ui_config, primary_color: e.target.value },
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tone">Tone</Label>
                <Select
                  value={config.tone}
                  onValueChange={(value) => setConfig({ ...config, tone: value })}
                >
                  <SelectTrigger id="tone">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="casual">Casual</SelectItem>
                    <SelectItem value="friendly">Friendly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Advanced Settings */}
        <TabsContent value="advanced" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>Fine-tune system behavior</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="embeddingModel">Embedding Model</Label>
                <Select
                  value={config.embedding_model}
                  onValueChange={(value) => setConfig({ ...config, embedding_model: value })}
                >
                  <SelectTrigger id="embeddingModel">
                    <SelectValue placeholder="Select an embedding model" />
                  </SelectTrigger>
                  <SelectContent>
                    {embeddingModels.map((model) => (
                      <SelectItem key={model.name} value={model.name}>
                        {model.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {config.embedding_model && embeddingModels.find(m => m.name === config.embedding_model) && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {embeddingModels.find(m => m.name === config.embedding_model)?.description}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Uses sentence-transformers library. Models download automatically on first use.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="autoSendThreshold">Auto-Send Threshold</Label>
                <Input
                  id="autoSendThreshold"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={config.auto_send_threshold}
                  onChange={(e) =>
                    setConfig({ ...config, auto_send_threshold: parseFloat(e.target.value) })
                  }
                />
                <p className="text-sm text-muted-foreground">
                  Confidence score threshold for auto-sending responses (0-1)
                </p>
              </div>

              <Button onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? 'Saving...' : 'Save'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Database Connection Form Component
function DatabaseConnectionForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    connection_name: '',
    db_type: 'postgresql',
    host: '',
    port: 5432,
    database: 'postgres',
    username: 'postgres',
    password: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleDbTypeChange = (value: string) => {
    setFormData({
      ...formData,
      db_type: value,
      // Auto-fill defaults for Supabase
      ...(value === 'supabase' && {
        port: 5432,
        database: 'postgres',
        username: 'postgres',
      }),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createDatabaseConnection(formData);
      setFormData({
        connection_name: '',
        db_type: 'postgresql',
        host: '',
        port: 5432,
        database: 'postgres',
        username: 'postgres',
        password: '',
      });
      onSuccess();
    } catch (error) {
      console.error('Failed to create connection:', error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="connection-name">Connection Name</Label>
          <Input
            id="connection-name"
            value={formData.connection_name}
            onChange={(e) => setFormData({ ...formData, connection_name: e.target.value })}
            placeholder="e.g., Production DB"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="db-type">Database Type</Label>
          <Select
            value={formData.db_type}
            onValueChange={handleDbTypeChange}
          >
            <SelectTrigger id="db-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="postgresql">PostgreSQL</SelectItem>
              <SelectItem value="supabase">Supabase</SelectItem>
              <SelectItem value="mysql">MySQL</SelectItem>
              <SelectItem value="sqlite">SQLite</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="host">
            Host {formData.db_type === 'supabase' && <span className="text-muted-foreground font-normal">(Project URL)</span>}
          </Label>
          <Input
            id="host"
            value={formData.host}
            onChange={(e) => setFormData({ ...formData, host: e.target.value })}
            placeholder={formData.db_type === 'supabase' ? 'db.xxxxx.supabase.co' : 'localhost'}
            required
          />
          {formData.db_type === 'supabase' && (
            <p className="text-xs text-muted-foreground mt-1">
              Find this in your Supabase project settings under Database → Connection string
            </p>
          )}
        </div>
        <div className="space-y-2">
          <Label htmlFor="port">Port</Label>
          <Input
            id="port"
            type="number"
            value={formData.port}
            onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) || 5432 })}
            required
            disabled={formData.db_type === 'supabase'}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="database">Database</Label>
          <Input
            id="database"
            value={formData.database}
            onChange={(e) => setFormData({ ...formData, database: e.target.value })}
            required
            disabled={formData.db_type === 'supabase'}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            required
            disabled={formData.db_type === 'supabase'}
          />
        </div>
        <div className="space-y-2 col-span-2">
          <Label htmlFor="password">
            Password {formData.db_type === 'supabase' && <span className="text-muted-foreground font-normal">(Database Password)</span>}
          </Label>
          <Input
            id="password"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            placeholder={formData.db_type === 'supabase' ? 'Your Supabase database password' : ''}
            required
          />
          {formData.db_type === 'supabase' && (
            <p className="text-xs text-muted-foreground mt-1">
              This is your database password, not your Supabase account password. Find it in Database → Connection string.
            </p>
          )}
        </div>
      </div>
      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? 'Connecting...' : 'Create Connection'}
        </Button>
      </div>
    </form>
  );
}

// Database Table Sync Component
function DatabaseTableSync({
  connectionId,
  tables,
  onSync,
}: {
  connectionId: number;
  tables: TableInfo[];
  onSync: () => void;
}) {
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    if (!selectedTable || selectedColumns.length === 0) return;
    
    setSyncing(true);
    try {
      const result = await syncDatabaseTable({
        connection_id: connectionId,
        table_name: selectedTable,
        columns: selectedColumns,
      });
      alert(`Synced ${result.articles_created} articles from ${selectedTable}`);
      onSync();
    } catch (error) {
      console.error('Failed to sync table:', error);
    } finally {
      setSyncing(false);
    }
  };

  const table = tables.find((t) => t.name === selectedTable);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Select Table</Label>
        <Select value={selectedTable} onValueChange={setSelectedTable}>
          <SelectTrigger>
            <SelectValue placeholder="Select a table" />
          </SelectTrigger>
          <SelectContent>
            {tables.map((t) => (
              <SelectItem key={t.name} value={t.name}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {table && (
        <div className="space-y-2">
          <Label>Select Columns</Label>
          <div className="grid grid-cols-3 gap-2">
            {table.columns.map((col) => (
              <label key={col} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={selectedColumns.includes(col)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedColumns([...selectedColumns, col]);
                    } else {
                      setSelectedColumns(selectedColumns.filter((c) => c !== col));
                    }
                  }}
                />
                <span className="text-sm">{col}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <Button onClick={handleSync} disabled={syncing || !selectedTable || selectedColumns.length === 0}>
        {syncing ? 'Syncing...' : 'Sync Table'}
      </Button>
    </div>
  );
}


