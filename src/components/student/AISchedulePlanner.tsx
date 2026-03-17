'use client';

import { useState, useRef, useEffect } from 'react';
import { Course } from '@/types';
import { sendChatMessage } from '@/lib/api-client';
import { Sparkles, Send, Loader2, ChevronDown, ChevronRight, CheckCircle2 } from 'lucide-react';

interface Semester {
  term: string;
  courses: { code: string; title: string; credits: number }[];
  totalCredits: number;
}

interface Props {
  completedCourses: Course[];
  currentCourses: Course[];
  plannedCourses: Course[];
  studentMajor?: string;
  creditsEarned: number;
  classYear: number;
  onClose: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  plan?: Semester[];
}

const CLARIFYING_PROMPT = `You are an academic advising AI for the Mason School of Business at William & Mary. The student wants you to build them a complete semester-by-semester course plan from now through graduation.

IMPORTANT: You must ask exactly 2-3 short clarifying questions BEFORE generating any plan. Ask all questions in a single message as a numbered list. Questions should cover:
1. Their interests/concentration preferences (e.g., finance, marketing, analytics, accounting)
2. Any scheduling constraints (e.g., prefer mornings, need lighter semesters, study abroad plans)
3. Elective interests or minor they want to pursue

Keep your questions concise and friendly. Do NOT generate a plan yet — just ask the questions.`;

const PLAN_PROMPT = `You are an academic advising AI for the Mason School of Business at William & Mary. Based on the student's answers, generate a complete semester-by-semester course plan through graduation.

CRITICAL: Your response MUST end with a JSON block in this exact format (after your text explanation):

\`\`\`json
{
  "semesters": [
    {
      "term": "Fall 2026",
      "courses": [
        {"code": "BUAD 311", "title": "Financial Management", "credits": 3},
        {"code": "BUAD 323", "title": "Management of Organizations", "credits": 3}
      ]
    }
  ]
}
\`\`\`

Rules for the plan:
- Each semester should have 14-16 credits (12 min, 18 max)
- Respect prerequisites (e.g., BUAD 300-level core requires pre-major prereqs)
- Include all remaining required courses for their major
- Fill remaining credits with electives aligned to their interests
- Include the business core courses they still need
- Label semesters as "Fall 20XX" or "Spring 20XX"
- Only include courses they haven't already completed
- The plan should get them to 120 total credits for graduation`;

export default function AISchedulePlanner({
  completedCourses,
  currentCourses,
  plannedCourses,
  studentMajor,
  creditsEarned,
  classYear,
  onClose,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<Semester[] | null>(null);
  const [expandedSemesters, setExpandedSemesters] = useState<Set<number>>(new Set([0, 1]));
  const [phase, setPhase] = useState<'init' | 'questions' | 'answered' | 'planning' | 'done'>('init');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-start: ask clarifying questions
  useEffect(() => {
    if (phase === 'init') {
      askClarifyingQuestions();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const completedCodes = completedCourses.map(c => c.code).join(', ');
  const currentCodes = currentCourses.map(c => c.code).join(', ');

  const studentContext = `Student info: Class of ${classYear}, ${creditsEarned} credits earned, ${studentMajor ? `declared ${studentMajor} major` : 'undeclared'}.
Completed courses: ${completedCodes || 'none'}.
Currently enrolled: ${currentCodes || 'none'}.
Credits remaining: ${120 - creditsEarned}.`;

  async function askClarifyingQuestions() {
    setLoading(true);
    setPhase('questions');
    try {
      const fullPrompt = `${CLARIFYING_PROMPT}\n\n${studentContext}\n\nAsk your 2-3 clarifying questions now.`;
      const response = await sendChatMessage(fullPrompt, conversationId);
      setConversationId(response.conversationId);
      setMessages([{ role: 'assistant', content: response.content }]);
    } catch (err) {
      setMessages([{ role: 'assistant', content: 'I\'d love to help plan your schedule! Could you tell me:\n\n1. What area of business interests you most (finance, marketing, analytics, accounting)?\n2. Do you have any scheduling preferences (morning/afternoon, lighter/heavier semesters, study abroad)?\n3. Are you pursuing a minor or have specific elective interests?' }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');

    const newMessages: Message[] = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);

    if (phase === 'questions') {
      // Student answered the questions — now generate the plan
      setPhase('planning');
      setLoading(true);
      try {
        const planPrompt = `${PLAN_PROMPT}\n\n${studentContext}\n\nStudent's preferences: "${userMsg}"\n\nGenerate the complete semester-by-semester plan now. Remember to end with the JSON block.`;
        const response = await sendChatMessage(planPrompt, conversationId);
        setConversationId(response.conversationId);

        // Try to extract JSON plan from response
        const jsonMatch = response.content.match(/```json\s*([\s\S]*?)```/);
        let extractedPlan: Semester[] | null = null;

        if (jsonMatch) {
          try {
            const parsed = JSON.parse(jsonMatch[1]);
            extractedPlan = (parsed.semesters || []).map((s: any) => ({
              term: s.term,
              courses: s.courses || [],
              totalCredits: (s.courses || []).reduce((sum: number, c: any) => sum + (c.credits || 3), 0),
            }));
          } catch { /* ignore parse errors */ }
        }

        // Clean the content (remove JSON block for display)
        const cleanContent = response.content.replace(/```json[\s\S]*?```/, '').trim();

        setMessages([...newMessages, { role: 'assistant', content: cleanContent, plan: extractedPlan || undefined }]);
        if (extractedPlan) {
          setPlan(extractedPlan);
          setExpandedSemesters(new Set(extractedPlan.map((_, i) => i)));
        }
        setPhase('done');
      } catch (err) {
        setMessages([...newMessages, { role: 'assistant', content: 'Sorry, I had trouble generating the plan. Please try again.' }]);
        setPhase('questions');
      } finally {
        setLoading(false);
      }
    } else if (phase === 'done') {
      // Follow-up adjustments
      setLoading(true);
      try {
        const adjustPrompt = `The student wants to adjust their plan: "${userMsg}"\n\nPlease update the plan accordingly. Include the updated JSON block at the end.`;
        const response = await sendChatMessage(adjustPrompt, conversationId);

        const jsonMatch = response.content.match(/```json\s*([\s\S]*?)```/);
        let extractedPlan: Semester[] | null = null;
        if (jsonMatch) {
          try {
            const parsed = JSON.parse(jsonMatch[1]);
            extractedPlan = (parsed.semesters || []).map((s: any) => ({
              term: s.term,
              courses: s.courses || [],
              totalCredits: (s.courses || []).reduce((sum: number, c: any) => sum + (c.credits || 3), 0),
            }));
          } catch { /* ignore */ }
        }

        const cleanContent = response.content.replace(/```json[\s\S]*?```/, '').trim();
        setMessages([...newMessages, { role: 'assistant', content: cleanContent, plan: extractedPlan || undefined }]);
        if (extractedPlan) {
          setPlan(extractedPlan);
          setExpandedSemesters(new Set(extractedPlan.map((_, i) => i)));
        }
      } catch {
        setMessages([...newMessages, { role: 'assistant', content: 'Sorry, I had trouble adjusting the plan.' }]);
      } finally {
        setLoading(false);
      }
    }
  }

  const toggleSemester = (idx: number) => {
    setExpandedSemesters(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const totalPlanCredits = plan ? plan.reduce((s, sem) => s + sem.totalCredits, 0) : 0;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-[#115740] px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 text-[#B9975B]" />
            <div>
              <h2 className="text-white font-semibold text-lg" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
                AI Schedule Planner
              </h2>
              <p className="text-white/60 text-sm">Plan your remaining semesters through graduation</p>
            </div>
          </div>
          <button onClick={onClose} className="text-white/60 hover:text-white text-sm px-3 py-1 rounded hover:bg-white/10 transition-colors">
            Close
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex min-h-0">
          {/* Chat side */}
          <div className="flex-1 flex flex-col border-r border-gray-200">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-lg px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-[#115740] text-white'
                      : 'bg-[#f7f5f0] text-gray-800 border border-[#e8e4db]'
                  }`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg px-4 py-3 flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-[#115740]" />
                    <span className="text-sm text-gray-500">
                      {phase === 'planning' ? 'Building your personalized plan...' : 'Thinking...'}
                    </span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-200 p-3">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                  placeholder={phase === 'questions' ? 'Answer the questions above...' : phase === 'done' ? 'Ask to adjust the plan...' : 'Type a message...'}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
                  disabled={loading || phase === 'init'}
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  className="px-4 py-2 bg-[#115740] text-white rounded-lg hover:bg-[#0d4632] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
              {phase === 'done' && (
                <p className="text-[11px] text-gray-400 mt-1.5">You can ask to swap courses, change semesters, add a minor, etc.</p>
              )}
            </div>
          </div>

          {/* Plan side */}
          <div className="w-80 flex flex-col bg-gray-50 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
              <h3 className="font-semibold text-[#115740] text-sm" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
                Your Plan
              </h3>
              {plan && (
                <p className="text-[11px] text-gray-500 mt-0.5">
                  {plan.length} semesters · {totalPlanCredits} credits · {creditsEarned + totalPlanCredits} total toward 120
                </p>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {!plan && !loading && (
                <div className="text-center py-8">
                  <Sparkles className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-400">Answer the questions to generate your plan</p>
                </div>
              )}
              {!plan && loading && phase === 'planning' && (
                <div className="text-center py-8">
                  <Loader2 className="h-8 w-8 text-[#115740] mx-auto mb-2 animate-spin" />
                  <p className="text-sm text-gray-500">Building your plan...</p>
                </div>
              )}
              {plan && plan.map((sem, i) => (
                <div key={i} className="border border-gray-200 rounded-lg bg-white overflow-hidden">
                  <button
                    onClick={() => toggleSemester(i)}
                    className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-gray-50 transition-colors text-left"
                  >
                    {expandedSemesters.has(i) ? (
                      <ChevronDown className="h-3.5 w-3.5 text-[#115740]" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
                    )}
                    <span className="font-semibold text-sm text-[#115740] flex-1">{sem.term}</span>
                    <span className="text-xs text-gray-400">{sem.totalCredits}cr</span>
                  </button>
                  {expandedSemesters.has(i) && (
                    <div className="border-t border-gray-100 px-3 py-2 space-y-1.5">
                      {sem.courses.map((c, j) => (
                        <div key={j} className="flex items-center gap-2 text-xs">
                          <CheckCircle2 className="h-3 w-3 text-[#B9975B] flex-shrink-0" />
                          <span className="font-medium text-[#115740]">{c.code}</span>
                          <span className="text-gray-500 truncate flex-1">{c.title}</span>
                          <span className="text-gray-400">{c.credits}cr</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* Summary stats */}
              {plan && (
                <div className="border-t border-gray-200 pt-3 mt-3 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Credits earned</span>
                    <span className="font-medium text-[#115740]">{creditsEarned}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Credits planned</span>
                    <span className="font-medium text-[#115740]">{totalPlanCredits}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-500">Projected total</span>
                    <span className="font-bold text-[#115740]">{creditsEarned + totalPlanCredits}/120</span>
                  </div>
                  <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mt-1">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(100, ((creditsEarned + totalPlanCredits) / 120) * 100)}%`,
                        background: 'linear-gradient(90deg, #115740, #B9975B)',
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
