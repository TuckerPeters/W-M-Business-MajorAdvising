'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X } from 'lucide-react';
import Input from '@/components/ui/Input';
import PendingApprovalModal from './PendingApprovalModal';
import StudentOnboarding from './StudentOnboarding';
import { registerAdvisorAccount, getAdvisorAccountStatus } from '@/lib/advisor-approval-store';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  role: 'student' | 'advisor';
}

export default function LoginModal({ isOpen, onClose, role }: LoginModalProps) {
  const router = useRouter();
  const [tab, setTab] = useState<'signin' | 'create'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [showPendingModal, setShowPendingModal] = useState(false);
  const [pendingName, setPendingName] = useState('');
  const [showOnboarding, setShowOnboarding] = useState(false);

  if (!isOpen) return null;

  const destination = role === 'student' ? '/student' : '/advisor';
  const title = role === 'student' ? 'Student Login' : 'Advisor Login';

  const validateWmEmail = (emailToCheck: string) => {
    if (role === 'student' && tab === 'create' && !emailToCheck.toLowerCase().endsWith('@wm.edu')) {
      setError('Please use your W&M email address (@wm.edu).');
      return false;
    }
    return true;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please fill in all required fields.');
      return;
    }

    if (tab === 'create') {
      if (!name) {
        setError('Please enter your name.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
      if (password.length < 6) {
        setError('Password must be at least 6 characters.');
        return;
      }

      // Advisor account creation → register and show pending modal
      if (role === 'advisor') {
        registerAdvisorAccount(email, name);
        setPendingName(name);
        setShowPendingModal(true);
        return;
      }

      // Student account creation → validate @wm.edu then show onboarding
      if (!validateWmEmail(email)) return;
      setShowOnboarding(true);
      return;
    }

    // Sign in flow — check advisor approval status
    if (role === 'advisor') {
      const account = getAdvisorAccountStatus(email);
      if (account && account.status === 'pending') {
        setPendingName(account.name);
        setShowPendingModal(true);
        return;
      }
      // Approved or no account (demo fallthrough) → allow login
    }

    router.push(destination);
  };

  const handleSSO = (provider: 'google' | 'microsoft' | 'blackboard') => {
    setError('');

    if (tab === 'create' && role === 'advisor') {
      registerAdvisorAccount(email || `sso-${Date.now()}@wm.edu`, name || 'Advisor');
      setPendingName(name || 'Advisor');
      setShowPendingModal(true);
      return;
    }

    // Student create account via SSO
    if (tab === 'create' && role === 'student') {
      if (provider === 'blackboard') {
        // Blackboard has their data — go straight to dashboard
        router.push(destination);
        return;
      }
      // Google/Microsoft — validate @wm.edu if email entered, then show onboarding
      if (email && !validateWmEmail(email)) return;
      setShowOnboarding(true);
      return;
    }

    router.push(destination);
  };

  const switchTab = (newTab: 'signin' | 'create') => {
    setTab(newTab);
    setError('');
    setName('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
  };

  // Blackboard SVG icon
  const blackboardIcon = (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id="bb-grad" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#0056D2" />
          <stop offset="60%" stopColor="#00875A" />
          <stop offset="100%" stopColor="#8CC63F" />
        </linearGradient>
      </defs>
      <rect width="24" height="24" rx="3" fill="url(#bb-grad)" />
      <path d="M12 4L5.5 20h3.8l2.7-7.5L14.7 20h3.8L12 4z" fill="white" />
    </svg>
  );

  // Google SVG icon
  const googleIcon = (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );

  // Microsoft SVG icon
  const microsoftIcon = (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );

  // SSO button order: students get Blackboard first (recommended), advisors get original order
  const ssoButtons = role === 'student'
    ? [
        { provider: 'blackboard' as const, icon: blackboardIcon, label: 'Continue with Blackboard', recommended: true },
        { provider: 'google' as const, icon: googleIcon, label: 'Continue with Google', recommended: false },
        { provider: 'microsoft' as const, icon: microsoftIcon, label: 'Continue with Microsoft', recommended: false },
      ]
    : [
        { provider: 'google' as const, icon: googleIcon, label: 'Continue with Google', recommended: false },
        { provider: 'microsoft' as const, icon: microsoftIcon, label: 'Continue with Microsoft', recommended: false },
        { provider: 'blackboard' as const, icon: blackboardIcon, label: 'Continue with Blackboard', recommended: false },
      ];

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className="relative bg-white w-full max-w-[420px] shadow-2xl pointer-events-auto border-t-4 border-[#B9975B]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 hover:bg-gray-100 rounded transition-colors z-10"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>

          {/* Header */}
          <div className="px-8 pt-8 pb-4">
            <div className="flex items-center gap-3 mb-1">
              <img
                src="/buisness_emblem.png"
                alt="Mason School of Business"
                className="h-14 w-auto -ml-2"
              />
              <h2
                className="text-[#115740] text-xl"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                {title}
              </h2>
            </div>
            <p className="text-sm text-gray-500 mt-2 ml-[52px]">
              {role === 'student'
                ? 'Access your courses, degree progress, and AI advisor.'
                : 'View advisees, review conversations, and manage caseloads.'}
            </p>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 mx-8">
            <button
              onClick={() => switchTab('signin')}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                tab === 'signin'
                  ? 'text-[#115740] border-b-2 border-[#115740]'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Sign In
            </button>
            <button
              onClick={() => switchTab('create')}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                tab === 'create'
                  ? 'text-[#115740] border-b-2 border-[#115740]'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Create Account
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-8 pt-6 pb-8 space-y-4">
            {tab === 'create' && (
              <div>
                <label className="block text-sm text-gray-600 mb-1.5">Full Name</label>
                <Input
                  type="text"
                  placeholder="Enter your full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="border-gray-300 focus-visible:ring-[#115740]"
                />
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-600 mb-1.5">Email</label>
              <Input
                type="email"
                placeholder="you@wm.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="border-gray-300 focus-visible:ring-[#115740]"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1.5">Password</label>
              <Input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="border-gray-300 focus-visible:ring-[#115740]"
              />
            </div>

            {tab === 'create' && (
              <div>
                <label className="block text-sm text-gray-600 mb-1.5">Confirm Password</label>
                <Input
                  type="password"
                  placeholder="Confirm your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="border-gray-300 focus-visible:ring-[#115740]"
                />
              </div>
            )}

            {error && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</p>
            )}

            <button
              type="submit"
              className="w-full bg-[#115740] text-white py-2.5 rounded text-sm font-medium hover:bg-[#0d4632] transition-colors"
            >
              {tab === 'signin' ? 'Sign In' : 'Create Account'}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3 py-1">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs text-gray-400 uppercase tracking-wider">or continue with</span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>

            {/* SSO buttons */}
            {ssoButtons.map((btn) => (
              <button
                key={btn.provider}
                type="button"
                onClick={() => handleSSO(btn.provider)}
                className={`w-full flex items-center justify-center gap-3 py-2.5 rounded text-sm font-medium transition-colors ${
                  btn.recommended
                    ? 'border-2 border-[#B9975B] text-[#115740] bg-[#f7f5f0] hover:bg-[#eeebe4]'
                    : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                {btn.icon}
                {btn.label}
                {btn.recommended && (
                  <span className="text-[10px] uppercase tracking-wider text-[#B9975B] font-semibold ml-1">
                    Recommended
                  </span>
                )}
              </button>
            ))}
          </form>
        </div>
      </div>

      <PendingApprovalModal
        isOpen={showPendingModal}
        onClose={() => {
          setShowPendingModal(false);
          onClose();
        }}
        advisorName={pendingName}
      />

      {showOnboarding && (
        <StudentOnboarding
          studentName={name}
          studentEmail={email}
          onClose={() => {
            setShowOnboarding(false);
            onClose();
          }}
          onComplete={() => {
            router.push('/student');
          }}
        />
      )}
    </>
  );
}
