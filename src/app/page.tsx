'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  GraduationCap,
  Users,
  MessageSquare,
  BarChart3,
  Shield,
  ArrowRight,
  LogOut,
  User,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import LoginModal from '@/components/auth/LoginModal';

const navItems = [
  { label: 'Student Portal', href: '/student', icon: GraduationCap },
  { label: 'Advisor Portal', href: '/advisor', icon: Users },
];

const isDemo = process.env.NEXT_PUBLIC_DEBUG === 'true';

export default function Home() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const [loginRole, setLoginRole] = useState<'student' | 'advisor' | null>(null);
  const canNavigate = !!user || isDemo;

  const handleSignOut = async () => {
    await signOut();
  };

  return (
    <div className="min-h-screen bg-white">
      {/* ===== GREEN ACCENT BAR (top edge) ===== */}
      <div className="h-1.5 bg-[#115740]" />

      {/* ===== DEMO BANNER ===== */}
      {isDemo && (
        <div className="bg-[#B9975B]/15 border-b border-[#B9975B]/30 px-6 py-2.5">
          <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-sm text-[#8a7040]">
            <span className="font-semibold">Demo Mode</span>
            <span className="text-[#8a7040]/60">|</span>
            <span>Explore the platform with sample data &mdash; no login required</span>
          </div>
        </div>
      )}

      {/* ===== HEADER — matches W&M site ===== */}
      <header className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-[72px]">
          {/* W&M Wordmark */}
          <a href="https://mason.wm.edu/" className="flex items-center gap-3">
            <span
              className="text-[#115740] text-2xl uppercase"
              style={{ fontFamily: '"Libre Baskerville", Baskerville, Georgia, serif', letterSpacing: '0.03em' }}
            >
              William{' '}
              <span className="text-[#B9975B] italic normal-case">&amp;</span>{' '}
              Mary
            </span>
          </a>

          {/* Right nav */}
          <div className="flex items-center gap-1">
            {user ? (
              <>
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-[#115740]">
                  <User className="h-4 w-4" />
                  <span style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
                    {user.displayName || user.email?.split('@')[0] || 'User'}
                  </span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </button>
              </>
            ) : isDemo ? (
              <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-[#B9975B] font-medium">
                Demo Mode
              </span>
            ) : (
              <>
                <button
                  onClick={() => setLoginRole('student')}
                  className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
                >
                  Student Login
                </button>
                <button
                  onClick={() => setLoginRole('advisor')}
                  className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
                >
                  Advisor Login
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ===== HERO BANNER ===== */}
      <div
        className="relative h-[280px] sm:h-[340px] bg-cover bg-center"
        style={{
          backgroundImage: `linear-gradient(to bottom, rgba(17,87,64,0.25), rgba(17,87,64,0.65)),
            url('/alan-b-miller-hall-courtyard.jpg')`,
        }}
      >
        <div className="absolute inset-0 flex items-center">
          <div className="max-w-7xl mx-auto px-6 w-full">
            <h1
              className="text-white text-3xl sm:text-5xl leading-tight max-w-xl"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Mason School of Business
              <br />
              <span className="text-[#B9975B]">Academic Advising</span>
            </h1>
          </div>
        </div>
      </div>

      {/* ===== BREADCRUMB ===== */}
      <div className="max-w-7xl mx-auto px-6 pt-6 pb-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-400">
          <a href="https://mason.wm.edu/" className="hover:text-[#115740]">Home</a>
          <span>/</span>
          <a href="https://mason.wm.edu/undergraduate/academics/" className="hover:text-[#115740]">Academics</a>
          <span>/</span>
          <span className="text-gray-600">Advising Platform</span>
        </div>
      </div>

      {/* ===== MAIN LAYOUT: sidebar + content ===== */}
      <div className="max-w-7xl mx-auto px-6 pb-16 flex flex-col lg:flex-row gap-10 mt-2">
        {/* LEFT SIDEBAR — W&M style with gold top bar */}
        <aside className="lg:w-[260px] flex-shrink-0">
          <div className="border-t-4 border-[#B9975B] bg-[#f7f5f0] pt-1">
            <nav className="py-2">
              {navItems.map((item) => {
                const isAdvisorLink = item.href.startsWith('/advisor');
                if (!canNavigate) {
                  return (
                    <button
                      key={item.label}
                      onClick={() => setLoginRole(isAdvisorLink ? 'advisor' : 'student')}
                      className="w-full flex items-center gap-3 px-5 py-3 text-[15px] text-[#262626] hover:bg-[#eeebe4] transition-colors border-b border-[#e8e4db] last:border-b-0 text-left"
                      style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                    >
                      <item.icon className="h-4 w-4 text-[#115740] flex-shrink-0" />
                      {item.label}
                    </button>
                  );
                }
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className="flex items-center gap-3 px-5 py-3 text-[15px] text-[#262626] hover:bg-[#eeebe4] transition-colors border-b border-[#e8e4db] last:border-b-0"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    <item.icon className="h-4 w-4 text-[#115740] flex-shrink-0" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* MAIN CONTENT */}
        <main className="flex-1 min-w-0">
          {/* Page title */}
          <h2
            className="text-[#115740] text-2xl sm:text-3xl mb-2"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            Advising Platform
          </h2>
          <p className="text-gray-600 mb-8 leading-relaxed max-w-2xl">
            Your AI-powered advising assistant for course planning, degree requirements,
            and major declaration guidance at the Mason School of Business.
          </p>

          {/* Portal cards */}
          <div className="grid sm:grid-cols-2 gap-5 mb-10">
            <button onClick={() => canNavigate ? router.push('/student') : setLoginRole('student')} className="group text-left">
              <div className="border border-gray-200 rounded bg-white p-6 hover:shadow-lg transition-all duration-200 hover:border-[#115740]/30">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded bg-[#115740] flex items-center justify-center flex-shrink-0">
                    <GraduationCap className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3
                      className="text-lg text-[#115740] mb-1 group-hover:underline"
                      style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                    >
                      Student Portal
                    </h3>
                    <p className="text-sm text-gray-500 leading-relaxed">
                      Track your progress toward graduation, chat with the AI advisor,
                      and build your course schedule.
                    </p>
                    <span className="inline-flex items-center gap-1 text-sm text-[#115740] mt-3 font-medium">
                      Open <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                    </span>
                  </div>
                </div>
              </div>
            </button>

            <button onClick={() => canNavigate ? router.push('/advisor') : setLoginRole('advisor')} className="group text-left">
              <div className="border border-gray-200 rounded bg-white p-6 hover:shadow-lg transition-all duration-200 hover:border-[#115740]/30">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded bg-[#262626] flex items-center justify-center flex-shrink-0">
                    <Users className="h-6 w-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3
                      className="text-lg text-[#115740] mb-1 group-hover:underline"
                      style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                    >
                      Advisor Portal
                    </h3>
                    <p className="text-sm text-gray-500 leading-relaxed">
                      View your advisees, review AI conversations, flag at-risk students,
                      and manage caseloads.
                    </p>
                    <span className="inline-flex items-center gap-1 text-sm text-[#115740] mt-3 font-medium">
                      Open <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                    </span>
                  </div>
                </div>
              </div>
            </button>
          </div>

          {/* Features heading */}
          <h3
            className="text-[#115740] text-xl mb-4"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            Platform Features
          </h3>

          {/* Features list — W&M school card style, single column */}
          <div className="space-y-4">
            {[
              {
                icon: MessageSquare,
                title: 'AI-Powered Chat Advising',
                desc: 'Get instant, source-grounded answers about prerequisites, degree requirements, and course planning from our RAG-powered advisor.',
              },
              {
                icon: BarChart3,
                title: 'Real-Time Degree Tracking',
                desc: 'See credits earned, milestones completed, GPA trends, and exactly what you need to finish before graduation.',
              },
              {
                icon: Shield,
                title: 'Advisor Dashboard & Oversight',
                desc: 'Faculty advisors get a 360-degree view of advisees with the ability to review and supplement AI recommendations.',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="relative bg-[#f7f5f0] border border-[#e8e4db] rounded p-5 flex items-start gap-5 hover:bg-[#f0ede5] transition-colors"
              >
                <feature.icon className="h-10 w-10 text-[#B9975B] flex-shrink-0 mt-0.5" strokeWidth={1.3} />
                <div className="flex-1 min-w-0">
                  <h4
                    className="text-[#115740] font-semibold text-[15px] uppercase tracking-wider mb-1.5"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    {feature.title}
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    {feature.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>

        </main>
      </div>

      {/* ===== FOOTER ===== */}
      <footer className="bg-[#262626] text-white">
        <div className="max-w-7xl mx-auto px-6 py-10">
          <div className="flex items-start justify-between gap-8">
            <div className="flex items-start gap-3 flex-1">
              <Shield className="h-5 w-5 text-gray-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4
                  className="text-white font-semibold mb-2"
                  style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                >
                  About This Platform
                </h4>
                <p className="text-sm text-gray-400 leading-relaxed">
                  This platform uses Retrieval-Augmented Generation (RAG) to provide accurate,
                  source-grounded academic guidance to pre-major and declared business students
                  at William &amp; Mary. All AI responses cite official catalog data. Faculty
                  advisors maintain full oversight and can review, correct, and supplement
                  AI recommendations at any time.
                </p>
              </div>
            </div>
            <img
              src="/buisness_emblem.png"
              alt="Mason School of Business"
              className="h-16 w-auto opacity-60 flex-shrink-0 mt-4"
            />
          </div>
        </div>
      </footer>

      {/* ===== LOGIN MODAL ===== */}
      {loginRole && (
        <LoginModal
          isOpen={true}
          onClose={() => setLoginRole(null)}
          role={loginRole}
        />
      )}
    </div>
  );
}
