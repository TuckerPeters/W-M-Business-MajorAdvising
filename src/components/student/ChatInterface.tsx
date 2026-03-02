'use client';

import { useState, useEffect, useRef } from 'react';
import { ChatMessage } from '@/types';
import {
  sendChatMessage,
  getConversations,
  getConversationMessages,
  ConversationSummary,
} from '@/lib/api-client';
import {
  Send,
  ExternalLink,
  AlertCircle,
  Lightbulb,
  Plus,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Trash2,
} from 'lucide-react';

type SendMessageFn = (message: string, conversationId?: string | null) => Promise<{
  content: string;
  citations: any[];
  risks: any[];
  nextSteps: any[];
  conversationId: string;
}>;

type ListConversationsFn = () => Promise<ConversationSummary[]>;
type DeleteConversationFn = (conversationId: string) => Promise<any>;

interface QuickPrompt {
  label: string;
  prompt: string;
}

interface ChatInterfaceProps {
  activeConversationId?: string | null;
  onConversationChange?: (id: string | null) => void;
  sendMessageFn?: SendMessageFn;
  listConversationsFn?: ListConversationsFn;
  deleteConversationFn?: DeleteConversationFn;
  quickPrompts?: QuickPrompt[];
  title?: string;
  subtitle?: string;
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const defaultQuickPrompts: QuickPrompt[] = [
  { label: 'When to declare?', prompt: 'When should I declare my major?' },
  { label: 'Next semester courses?', prompt: 'What courses should I take next semester?' },
  { label: 'AP credits?', prompt: 'Do my AP credits count?' },
];

export default function ChatInterface({
  activeConversationId = null,
  onConversationChange,
  sendMessageFn = sendChatMessage,
  listConversationsFn = getConversations,
  deleteConversationFn,
  quickPrompts = defaultQuickPrompts,
  title = 'AI Academic Advisor',
  subtitle = 'AI-powered answers about requirements, courses, and planning',
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(activeConversationId);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [convoLoading, setConvoLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversation list on mount
  useEffect(() => {
    listConversationsFn()
      .then(setConversations)
      .catch((err) => console.error('Failed to load conversations:', err))
      .finally(() => setConvoLoading(false));
  }, [listConversationsFn]);

  // If we have an active conversation from parent, load its messages
  useEffect(() => {
    if (activeConversationId && conversations.length >= 0 && !convoLoading) {
      loadConversation(activeConversationId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConversationId, convoLoading]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const loadConversation = async (id: string) => {
    setLoadingHistory(true);
    try {
      const msgs = await getConversationMessages(id);
      setMessages(msgs);
      setConversationId(id);
      onConversationChange?.(id);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setConversationId(null);
    onConversationChange?.(null);
  };

  const refreshConversations = async () => {
    try {
      const list = await listConversationsFn();
      setConversations(list);
    } catch (err) {
      console.error('Failed to refresh conversations:', err);
    }
  };

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!deleteConversationFn) return;

    setDeletingId(id);
    try {
      await deleteConversationFn(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      // If we deleted the active conversation, clear the chat
      if (conversationId === id) {
        startNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageText = input;
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendMessageFn(messageText, conversationId);

      if (response.conversationId && !conversationId) {
        setConversationId(response.conversationId);
        onConversationChange?.(response.conversationId);
        // Refresh list so new conversation appears
        refreshConversations();
      } else if (response.conversationId) {
        // Refresh to update lastMessagePreview / title
        refreshConversations();
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        citations: response.citations?.map((c: any) => ({
          title: c.source || 'Source',
          url: '',
          version: c.relevance ? `relevance: ${c.relevance}` : '',
        })),
        risks: response.risks?.map((r: any) =>
          `[${r.severity?.toUpperCase()}] ${r.message}`
        ),
        nextSteps: response.nextSteps?.map((s: any) =>
          `${s.action}${s.deadline ? ` (by ${s.deadline})` : ''}`
        ),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I was unable to process your request. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex border border-[#e8e4db] rounded bg-white overflow-hidden">
      {/* Conversation Sidebar */}
      <div
        className={`flex-shrink-0 border-r border-[#e8e4db] bg-[#f7f5f0] flex flex-col transition-all duration-200 ${
          sidebarOpen ? 'w-[220px]' : 'w-0 overflow-hidden border-r-0'
        }`}
      >
        {/* Sidebar header */}
        <div className="px-3 py-3 border-b border-[#e8e4db]">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-[#115740] rounded hover:bg-[#0d4632] transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            New Chat
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto">
          {convoLoading ? (
            <div className="flex justify-center py-6">
              <div className="animate-spin h-5 w-5 border-2 border-[#115740] border-t-transparent rounded-full" />
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-6 px-3">
              No conversations yet
            </p>
          ) : (
            conversations.map((convo) => (
              <div
                key={convo.id}
                className={`group relative border-b border-[#e8e4db] transition-colors ${
                  conversationId === convo.id
                    ? 'bg-[#115740] text-white'
                    : 'hover:bg-[#eeebe4] text-[#262626]'
                }`}
              >
                <button
                  onClick={() => loadConversation(convo.id)}
                  className="w-full text-left px-3 py-3 pr-8"
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare
                      className={`h-3.5 w-3.5 mt-0.5 flex-shrink-0 ${
                        conversationId === convo.id ? 'text-white/70' : 'text-[#115740]'
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium truncate">
                        {convo.title}
                      </p>
                      {convo.lastMessagePreview && (
                        <p
                          className={`text-[11px] mt-0.5 truncate ${
                            conversationId === convo.id ? 'text-white/60' : 'text-gray-400'
                          }`}
                        >
                          {convo.lastMessagePreview}
                        </p>
                      )}
                      <p
                        className={`text-[10px] mt-1 ${
                          conversationId === convo.id ? 'text-white/50' : 'text-gray-400'
                        }`}
                      >
                        {timeAgo(convo.updatedAt)}
                      </p>
                    </div>
                  </div>
                </button>
                {deleteConversationFn && (
                  <button
                    onClick={(e) => handleDeleteConversation(convo.id, e)}
                    disabled={deletingId === convo.id}
                    className={`absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50 ${
                      conversationId === convo.id
                        ? 'hover:bg-white/20 text-white/70'
                        : 'hover:bg-red-50 text-gray-400 hover:text-red-500'
                    }`}
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-4 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 hover:bg-[#e8e4db] rounded transition-colors flex-shrink-0"
          >
            {sidebarOpen ? (
              <PanelLeftClose className="h-4 w-4 text-[#115740]" />
            ) : (
              <PanelLeftOpen className="h-4 w-4 text-[#115740]" />
            )}
          </button>
          <div>
            <h3
              className="text-[#115740] font-semibold text-base"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              {title}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {subtitle}
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 p-6 min-h-0">
          {loadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin h-8 w-8 border-3 border-[#115740] border-t-transparent rounded-full" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <img
                src="/buisness_emblem.png"
                alt="Mason School of Business"
                className="h-16 w-auto opacity-30 mb-4"
              />
              <p className="text-sm text-gray-400">
                Ask a question to get started
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-[#115740] text-white'
                      : 'bg-[#f7f5f0] border border-[#e8e4db] text-[#262626]'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                  {/* Citations */}
                  {message.citations && message.citations.length > 0 && (
                    <div className={`mt-3 pt-3 border-t ${message.role === 'user' ? 'border-white/20' : 'border-[#e8e4db]'} space-y-2`}>
                      <p className="text-xs font-semibold flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" />
                        Sources:
                      </p>
                      {message.citations.map((citation, idx) => (
                        <span
                          key={idx}
                          className={`block text-xs ${message.role === 'user' ? 'text-white/80' : 'text-[#115740]'}`}
                        >
                          {citation.title} ({citation.version})
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Risks */}
                  {message.risks && message.risks.length > 0 && (
                    <div className={`mt-3 pt-3 border-t ${message.role === 'user' ? 'border-white/20' : 'border-[#e8e4db]'}`}>
                      <p className="text-xs font-semibold flex items-center gap-1 mb-2">
                        <AlertCircle className="h-3 w-3 text-red-500" />
                        Potential Risks:
                      </p>
                      <ul className="space-y-1">
                        {message.risks.map((risk, idx) => (
                          <li key={idx} className="text-xs">
                            {risk}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Next Steps */}
                  {message.nextSteps && message.nextSteps.length > 0 && (
                    <div className={`mt-3 pt-3 border-t ${message.role === 'user' ? 'border-white/20' : 'border-[#e8e4db]'}`}>
                      <p className="text-xs font-semibold flex items-center gap-1 mb-2">
                        <Lightbulb className="h-3 w-3 text-[#B9975B]" />
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

                  <p className={`text-xs mt-2 ${message.role === 'user' ? 'text-white/50' : 'text-gray-400'}`}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg p-4">
                <div className="flex gap-2">
                  <div className="w-2 h-2 bg-[#115740]/40 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-[#115740]/40 rounded-full animate-bounce [animation-delay:100ms]" />
                  <div className="w-2 h-2 bg-[#115740]/40 rounded-full animate-bounce [animation-delay:200ms]" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-6 pb-5 pt-3 border-t border-[#e8e4db]">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about requirements, courses, or planning..."
              disabled={isLoading}
              className="flex-1 h-10 rounded border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="h-10 w-10 rounded bg-[#115740] text-white flex items-center justify-center hover:bg-[#0d4632] transition-colors disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>

          {/* Quick Prompts */}
          {messages.length === 0 && quickPrompts.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {quickPrompts.map((item) => (
                <button
                  key={item.label}
                  onClick={() => setInput(item.prompt)}
                  className="px-3 py-1 text-xs border border-[#e8e4db] rounded-full text-[#115740] hover:bg-[#f7f5f0] transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
