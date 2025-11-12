import { Alert, AlertDescription } from './ui/alert';
import { Info, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';

export default function DemoBanner() {
  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

  if (!isDemoMode) {
    return null;
  }

  return (
    <Alert className="mb-4 border-blue-200 bg-blue-50">
      <Info className="h-4 w-4 text-blue-600" />
      <AlertDescription className="flex items-center justify-between">
        <div className="flex-1">
          <strong className="text-blue-900">Demo Mode:</strong>
          <span className="ml-2 text-blue-800">
            This is a demonstration version with limited features. 
            Rate limits: 100 requests/hour, 10 conversations/day, 20 messages per conversation.
          </span>
        </div>
        <Link to="/contact" className="ml-4">
          <Button variant="outline" size="sm" className="border-blue-300 text-blue-700 hover:bg-blue-100">
            Request Integration
            <ExternalLink className="ml-2 h-3 w-3" />
          </Button>
        </Link>
      </AlertDescription>
    </Alert>
  );
}

