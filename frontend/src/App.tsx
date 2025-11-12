import { BrowserRouter as Router, Routes, Route, useLocation, Link } from 'react-router-dom';
import { MessageSquare, BarChart3, Users, BookOpen, Settings, Building2 } from 'lucide-react';
import { Button } from './components/ui/button';
import { Separator } from './components/ui/separator';
import CustomerChat from './pages/CustomerChat';
import AgentDashboard from './pages/AgentDashboard';
import Analytics from './pages/Analytics';
import KnowledgeBase from './pages/KnowledgeBase';
import Configuration from './pages/Configuration';
import TenantManagement from './pages/TenantManagement';
import Contact from './pages/Contact';
import DemoBanner from './components/DemoBanner';
import { cn } from './components/ui/utils';
import { useEffect } from 'react';
import { getTheme, applyTheme } from './config/theme';
import { Toaster } from 'sonner';

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/customer', label: 'Customer Chat', icon: MessageSquare },
    { path: '/agent', label: 'Agent Dashboard', icon: Users },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
    { path: '/configuration', label: 'Configuration', icon: Settings },
    { path: '/tenants', label: 'Tenants', icon: Building2 },
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
    // Set default tenant ID if not set
    if (!localStorage.getItem('tenant_id')) {
      localStorage.setItem('tenant_id', '1');
    }
    
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
          <Routes>
            <Route path="/" element={<CustomerChat />} />
            <Route path="/customer" element={<CustomerChat />} />
            <Route path="/agent" element={<AgentDashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/knowledge-base" element={<KnowledgeBase />} />
            <Route path="/configuration" element={<Configuration />} />
            <Route path="/tenants" element={<TenantManagement />} />
            <Route path="/contact" element={<Contact />} />
          </Routes>
        </main>
        <Toaster position="top-right" richColors />
      </div>
    </Router>
  );
}

export default App;

