'use client';

import { useEffect, useState } from 'react';
import { Advisee, Course, Milestone } from '@/types';
import { getStudentCoursesForAdvisor, getStudentMilestonesForAdvisor } from '@/lib/api-client';
import {
  Mail, MessageSquare, AlertTriangle, CheckCircle2, Circle,
  BookOpen, GraduationCap, Clock, AlertCircle,
} from 'lucide-react';

interface AdviseeDetailProps {
  advisee: Advisee;
}

const serif = 'Georgia, "Times New Roman", serif';

export default function AdviseeDetail({ advisee }: AdviseeDetailProps) {
  const [courses, setCourses] = useState<{ current: Course[]; completed: Course[]; planned: Course[] }>({
    current: [], completed: [], planned: [],
  });
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const [coursesData, milestonesData] = await Promise.allSettled([
        getStudentCoursesForAdvisor(advisee.id),
        getStudentMilestonesForAdvisor(advisee.id),
      ]);
      if (coursesData.status === 'fulfilled') setCourses(coursesData.value);
      if (milestonesData.status === 'fulfilled') setMilestones(milestonesData.value || []);
      setLoading(false);
    };
    load();
  }, [advisee.id]);

  const creditsEarned = courses.completed.length > 0
    ? courses.completed.reduce((sum, c) => sum + c.credits, 0)
    : advisee.creditsEarned;
  const currentCredits = courses.current.reduce((sum, c) => sum + c.credits, 0);
  const graduationProgress = Math.min((creditsEarned / 120) * 100, 100);
  const declarationWindow = creditsEarned >= 39 && creditsEarned < 54;
  const hasRisks = Object.values(advisee.riskFlags).some(f => f);

  return (
    <div className="space-y-6">
      {/* Student Header */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-[#115740] font-semibold text-xl" style={{ fontFamily: serif }}>
                {advisee.name}
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">{advisee.email}</p>
            </div>
            <div className="flex gap-2">
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[#e8e4db] rounded hover:bg-[#f7f5f0] text-[#262626] transition-colors">
                <Mail className="h-3.5 w-3.5" /> Email
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[#e8e4db] rounded hover:bg-[#f7f5f0] text-[#262626] transition-colors">
                <MessageSquare className="h-3.5 w-3.5" /> Message
              </button>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: serif }}>Class Year</p>
              <p className="text-2xl font-bold text-[#115740]">{advisee.classYear}</p>
            </div>
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: serif }}>GPA</p>
              <p className="text-2xl font-bold text-[#115740]">{advisee.gpa.toFixed(2)}</p>
            </div>
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: serif }}>Credits Earned</p>
              <p className="text-2xl font-bold text-[#115740]">{creditsEarned}</p>
            </div>
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: serif }}>Enrolled Credits</p>
              <p className="text-2xl font-bold text-[#115740]">{currentCredits}</p>
            </div>
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: serif }}>Status</p>
              <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                advisee.declared
                  ? 'bg-[#115740] text-white'
                  : 'bg-[#B9975B]/20 text-[#8a6e3b]'
              }`}>
                {advisee.declared ? 'Declared' : 'Pre-major'}
              </span>
              {advisee.intendedMajor && (
                <p className="text-sm font-medium text-[#262626] mt-1">{advisee.intendedMajor}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Risk Alerts */}
      {hasRisks && (
        <div className="border border-red-200 rounded bg-white">
          <div className="px-6 py-4 border-b border-red-200 bg-red-50">
            <h3 className="text-red-700 font-semibold flex items-center gap-2" style={{ fontFamily: serif }}>
              <AlertTriangle className="h-4 w-4" /> Risk Alerts
            </h3>
          </div>
          <div className="p-4 space-y-3">
            {advisee.riskFlags.overloadRisk && (
              <div className="flex items-start gap-3 p-3 rounded bg-red-50 border border-red-200">
                <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-900">Overload Risk</p>
                  <p className="text-xs text-red-700">High credit load with multiple difficult courses</p>
                </div>
              </div>
            )}
            {advisee.riskFlags.missingPrereqs && (
              <div className="flex items-start gap-3 p-3 rounded bg-yellow-50 border border-yellow-200">
                <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-yellow-900">Missing Prerequisites</p>
                  <p className="text-xs text-yellow-700">May be missing required prerequisites for enrolled courses</p>
                </div>
              </div>
            )}
            {advisee.riskFlags.gpaDip && (
              <div className="flex items-start gap-3 p-3 rounded bg-orange-50 border border-orange-200">
                <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-orange-900">GPA Decline</p>
                  <p className="text-xs text-orange-700">GPA has decreased from the previous semester</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Degree Progress + Milestones */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Degree Progress */}
        <div className="border border-[#e8e4db] rounded bg-white">
          <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
            <h3 className="text-[#115740] font-semibold text-lg" style={{ fontFamily: serif }}>
              Degree Progress
            </h3>
          </div>
          <div className="p-6 space-y-5">
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold text-[#115740]" style={{ fontFamily: serif }}>
                  Overall Progress
                </span>
                <span className="text-sm text-gray-500">{creditsEarned} / 120</span>
              </div>
              <div className="relative h-3 w-full rounded-full overflow-hidden bg-[#ede5cf]" style={{ border: '1px solid #d4c9a8' }}>
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${graduationProgress}%`, background: 'linear-gradient(90deg, #B9975B, #d4b876)' }}
                />
              </div>
            </div>

            {declarationWindow && !advisee.declared && (
              <div className="flex items-start gap-2 p-3 rounded bg-[#115740]/5 border border-[#115740]/20">
                <GraduationCap className="h-5 w-5 text-[#115740] mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-[#115740]">Ready to Declare Major</p>
                  <p className="text-xs text-gray-600">Within declaration window (39-54 credits)</p>
                </div>
              </div>
            )}

            {/* Milestones */}
            {milestones.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[#e8e4db]">
                <p className="text-sm font-semibold text-[#115740]" style={{ fontFamily: serif }}>Milestones</p>
                {milestones.map((m) => (
                  <div key={m.id} className="flex items-start gap-2.5 py-1.5">
                    {m.completed ? (
                      <CheckCircle2 className="h-4 w-4 text-[#115740] mt-0.5 flex-shrink-0" />
                    ) : (
                      <Circle className="h-4 w-4 text-gray-300 mt-0.5 flex-shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${m.completed ? 'text-[#262626]' : 'text-gray-500'}`}>{m.title}</p>
                      {m.credits && (
                        <div className="mt-1">
                          <div className="relative h-1.5 w-full rounded-full overflow-hidden bg-[#ede5cf]">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.min((m.credits.current / m.credits.required) * 100, 100)}%`,
                                background: 'linear-gradient(90deg, #B9975B, #d4b876)',
                              }}
                            />
                          </div>
                          <p className="text-[10px] text-gray-400 mt-0.5">{m.credits.current} / {m.credits.required}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Current Courses */}
        <div className="border border-[#e8e4db] rounded bg-white">
          <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
            <div className="flex items-center justify-between">
              <h3 className="text-[#115740] font-semibold text-lg" style={{ fontFamily: serif }}>
                Current Courses
              </h3>
              <span className="text-xs text-gray-500">{currentCredits} credits</span>
            </div>
          </div>
          <div className="divide-y divide-[#e8e4db]">
            {loading ? (
              <div className="p-6 text-center text-sm text-gray-400">Loading courses...</div>
            ) : courses.current.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-400">No enrolled courses</div>
            ) : (
              courses.current.map((c, i) => (
                <div key={i} className="px-6 py-3 hover:bg-[#f7f5f0] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-3.5 w-3.5 text-[#B9975B]" />
                      <span className="text-sm font-medium text-[#262626]">{c.code}</span>
                    </div>
                    <span className="text-xs text-gray-500">{c.credits} credits</span>
                  </div>
                  <p className="text-xs text-gray-500 ml-5.5 mt-0.5 pl-[22px]">{c.title}</p>
                  {(c.meetingDays || c.meetingTime) && (
                    <div className="flex items-center gap-1 mt-1 pl-[22px]">
                      <Clock className="h-3 w-3 text-gray-400" />
                      <span className="text-[10px] text-gray-400">
                        {[c.meetingDays, c.meetingTime].filter(Boolean).join(' ')}
                        {c.building ? ` — ${c.building}${c.room ? ` ${c.room}` : ''}` : ''}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Completed Courses */}
      {courses.completed.length > 0 && (
        <div className="border border-[#e8e4db] rounded bg-white">
          <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
            <div className="flex items-center justify-between">
              <h3 className="text-[#115740] font-semibold text-lg" style={{ fontFamily: serif }}>
                Completed Courses
              </h3>
              <span className="text-xs text-gray-500">{courses.completed.length} courses &bull; {creditsEarned} credits</span>
            </div>
          </div>
          <div className="divide-y divide-[#e8e4db] max-h-[320px] overflow-y-auto">
            {courses.completed.map((c, i) => (
              <div key={i} className="px-6 py-3 hover:bg-[#f7f5f0] transition-colors flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <CheckCircle2 className="h-3.5 w-3.5 text-[#115740] flex-shrink-0" />
                  <span className="text-sm font-medium text-[#262626]">{c.code}</span>
                  <span className="text-xs text-gray-500 truncate">{c.title}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-xs text-gray-500">{c.credits} credits</span>
                  {c.grade && (
                    <span className="text-xs font-semibold text-[#115740] bg-[#f7f5f0] border border-[#e8e4db] px-2 py-0.5 rounded">
                      {c.grade}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
