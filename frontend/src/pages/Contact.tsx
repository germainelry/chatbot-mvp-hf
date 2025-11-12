import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Mail, CheckCircle, AlertCircle } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';

export default function Contact() {
  const [formData, setFormData] = useState({
    companyName: '',
    email: '',
    useCase: '',
    requirements: ''
  });
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAlert(null);

    try {
      // In a real implementation, you would send this to your backend
      // For now, we'll just show a success message
      // You can integrate with a service like Formspree, EmailJS, or your own backend endpoint
      
      // Example: Send to backend endpoint
      // await fetch('/api/contact', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(formData)
      // });

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      setAlert({
        type: 'success',
        message: 'Thank you for your interest! We will contact you soon.'
      });
      
      // Reset form
      setFormData({
        companyName: '',
        email: '',
        useCase: '',
        requirements: ''
      });
    } catch (error) {
      setAlert({
        type: 'error',
        message: 'Failed to submit form. Please try again or contact us directly.'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <PageHeader
        title="Request Integration"
        description="Interested in integrating our AI chatbot into your business? Fill out the form below and we'll get in touch."
      />

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Contact Form
          </CardTitle>
          <CardDescription>
            Tell us about your use case and requirements. We'll respond within 24 hours.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {alert && (
            <Alert className={`mb-4 ${alert.type === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              {alert.type === 'success' ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-600" />
              )}
              <AlertDescription className={alert.type === 'success' ? 'text-green-800' : 'text-red-800'}>
                {alert.message}
              </AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="companyName">Company Name *</Label>
              <Input
                id="companyName"
                required
                value={formData.companyName}
                onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                placeholder="Your company name"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="your.email@company.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="useCase">Use Case *</Label>
              <Textarea
                id="useCase"
                required
                rows={3}
                value={formData.useCase}
                onChange={(e) => setFormData({ ...formData, useCase: e.target.value })}
                placeholder="Describe how you plan to use the chatbot (e.g., customer support, internal knowledge base, etc.)"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="requirements">Integration Requirements</Label>
              <Textarea
                id="requirements"
                rows={4}
                value={formData.requirements}
                onChange={(e) => setFormData({ ...formData, requirements: e.target.value })}
                placeholder="Any specific requirements, integrations, or features you need (optional)"
              />
            </div>

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? 'Submitting...' : 'Submit Request'}
            </Button>
          </form>

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              <strong>Note:</strong> This is a demo contact form. In production, you would integrate this with:
            </p>
            <ul className="mt-2 text-sm text-gray-600 list-disc list-inside space-y-1">
              <li>Your backend API endpoint</li>
              <li>Email service (SendGrid, Mailgun, etc.)</li>
              <li>CRM integration (HubSpot, Salesforce, etc.)</li>
              <li>Form service (Formspree, Typeform, etc.)</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

