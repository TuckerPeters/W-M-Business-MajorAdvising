'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AdviseeList from '@/components/advisor/AdviseeList';
import AdviseeDetail from '@/components/advisor/AdviseeDetail';
import AnalyticsDashboard from '@/components/advisor/AnalyticsDashboard';
import ManageStudents from '@/components/advisor/ManageStudents';
import AdvisorApprovals from '@/components/advisor/AdvisorApprovals';
import ChatInterface from '@/components/student/ChatInterface';
import Badge from '@/components/ui/Badge';
import { Advisee } from '@/types';
import {
  getAdvisees,
  getAdvisorProfile,
  getCommonQuestions,
  getAdvisorAlerts,
  getAdvisorConversations,
  sendAdvisorChatMessage,
  deleteAdvisorConversation,
  AdvisorAlert,
} from '@/lib/api-client';
import {
  Users,
  AlertTriangle,
  TrendingUp,
  MessageSquare,
  LogOut,
  ArrowLeft,
  Menu,
  X,
  BarChart3,
  UserCog,
  Shield,
} from 'lucide-react';

const VALID_ADVISOR_TABS = ['students', 'chat', 'analytics', 'manage', 'approvals'] as const;
type AdvisorTab = typeof VALID_ADVISOR_TABS[number];

function getInitialTab<T extends string>(validTabs: readonly T[], fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  const hash = window.location.hash.replace('#', '');
  return (validTabs as readonly string[]).includes(hash) ? (hash as T) : fallback;
}

const sidebarItems: { key: AdvisorTab; label: string; icon: typeof Users }[] = [
  { key: 'students', label: 'Students', icon: Users },
  { key: 'analytics', label: 'Analytics', icon: BarChart3 },
  { key: 'chat', label: 'AI Advisor', icon: MessageSquare },
  { key: 'manage', label: 'Manage Students', icon: UserCog },
  { key: 'approvals', label: 'Approvals', icon: Shield },
];

const advisorQuickPrompts = [
  { label: 'At-risk students?', prompt: 'Which of my advisees are at risk and why?' },
  { label: 'Undeclared students?', prompt: 'Which students should be declaring their major soon?' },
  { label: 'Course load review', prompt: 'Are any of my students overloaded this semester?' },
];

export default function AdvisorDashboard() {
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<AdvisorTab>(() => getInitialTab(VALID_ADVISOR_TABS, 'students'));

  // Sync tab to URL hash
  useEffect(() => {
    window.location.hash = activeTab;
  }, [activeTab]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedAdvisee, setSelectedAdvisee] = useState<Advisee | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const [advisees, setAdvisees] = useState<Advisee[]>([]);
  const [advisorName, setAdvisorName] = useState<string | null>(null);
  const [commonQuestions, setCommonQuestions] = useState<{ text: string; count: number }[]>([]);
  const [alerts, setAlerts] = useState<AdvisorAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [adviseeData, profileData, questionsData, alertsData] = await Promise.allSettled([
          getAdvisees(),
          getAdvisorProfile(),
          getCommonQuestions(5),
          getAdvisorAlerts(),
        ]);
        if (adviseeData.status === 'fulfilled') setAdvisees(adviseeData.value || []);
        if (profileData.status === 'fulfilled') setAdvisorName(profileData.value?.name || null);
        if (questionsData.status === 'fulfilled') setCommonQuestions(questionsData.value || []);
        if (alertsData.status === 'fulfilled') setAlerts(alertsData.value || []);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleAdviseeAdded = useCallback((advisee: Advisee) => {
    setAdvisees(prev => [...prev, advisee]);
  }, []);

  const handleAdviseeRemoved = useCallback((studentId: string) => {
    setAdvisees(prev => prev.filter(a => a.id !== studentId));
  }, []);

  const atRiskCount = advisees.filter(a =>
    a.riskFlags && Object.values(a.riskFlags).some(flag => flag)
  ).length;
  const undeclaredCount = advisees.filter(a => !a.declared).length;
  const avgGPA = advisees.length > 0
    ? advisees.reduce((sum, a) => sum + a.gpa, 0) / advisees.length
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="animate-spin h-10 w-10 border-4 border-[#115740] border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Green accent bar */}
      <div className="h-1.5 bg-[#115740]" />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-[72px]">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 hover:bg-gray-100 rounded transition-colors"
            >
              {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <a href="/" className="flex items-center gap-3">
              <span
                className="text-[#115740] text-2xl uppercase"
                style={{ fontFamily: '"Libre Baskerville", Baskerville, Georgia, serif', letterSpacing: '0.03em' }}
              >
                William{' '}
                <span className="text-[#B9975B] italic normal-case">&amp;</span>{' '}
                Mary
              </span>
            </a>

            {advisorName && (
              <span className="hidden sm:inline text-sm text-gray-500 border-l border-gray-300 pl-3 ml-1">
                {advisorName}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            {selectedAdvisee && activeTab === 'students' && (
              <button
                onClick={() => setSelectedAdvisee(null)}
                className="hidden md:inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to List
              </button>
            )}
            <Link
              href="/"
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
            >
              Home
            </Link>
            <button
              onClick={() => router.push('/')}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="max-w-7xl mx-auto px-6 pt-6 pb-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-400">
          <Link href="/" className="hover:text-[#115740]">Home</Link>
          <span>/</span>
          {selectedAdvisee && activeTab === 'students' ? (
            <>
              <button onClick={() => setSelectedAdvisee(null)} className="hover:text-[#115740]">
                Advisor Dashboard
              </button>
              <span>/</span>
              <span className="text-gray-600">{selectedAdvisee.name}</span>
            </>
          ) : (
            <span className="text-gray-600">Advisor Dashboard</span>
          )}
        </div>
      </div>

      {/* Slide-out sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={`fixed top-0 left-0 h-full w-[260px] bg-white z-50 shadow-xl transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="h-1.5 bg-[#115740]" />
        <div className="relative flex items-center px-5 py-4 border-b border-[#e8e4db]">
          <span
            className="text-[#115740] text-xl uppercase"
            style={{ fontFamily: '"Libre Baskerville", Baskerville, Georgia, serif', letterSpacing: '0.03em' }}
          >
            W<span className="text-[#B9975B] italic normal-case">&amp;</span>M
          </span>
          <button
            onClick={() => setSidebarOpen(false)}
            className="absolute right-4 p-1.5 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>
        <div className="border-t-4 border-[#B9975B] bg-[#f7f5f0]">
          <nav className="py-2">
            {sidebarItems.map((item) => (
              <button
                key={item.key}
                onClick={() => { setActiveTab(item.key); setSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-5 py-3.5 text-[15px] transition-colors border-b border-[#e8e4db] last:border-b-0 ${
                  activeTab === item.key
                    ? 'bg-[#115740] text-white'
                    : 'text-[#262626] hover:bg-[#eeebe4]'
                }`}
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                <item.icon className={`h-4 w-4 flex-shrink-0 ${activeTab === item.key ? 'text-white' : 'text-[#115740]'}`} />
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-6 pb-16 mt-2">
        <main>
          {/* Students Tab */}
          {activeTab === 'students' && (
            <>
              {!selectedAdvisee ? (
                <div className="space-y-6">
                  <h2
                    className="text-[#115740] text-2xl sm:text-3xl"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    Advisor Dashboard
                  </h2>

                  {/* Stats Overview */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-5">
                      <p className="text-sm text-gray-500 mb-1" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>Total Advisees</p>
                      <div className="flex items-center gap-2">
                        <span className="text-3xl font-bold text-[#115740]">{advisees.length}</span>
                        <Users className="h-5 w-5 text-[#B9975B]" />
                      </div>
                    </div>

                    <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-5">
                      <p className="text-sm text-gray-500 mb-1" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>At Risk</p>
                      <div className="flex items-center gap-2">
                        <span className="text-3xl font-bold text-red-600">{atRiskCount}</span>
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                      </div>
                    </div>

                    <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-5">
                      <p className="text-sm text-gray-500 mb-1" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>Undeclared</p>
                      <div className="flex items-center gap-2">
                        <span className="text-3xl font-bold text-[#115740]">{undeclaredCount}</span>
                      </div>
                    </div>

                    <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-5">
                      <p className="text-sm text-gray-500 mb-1" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>Average GPA</p>
                      <div className="flex items-center gap-2">
                        <span className="text-3xl font-bold text-[#115740]">{avgGPA.toFixed(2)}</span>
                        <TrendingUp className="h-5 w-5 text-[#B9975B]" />
                      </div>
                    </div>
                  </div>

                  {/* Advisee List + Sidebar */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <AdviseeList
                        advisees={advisees}
                        onSelectAdvisee={setSelectedAdvisee}
                      />
                    </div>

                    {/* Quick Actions */}
                    <div className="space-y-6">
                      <div className="border-t-4 border-[#B9975B] bg-[#f7f5f0]">
                        <div className="px-5 pt-4 pb-2">
                          <h3
                            className="text-[#115740] font-semibold text-[15px] uppercase tracking-wider"
                            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                          >
                            Quick Actions
                          </h3>
                        </div>
                        <div className="px-5 pb-4 space-y-2">
                          <button
                            onClick={() => setActiveTab('analytics')}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#262626] border border-[#e8e4db] rounded hover:bg-[#eeebe4] transition-colors"
                          >
                            <BarChart3 className="h-4 w-4 text-[#115740]" />
                            Analytics Dashboard
                          </button>
                          <button
                            onClick={() => setActiveTab('chat')}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#262626] border border-[#e8e4db] rounded hover:bg-[#eeebe4] transition-colors"
                          >
                            <MessageSquare className="h-4 w-4 text-[#115740]" />
                            AI Advisor Chat
                          </button>
                          <button
                            onClick={() => setActiveTab('manage')}
                            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#262626] border border-[#e8e4db] rounded hover:bg-[#eeebe4] transition-colors"
                          >
                            <UserCog className="h-4 w-4 text-[#115740]" />
                            Manage Students
                          </button>
                        </div>
                      </div>

                      <div className="border-t-4 border-[#B9975B] bg-[#f7f5f0]">
                        <div className="px-5 pt-4 pb-2">
                          <h3
                            className="text-[#115740] font-semibold text-[15px] uppercase tracking-wider"
                            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                          >
                            Common Questions
                          </h3>
                          <p className="text-xs text-gray-500 mt-0.5">Clustered by similarity</p>
                        </div>
                        <div className="px-5 pb-4 space-y-2">
                          {commonQuestions.length > 0 ? (
                            commonQuestions.map((q, i) => (
                              <div key={i} className="p-3 rounded border border-[#e8e4db] bg-white text-sm">
                                <p className="font-medium mb-1 text-[#262626]">{q.text}</p>
                                <Badge variant="secondary">Asked {q.count} {q.count === 1 ? 'time' : 'times'}</Badge>
                              </div>
                            ))
                          ) : (
                            <p className="text-sm text-gray-400 py-2">No similar questions yet</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <button
                    onClick={() => setSelectedAdvisee(null)}
                    className="inline-flex items-center gap-1.5 mb-4 text-sm text-[#115740] hover:text-[#0d4632] transition-colors"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Advisee List
                  </button>
                  <AdviseeDetail advisee={selectedAdvisee} />
                </div>
              )}
            </>
          )}

          {/* Analytics Tab */}
          {activeTab === 'analytics' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Analytics Dashboard
              </h2>
              <AnalyticsDashboard
                advisees={advisees}
                alerts={alerts}
                commonQuestions={commonQuestions}
              />
            </>
          )}

          {/* AI Advisor Chat Tab */}
          {activeTab === 'chat' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                AI Advisor Assistant
              </h2>
              <div className="h-[calc(100vh-280px)]">
                <ChatInterface
                  activeConversationId={activeConversationId}
                  onConversationChange={setActiveConversationId}
                  sendMessageFn={sendAdvisorChatMessage}
                  listConversationsFn={getAdvisorConversations}
                  deleteConversationFn={deleteAdvisorConversation}
                  quickPrompts={advisorQuickPrompts}
                  title="AI Advisor Assistant"
                  subtitle="Ask about your advisees, risks, course loads, and planning"
                />
              </div>
            </>
          )}

          {/* Manage Students Tab */}
          {activeTab === 'manage' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Manage Students
              </h2>
              <ManageStudents
                advisees={advisees}
                onAdviseeAdded={handleAdviseeAdded}
                onAdviseeRemoved={handleAdviseeRemoved}
              />
            </>
          )}

          {activeTab === 'approvals' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Advisor Account Approvals
              </h2>
              <AdvisorApprovals />
            </>
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="bg-[#262626] text-white">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">
              Mason School of Business &middot; Academic Advising Platform
            </p>
            <img
              src="/buisness_emblem.png"
              alt="Mason School of Business"
              className="h-10 w-auto opacity-60"
            />
          </div>
        </div>
      </footer>
    </div>
  );
}
