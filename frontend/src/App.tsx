import { BrowserRouter as Router, Routes, Route, useLocation, Link } from 'react-router-dom';
import { MessageSquare, BarChart3, Users, BookOpen, Settings } from 'lucide-react';
import { Button } from './components/ui/button';
import { Separator } from './components/ui/separator';
import { lazy, Suspense, useEffect } from 'react';
import DemoBanner from './components/DemoBanner';
import { cn } from './components/ui/utils';
import { getTheme, applyTheme } from './config/theme';
import { Toaster } from 'sonner';
import { Loader2 } from 'lucide-react';

// Lazy load pages for better performance and code splitting
const CustomerChat = lazy(() => import('./pages/CustomerChat'));
const AgentDashboard = lazy(() => import('./pages/AgentDashboard'));
const Analytics = lazy(() => import('./pages/Analytics'));
const KnowledgeBase = lazy(() => import('./pages/KnowledgeBase'));
const Configuration = lazy(() => import('./pages/Configuration'));
const Contact = lazy(() => import('./pages/Contact'));

// Loading component
const PageLoader = () => (
  <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
    <div className="text-center space-y-4">
      <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
      <p className="text-muted-foreground">Loading...</p>
    </div>
  </div>
);

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/customer', label: 'Customer Chat', icon: MessageSquare },
    { path: '/agent', label: 'Agent Dashboard', icon: Users },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
    { path: '/configuration', label: 'Configuration', icon: Settings },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center px-4">
        <div className="mr-4 flex items-center space-x-2">
          <MessageSquare className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">AI Chatbot Assistant</span>
        </div>
        <Separator orientation="vertical" className="h-6 mx-4" />
        <div className="flex flex-1 items-center space-x-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || 
              (item.path === '/customer' && location.pathname === '/');
            return (
              <Button
                key={item.path}
                asChild
                variant={isActive ? "default" : "ghost"}
                size="sm"
                className={cn(
                  "transition-colors",
                  isActive && "bg-primary text-primary-foreground hover:bg-primary/90"
                )}
              >
                <Link to={item.path} className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline-block">{item.label}</span>
                </Link>
              </Button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function App() {
  useEffect(() => {
    // Load and apply theme on app start
    const theme = getTheme();
    if (theme) {
      // Apply theme with empty config to use stored theme
      applyTheme({ ui_config: { primary_color: theme.primaryColor, brand_name: theme.brandName } });
    }
  }, []);

  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Navigation />
        <main className="container py-6">
          <DemoBanner />
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/" element={<CustomerChat />} />
              <Route path="/customer" element={<CustomerChat />} />
              <Route path="/agent" element={<AgentDashboard />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
              <Route path="/configuration" element={<Configuration />} />
              <Route path="/contact" element={<Contact />} />
            </Routes>
          </Suspense>
        </main>
        <Toaster position="top-right" richColors />
      </div>
    </Router>
  );
}

export default App;

