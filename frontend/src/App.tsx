import { BrowserRouter as Router, Routes, Route, useLocation, Link } from 'react-router-dom';
import { MessageSquare, BarChart3, Users, BookOpen } from 'lucide-react';
import { Button } from './components/ui/button';
import { Separator } from './components/ui/separator';
import CustomerChat from './pages/CustomerChat';
import AgentDashboard from './pages/AgentDashboard';
import Analytics from './pages/Analytics';
import KnowledgeBase from './pages/KnowledgeBase';
import { cn } from './components/ui/utils';

function Navigation() {
  const location = useLocation();
  
  const navItems = [
    { path: '/customer', label: 'Customer Chat', icon: MessageSquare },
    { path: '/agent', label: 'Agent Dashboard', icon: Users },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/knowledge-base', label: 'Knowledge Base', icon: BookOpen },
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
                  isActive && "bg-primary text-primary-foreground"
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
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Navigation />
        <main className="container py-6">
          <Routes>
            <Route path="/" element={<CustomerChat />} />
            <Route path="/customer" element={<CustomerChat />} />
            <Route path="/agent" element={<AgentDashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/knowledge-base" element={<KnowledgeBase />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

