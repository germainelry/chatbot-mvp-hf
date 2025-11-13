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
  TenantConfiguration as TenantConfigType,
  detectEnvironment,
  getLLMProviderInfo,
  EnvironmentInfo,
} from '../services/api';
import { LLMProviderGuide } from '../components/LLMProviderGuide';
import { Badge } from '../components/ui/badge';
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

export default function Configuration() {
  const [activeTab, setActiveTab] = useState('llm');
  const [config, setConfig] = useState<TenantConfigType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModel[]>([]);
  const [testingLLM, setTestingLLM] = useState(false);
  const [environment, setEnvironment] = useState<EnvironmentInfo | null>(null);
  const [providerMetadata, setProviderMetadata] = useState<any>(null);
  const [apiKeyError, setApiKeyError] = useState<string>('');
  
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
  
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string; details?: string } | null>(null);
  
  // File input refs
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const documentInputRef = useRef<HTMLInputElement>(null);

  // Track loading state to prevent duplicate requests
  const loadingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    // OPTIMIZED: Load only configuration on mount
    const loadInitialData = async () => {
      if (loadingRef.current) return;
      loadingRef.current = true;

      try {
        setLoading(true);
        const configData = await getTenantConfiguration();
        setConfig(configData);
        applyTheme(configData);
        setAlert(null);
      } catch (error: any) {
        console.error('Failed to load configuration:', error);
        let errorMessage = 'Failed to load configuration';
        if (error.response?.status === 401) {
          errorMessage = 'Authentication failed. Check if VITE_API_KEY is set in .env.local and restart the dev server.';
        } else if (error.response?.status === 404) {
          errorMessage = 'Configuration not found. Please create a configuration for this tenant.';
        } else if (error.message === 'Network Error' || error.code === 'ECONNREFUSED') {
          errorMessage = 'Cannot connect to backend. Ensure backend server is running on http://localhost:8000';
        }
        setAlert({ type: 'error', message: errorMessage });
      } finally {
        setLoading(false);
        loadingRef.current = false;
      }
    };

    loadInitialData();
  }, []); // Load once on mount

  // OPTIMIZED: Lazy load data when tabs are activated
  useEffect(() => {
    const loadTabData = async () => {
      if (activeTab === 'llm' && config?.llm_provider) {
        // Load LLM tab data
        if (providers.length === 0) {
          const providersData = await listLLMProviders().catch(() => ({ providers: [] }));
          setProviders(providersData.providers);
        }
        if (models.length === 0 || !providerMetadata) {
          await Promise.all([
            listLLMModels(config.llm_provider).then(data => setModels(data.models)).catch(() => {}),
            getLLMProviderInfo(config.llm_provider).then(data => setProviderMetadata(data)).catch(() => {}),
            detectEnvironment().then(data => setEnvironment(data)).catch(() => {}),
          ]);
        }
      } else if (activeTab === 'advanced') {
        // Load advanced tab data
        if (embeddingModels.length === 0) {
          const embeddingData = await listEmbeddingModels().catch(() => ({ models: [] }));
          setEmbeddingModels(embeddingData.models);
        }
      }
    };

    loadTabData();
  }, [activeTab, config?.llm_provider]);


  // Helper function to load models for a provider
  const loadModels = async (provider: string) => {
    try {
      const data = await listLLMModels(provider);
      setModels(data.models);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  // Helper function to load provider info
  const loadProviderInfo = async (provider: string) => {
    try {
      const data = await getLLMProviderInfo(provider);
      setProviderMetadata(data);
    } catch (error) {
      console.error('Failed to load provider info:', error);
    }
  };


  const handleSave = async () => {
    if (!config) return;

    setSaving(true);
    try {
      const updated = await updateTenantConfiguration(1, config); // Use 1 for backward compatibility
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

  const validateAPIKey = (provider: string, apiKey: string): string => {
    if (!apiKey) return '';
    
    if (provider === 'openai') {
      const regex = /^sk-[a-zA-Z0-9]{48}$/;
      if (!regex.test(apiKey)) {
        return 'Invalid OpenAI API key format. Should start with sk- and be 51 characters long.';
      }
    } else if (provider === 'anthropic') {
      const regex = /^sk-ant-[a-zA-Z0-9\-_]{95,}$/;
      if (!regex.test(apiKey)) {
        return 'Invalid Anthropic API key format. Should start with sk-ant- and be at least 100 characters long.';
      }
    }
    
    return '';
  };

  const handleTestLLM = async () => {
    if (!config) return;
    
    // Validate API key format if provided
    if (config.llm_config?.api_key) {
      const error = validateAPIKey(config.llm_provider, config.llm_config.api_key);
      if (error) {
        setApiKeyError(error);
        setAlert({ type: 'error', message: error });
        return;
      }
      setApiKeyError('');
    }
    
    // Validate API key is provided for all providers
    if (!config.llm_config?.api_key) {
      setAlert({ type: 'error', message: 'API key is required for all providers' });
      return;
    }
    
    setTestingLLM(true);
    setAlert({ type: 'success', message: `Testing connection to ${config.llm_model_name}...` });
    
    try {
      const result = await testLLMConnection({
        provider: config.llm_provider,
        model: config.llm_model_name,
        config: config.llm_config,
      });
      
      setAlert({ 
        type: result.success ? 'success' : 'error', 
        message: result.message,
        details: result.test_response 
      });
      
      // Auto-dismiss success messages after 8 seconds, but keep errors
      if (result.success) {
        setTimeout(() => setAlert(null), 8000);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to test LLM connection';
      const errorDetails = error.response?.data?.error || error.message || '';
      setAlert({ 
        type: 'error', 
        message: `Connection test failed for ${config.llm_model_name}`,
        details: errorMessage
      });
      // Errors stay visible until manually dismissed
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



  if (loading || !config) {
    return <div>Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Configuration"
        description="Manage LLM, Knowledge Base, UI, and advanced settings"
      />


      {alert && (
        <Alert variant={alert.type === 'error' ? 'destructive' : 'default'} className="relative">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <AlertTitle className="flex items-center gap-2">
                {alert.type === 'error' ? 'Error' : 'Success'}
              </AlertTitle>
              <AlertDescription className="mt-2">
                {alert.message}
                {alert.details && (
                  <div className="mt-2 p-2 bg-muted/50 rounded text-xs font-mono whitespace-pre-wrap max-h-32 overflow-auto">
                    {alert.details}
                  </div>
                )}
              </AlertDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setAlert(null)}
            >
              ×
            </Button>
          </div>
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
                    loadProviderInfo(value);
                    setApiKeyError('');
                  }}
                >
                  <SelectTrigger id="provider">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map((provider) => (
                      <SelectItem key={provider} value={provider}>
                        <span className="capitalize">{provider}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Provider Guide */}
              {config.llm_provider && (
                <LLMProviderGuide provider={config.llm_provider} />
              )}

              {/* Model Selection */}
              <div className="space-y-2">
                <Label htmlFor="model">Select Model</Label>
                <Select
                  value={config.llm_model_name}
                  onValueChange={(value) => setConfig({ ...config, llm_model_name: value })}
                >
                  <SelectTrigger id="model">
                    <SelectValue placeholder="Select a model" />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {models.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Loading available models...
                  </p>
                )}
              </div>

              {/* API Key input - required for all providers */}
              <div className="space-y-2">
                <Label htmlFor="apiKey">
                  API Key <span className="text-red-500">(Required)</span>
                </Label>
                  <Input
                    id="apiKey"
                    type="password"
                    value={config.llm_config?.api_key || ''}
                    onChange={(e) => {
                      const newApiKey = e.target.value;
                      setConfig({
                        ...config,
                        llm_config: { ...config.llm_config, api_key: newApiKey },
                      });
                      // Validate on change
                      if (newApiKey) {
                        const error = validateAPIKey(config.llm_provider, newApiKey);
                        setApiKeyError(error);
                      } else {
                        setApiKeyError('');
                      }
                    }}
                    placeholder={`Enter your ${config.llm_provider} API key`}
                    className={apiKeyError ? 'border-red-500' : ''}
                  />
                  {apiKeyError && (
                    <p className="text-sm text-red-500">{apiKeyError}</p>
                  )}
                <p className="text-sm text-muted-foreground">
                  Your API key is stored securely and only used for LLM requests.
                </p>
              </div>

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
                    </div>
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
                    </div>
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
                    </div>
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

              {/* OPTIMIZED: Simplified guidelines */}
              <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-dashed">
                <p className="text-sm font-medium mb-2">Quick Guide:</p>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li><strong>PDF:</strong> Manuals, guides, reports (text-based, not scanned)</li>
                  <li><strong>CSV:</strong> FAQs, product catalogs (must include headers)</li>
                  <li><strong>Documents:</strong> .txt, .md, .docx files</li>
                  <li>Max 10MB per file • Auto-processed into searchable articles</li>
                </ul>
              </div>
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

