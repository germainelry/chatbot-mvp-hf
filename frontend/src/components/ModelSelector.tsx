/**
 * Model Selector Component
 * Displays available models (free and paid) with selection cards
 */
import { useState, useEffect } from 'react';
import { CheckCircle2, Sparkles, DollarSign } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Button } from './ui/button';

export interface Model {
  id: string;
  name: string;
  description: string;
  size?: string;
  recommended_for?: string;
  default?: boolean;
  cost?: string;
}

interface ModelSelectorProps {
  provider: string;
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  allowCustom?: boolean;
  freeModels?: Model[];
  paidModels?: Model[];
}

export function ModelSelector({
  selectedModel,
  onModelChange,
  allowCustom = false,
  freeModels = [],
  paidModels = [],
}: ModelSelectorProps) {
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customModel, setCustomModel] = useState('');

  // Check if selected model is custom (not in free or paid lists)
  useEffect(() => {
    const isInList = 
      freeModels.some(m => m.id === selectedModel) ||
      paidModels.some(m => m.id === selectedModel);
    
    if (!isInList && selectedModel && allowCustom) {
      setShowCustomInput(true);
      setCustomModel(selectedModel);
    }
  }, [selectedModel, freeModels, paidModels, allowCustom]);

  const handleCustomModelChange = (value: string) => {
    setCustomModel(value);
    if (value) {
      onModelChange(value);
    }
  };

  return (
    <div className="space-y-6">
      {/* Free Models Section */}
      {freeModels && freeModels.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-yellow-500" />
            <h4 className="text-sm font-semibold">Free Models</h4>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {freeModels.map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                selected={selectedModel === model.id}
                onSelect={() => onModelChange(model.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Paid Models Section */}
      {paidModels && paidModels.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-green-500" />
            <h4 className="text-sm font-semibold">Paid Models</h4>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {paidModels.map((model) => (
              <ModelCard
                key={model.id}
                model={model}
                selected={selectedModel === model.id}
                onSelect={() => onModelChange(model.id)}
                showCost
              />
            ))}
          </div>
        </div>
      )}

      {/* Custom Model Input */}
      {allowCustom && (
        <div className="space-y-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setShowCustomInput(!showCustomInput)}
            className="w-full"
          >
            {showCustomInput ? '−' : '+'} Use Custom Model
          </Button>
          {showCustomInput && (
            <div className="space-y-2">
              <Input
                placeholder="Enter model ID (e.g., meta-llama/Llama-2-7b-chat-hf)"
                value={customModel}
                onChange={(e) => handleCustomModelChange(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Enter any valid model identifier for this provider
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface ModelCardProps {
  model: Model;
  selected: boolean;
  onSelect: () => void;
  showCost?: boolean;
}

function ModelCard({ model, selected, onSelect, showCost }: ModelCardProps) {
  return (
    <Card
      className={`cursor-pointer transition-all hover:border-primary ${
        selected ? 'border-primary bg-primary/5' : ''
      }`}
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h5 className="font-semibold text-sm">{model.name}</h5>
              {model.default && (
                <Badge variant="secondary" className="text-xs">
                  Default
                </Badge>
              )}
              {showCost && model.cost && (
                <Badge variant="outline" className="text-xs">
                  {model.cost}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mb-2">
              {model.description}
            </p>
          </div>
          {selected && (
            <CheckCircle2 className="h-5 w-5 text-primary flex-shrink-0" />
          )}
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {model.size && (
            <span className="text-muted-foreground">Size: {model.size}</span>
          )}
          {model.recommended_for && (
            <span className="text-muted-foreground">
              💡 {model.recommended_for}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

