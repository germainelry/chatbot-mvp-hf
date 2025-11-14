/**
 * Admin Login Component
 * Simple modal for admin authentication
 */
import { useState } from 'react';
import { Shield, LogOut } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';

interface AdminLoginProps {
  onLoginSuccess?: (username: string) => void;
  onLogout?: () => void;
}

export function AdminLogin({ onLoginSuccess, onLogout }: AdminLoginProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isOpen, setIsOpen] = useState(false);

  // Check if admin is already logged in
  const isLoggedIn = !!localStorage.getItem('admin_token');
  const adminUsername = localStorage.getItem('admin_username');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

      const response = await fetch(`${API_BASE_URL}/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Login failed');
      }

      const data = await response.json();

      // Store token and username
      localStorage.setItem('admin_token', data.access_token);
      localStorage.setItem('admin_username', data.username);
      localStorage.setItem('admin_token_expiry', String(Date.now() + data.expires_in * 1000));

      // Clear form
      setUsername('');
      setPassword('');
      setIsOpen(false);

      // Notify parent component
      if (onLoginSuccess) {
        onLoginSuccess(data.username);
      }

      // Show success message
      console.log(`[Admin] Logged in as ${data.username}`);
    } catch (err: any) {
      setError(err.message || 'Failed to login');
      console.error('[Admin Login Error]', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    // Clear admin session
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('admin_token_expiry');

    // Notify parent component
    if (onLogout) {
      onLogout();
    }

    console.log('[Admin] Logged out');
  };

  // If logged in, show logout button
  if (isLoggedIn) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground flex items-center gap-1">
          <Shield className="h-4 w-4 text-green-600" />
          Admin: {adminUsername}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          className="gap-1"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </Button>
      </div>
    );
  }

  // If not logged in, show login button
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1">
          <Shield className="h-4 w-4" />
          Admin Login
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Admin Login</DialogTitle>
          <DialogDescription>
            Enter your admin credentials to access delete and management features.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              required
              autoComplete="username"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Hook to check if user has a valid admin token
 */
export function useIsAdmin(): boolean {
  const token = localStorage.getItem('admin_token');
  const expiry = localStorage.getItem('admin_token_expiry');

  if (!token || !expiry) {
    return false;
  }

  // Check if token has expired
  if (Date.now() > parseInt(expiry)) {
    // Token expired, clear it
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('admin_token_expiry');
    return false;
  }

  return true;
}

/**
 * Get admin token for API calls
 */
export function getAdminToken(): string | null {
  const token = localStorage.getItem('admin_token');
  const expiry = localStorage.getItem('admin_token_expiry');

  if (!token || !expiry) {
    return null;
  }

  // Check if token has expired
  if (Date.now() > parseInt(expiry)) {
    // Token expired, clear it
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_username');
    localStorage.removeItem('admin_token_expiry');
    return null;
  }

  return token;
}
