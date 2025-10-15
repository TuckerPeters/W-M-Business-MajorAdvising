'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import { ChatMessage } from '@/types';
import { Send, ExternalLink, AlertCircle, Lightbulb } from 'lucide-react';

interface ChatInterfaceProps {
  initialMessages?: ChatMessage[];
}

export default function ChatInterface({ initialMessages = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Simulate AI response (in production, this would call your backend)
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Based on your current progress (42 credits with a 3.65 GPA), you're in an excellent position to declare your Business Analytics major. You've completed the prerequisite courses and are within the declaration window (39-54 credits).`,
        citations: [
          {
            title: 'W&M Business School - Major Declaration Requirements',
            url: 'https://mason.wm.edu/undergraduate/requirements',
            version: '2024-08-01',
          },
        ],
        nextSteps: [
          'Complete BUAD 204 (Managerial Accounting) this semester',
          'Schedule a declaration meeting with your advisor',
          'Review the Business Analytics concentration requirements',
        ],
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 1500);
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Ask Your Advisor</CardTitle>
        <CardDescription>
          Get instant answers about requirements, courses, and planning
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col min-h-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border space-y-2">
                    <p className="text-xs font-semibold flex items-center gap-1">
                      <ExternalLink className="h-3 w-3" />
                      Sources:
                    </p>
                    {message.citations.map((citation, idx) => (
                      <a
                        key={idx}
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-xs hover:underline text-blue-600 dark:text-blue-400"
                      >
                        {citation.title} (v{citation.version})
                      </a>
                    ))}
                  </div>
                )}

                {/* Risks */}
                {message.risks && message.risks.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs font-semibold flex items-center gap-1 mb-2">
                      <AlertCircle className="h-3 w-3" />
                      Potential Risks:
                    </p>
                    <ul className="space-y-1">
                      {message.risks.map((risk, idx) => (
                        <li key={idx} className="text-xs">
                          • {risk}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Next Steps */}
                {message.nextSteps && message.nextSteps.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs font-semibold flex items-center gap-1 mb-2">
                      <Lightbulb className="h-3 w-3" />
                      Next Steps:
                    </p>
                    <ul className="space-y-1">
                      {message.nextSteps.map((step, idx) => (
                        <li key={idx} className="text-xs">
                          {idx + 1}. {step}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <p className="text-xs opacity-70 mt-2">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg p-4">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about requirements, courses, or planning..."
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()} size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Quick Prompts */}
        <div className="flex flex-wrap gap-2 mt-3">
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-accent"
            onClick={() => setInput('When should I declare my major?')}
          >
            When to declare?
          </Badge>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-accent"
            onClick={() => setInput('What courses should I take next semester?')}
          >
            Next semester courses?
          </Badge>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-accent"
            onClick={() => setInput('Do my AP credits count?')}
          >
            AP credits?
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
