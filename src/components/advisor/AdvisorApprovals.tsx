'use client';

import { useState, useEffect } from 'react';
import {
  getAllAdvisorAccounts,
  approveAdvisorAccount,
  removeAdvisorAccount,
  AdvisorAccount,
} from '@/lib/advisor-approval-store';
import {
  CheckCircle2,
  XCircle,
  Clock,
  UserCheck,
} from 'lucide-react';

const serif = 'Georgia, "Times New Roman", serif';

export default function AdvisorApprovals() {
  const [accounts, setAccounts] = useState<AdvisorAccount[]>([]);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    setAccounts(getAllAdvisorAccounts());
  }, []);

  const handleApprove = (email: string) => {
    approveAdvisorAccount(email);
    setAccounts(getAllAdvisorAccounts());
    setFeedback({ type: 'success', message: `Approved ${email}` });
    setTimeout(() => setFeedback(null), 3000);
  };

  const handleReject = (email: string) => {
    removeAdvisorAccount(email);
    setAccounts(getAllAdvisorAccounts());
    setFeedback({ type: 'success', message: `Rejected and removed ${email}` });
    setTimeout(() => setFeedback(null), 3000);
  };

  const pending = accounts.filter(a => a.status === 'pending');
  const approved = accounts.filter(a => a.status === 'approved');

  return (
    <div className="space-y-6">
      {/* Feedback */}
      {feedback && (
        <div className={`flex items-center gap-2 text-sm p-3 rounded border ${
          feedback.type === 'success'
            ? 'bg-green-50 border-green-200 text-green-800'
            : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          {feedback.message}
        </div>
      )}

      {/* Pending Requests */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3
            className="text-[#115740] font-semibold text-base flex items-center gap-2"
            style={{ fontFamily: serif }}
          >
            <Clock className="h-4 w-4" />
            Pending Approval Requests
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {pending.length} request{pending.length !== 1 ? 's' : ''} awaiting review
          </p>
        </div>
        <div className="divide-y divide-[#e8e4db]">
          {pending.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No pending requests</p>
          ) : (
            pending.map((account) => (
              <div key={account.email} className="flex items-center justify-between py-3 px-6">
                <div className="min-w-0 flex-1">
                  <span className="font-semibold text-[#262626] text-sm">{account.name}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {account.email} &middot; Requested {new Date(account.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2 ml-3">
                  <button
                    onClick={() => handleApprove(account.email)}
                    className="px-3 py-1.5 text-xs font-medium bg-[#115740] text-white rounded hover:bg-[#0d4632] transition-colors flex items-center gap-1"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(account.email)}
                    className="px-3 py-1.5 text-xs font-medium border border-red-200 text-red-700 rounded hover:bg-red-50 transition-colors flex items-center gap-1"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Approved Advisors */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3
            className="text-[#115740] font-semibold text-base flex items-center gap-2"
            style={{ fontFamily: serif }}
          >
            <UserCheck className="h-4 w-4" />
            Approved Advisors
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {approved.length} advisor{approved.length !== 1 ? 's' : ''} approved
          </p>
        </div>
        <div className="divide-y divide-[#e8e4db]">
          {approved.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No approved advisors yet</p>
          ) : (
            approved.map((account) => (
              <div key={account.email} className="flex items-center justify-between py-3 px-6">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#262626] text-sm">{account.name}</span>
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[#115740] text-white">
                      Approved
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{account.email}</p>
                </div>
                <button
                  onClick={() => handleReject(account.email)}
                  className="flex-shrink-0 ml-3 px-3 py-1.5 text-xs font-medium border border-red-200 text-red-700 rounded hover:bg-red-50 transition-colors"
                >
                  Revoke
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
