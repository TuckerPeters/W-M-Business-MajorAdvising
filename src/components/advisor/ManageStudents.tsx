'use client';

import { useState } from 'react';
import { Advisee } from '@/types';
import { assignAdvisee, removeAdvisee } from '@/lib/api-client';
import {
  UserPlus,
  UserMinus,
  Search,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';

const serif = 'Georgia, "Times New Roman", serif';

interface ManageStudentsProps {
  advisees: Advisee[];
  onAdviseeAdded: (advisee: Advisee) => void;
  onAdviseeRemoved: (studentId: string) => void;
}

export default function ManageStudents({ advisees, onAdviseeAdded, onAdviseeRemoved }: ManageStudentsProps) {
  const [studentId, setStudentId] = useState('');
  const [addLoading, setAddLoading] = useState(false);
  const [removeLoadingId, setRemoveLoadingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAdvisees = advisees.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAdd = async () => {
    const id = studentId.trim();
    if (!id) return;

    if (advisees.some(a => a.id === id)) {
      setFeedback({ type: 'error', message: 'This student is already in your advisee list.' });
      return;
    }

    setAddLoading(true);
    setFeedback(null);
    try {
      const newAdvisee = await assignAdvisee(id);
      onAdviseeAdded(newAdvisee);
      setStudentId('');
      setFeedback({ type: 'success', message: `Successfully added ${newAdvisee.name || id}.` });
    } catch (err: any) {
      const msg = err?.message || 'Failed to add student.';
      if (msg.includes('404')) {
        setFeedback({ type: 'error', message: 'Student not found. Check the student ID and try again.' });
      } else {
        setFeedback({ type: 'error', message: msg });
      }
    } finally {
      setAddLoading(false);
    }
  };

  const handleRemove = async (id: string, name: string) => {
    setRemoveLoadingId(id);
    setFeedback(null);
    try {
      await removeAdvisee(id);
      onAdviseeRemoved(id);
      setFeedback({ type: 'success', message: `Removed ${name} from your advisee list.` });
    } catch (err: any) {
      setFeedback({ type: 'error', message: err?.message || 'Failed to remove student.' });
    } finally {
      setRemoveLoadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Add Student */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3 className="text-[#115740] font-semibold text-base flex items-center gap-2" style={{ fontFamily: serif }}>
            <UserPlus className="h-4 w-4" />
            Add Student
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">Enter a student ID to add them to your advisee list</p>
        </div>
        <div className="p-6">
          <div className="flex gap-2">
            <input
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
              placeholder="Student ID (e.g., demo-student)"
              disabled={addLoading}
              className="flex-1 h-10 rounded border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent disabled:opacity-50"
            />
            <button
              onClick={handleAdd}
              disabled={addLoading || !studentId.trim()}
              className="h-10 px-4 rounded bg-[#115740] text-white text-sm font-medium flex items-center gap-2 hover:bg-[#0d4632] transition-colors disabled:opacity-50"
            >
              {addLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserPlus className="h-4 w-4" />
              )}
              Add
            </button>
          </div>

          {feedback && (
            <div className={`mt-3 flex items-center gap-2 text-sm p-3 rounded border ${
              feedback.type === 'success'
                ? 'bg-green-50 border-green-200 text-green-800'
                : 'bg-red-50 border-red-200 text-red-800'
            }`}>
              {feedback.type === 'success' ? (
                <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              ) : (
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
              )}
              {feedback.message}
            </div>
          )}
        </div>
      </div>

      {/* Current Advisees */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3 className="text-[#115740] font-semibold text-base flex items-center gap-2" style={{ fontFamily: serif }}>
            <UserMinus className="h-4 w-4" />
            Current Advisees
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">{advisees.length} student{advisees.length !== 1 ? 's' : ''} assigned</p>
        </div>

        {/* Search */}
        <div className="px-6 pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search advisees..."
              className="w-full h-9 pl-9 pr-3 rounded border border-[#e8e4db] bg-white text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
            />
          </div>
        </div>

        <div className="p-4 max-h-[500px] overflow-y-auto divide-y divide-[#e8e4db]">
          {filteredAdvisees.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              {advisees.length === 0 ? 'No advisees yet' : 'No matching advisees'}
            </p>
          ) : (
            filteredAdvisees.map((advisee) => (
              <div
                key={advisee.id}
                className="flex items-center justify-between py-3 px-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-[#262626]">{advisee.name}</span>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                      advisee.declared
                        ? 'bg-[#115740] text-white'
                        : 'bg-[#B9975B]/20 text-[#8a6e3b]'
                    }`}>
                      {advisee.declared ? 'Declared' : 'Pre-major'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {advisee.id} &middot; GPA {advisee.gpa.toFixed(2)} &middot; {advisee.creditsEarned} credits
                  </p>
                </div>
                <button
                  onClick={() => handleRemove(advisee.id, advisee.name)}
                  disabled={removeLoadingId === advisee.id}
                  className="flex-shrink-0 ml-3 px-3 py-1.5 text-xs font-medium border border-red-200 text-red-700 rounded hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  {removeLoadingId === advisee.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    'Remove'
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
