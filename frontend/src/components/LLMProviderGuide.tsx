/**
 * LLM Provider Guide Component
 * Displays provider information and setup instructions
 */
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

export interface ProviderMetadata {
  display_name: string;
  description: string;
  cost: string;
  environments: string[];
  requires_api_key: boolean;
  setup_complexity: string;
  setup_steps: string[];
  signup_url?: string;
  paid_models?: string[];
}

interface LLMProviderGuideProps {
  provider: string;
}

export function LLMProviderGuide({ provider }: LLMProviderGuideProps) {
  const [metadata, setMetadata] = useState<ProviderMetadata | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!provider) {
      setMetadata(null);
      setLoading(false);
      return;
    }

    const fetchProviderInfo = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/config/llm-provider-info/${provider}`);
        if (response.ok) {
          const data = await response.json();
          setMetadata(data);
        } else {
          setMetadata(null);
        }
      } catch (error) {
        console.error('Failed to fetch provider info:', error);
        setMetadata(null);
      } finally {
        setLoading(false);
      }
    };

    fetchProviderInfo();
  }, [provider]);

  if (loading || !metadata) {
    return null;
  }

  const isFree = metadata.cost.toLowerCase().includes('free');

  return (
    <Card className="mt-4">
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Cost Badge */}
          <div className="flex flex-wrap gap-2">
            <Badge variant={isFree ? 'default' : 'outline'}>
              {metadata.cost}
            </Badge>
          </div>

          {/* Description */}
          <p className="text-sm text-muted-foreground">{metadata.description}</p>

          {/* Setup Instructions */}
          <div className="space-y-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              className="p-0 h-auto font-semibold"
            >
              {expanded ? (
                <ChevronDown className="h-4 w-4 mr-1" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-1" />
              )}
              Setup Guide
            </Button>
            {expanded && (
              <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground ml-5">
                {metadata.setup_steps.map((step, i) => (
                  <li key={i} className="leading-relaxed">
                    {step}
                  </li>
                ))}
              </ol>
            )}
            
          </div>

        </div>
      </CardContent>
    </Card>
  );
}

