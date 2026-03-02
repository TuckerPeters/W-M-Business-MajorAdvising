'use client';

import { Clock, X } from 'lucide-react';

interface PendingApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  advisorName?: string;
}

export default function PendingApprovalModal({ isOpen, onClose, advisorName }: PendingApprovalModalProps) {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-[60] transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 pointer-events-none">
        <div
          className="relative bg-white w-full max-w-[420px] shadow-2xl pointer-events-auto border-t-4 border-[#B9975B]"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 hover:bg-gray-100 rounded transition-colors z-10"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>

          <div className="px-8 pt-8 pb-8 text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-[#B9975B]/10 flex items-center justify-center mb-5">
              <Clock className="h-8 w-8 text-[#B9975B]" />
            </div>

            <h2
              className="text-[#115740] text-xl mb-3"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Account Under Review
            </h2>

            <p className="text-sm text-gray-600 leading-relaxed mb-2">
              {advisorName ? `Thank you, ${advisorName}.` : 'Thank you.'} Your advisor account
              request has been submitted and is currently being reviewed.
            </p>
            <p className="text-sm text-gray-500 leading-relaxed mb-6">
              An administrator will verify your credentials and approve your account shortly.
              You will be able to sign in once your account has been approved.
            </p>

            <div className="h-px bg-[#e8e4db] mb-6" />

            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4 mb-6 text-left">
              <p
                className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                What happens next?
              </p>
              <ul className="text-sm text-gray-600 space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="text-[#B9975B] font-semibold mt-0.5">1.</span>
                  Your request is reviewed by an administrator
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#B9975B] font-semibold mt-0.5">2.</span>
                  Your credentials are verified
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#B9975B] font-semibold mt-0.5">3.</span>
                  You receive access to the Advisor Portal
                </li>
              </ul>
            </div>

            <button
              onClick={onClose}
              className="w-full bg-[#115740] text-white py-2.5 rounded text-sm font-medium hover:bg-[#0d4632] transition-colors"
            >
              Return to Home
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
