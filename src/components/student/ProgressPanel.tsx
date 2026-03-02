'use client';

import Badge from '@/components/ui/Badge';
import { Student, Milestone, Course } from '@/types';
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface ProgressPanelProps {
  student: Student;
  milestones: Milestone[];
  completedCourses?: Course[];
}

export default function ProgressPanel({ student, milestones, completedCourses = [] }: ProgressPanelProps) {
  const creditsEarned = completedCourses.length > 0
    ? completedCourses.reduce((sum, c) => sum + c.credits, 0)
    : student.creditsEarned;
  const graduationProgress = Math.min((creditsEarned / 120) * 100, 100);
  const declarationWindow = creditsEarned >= 39 && creditsEarned < 54;

  return (
    <div className="space-y-6">
      {/* Academic Progress */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3
            className="text-[#115740] font-semibold text-lg"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            Academic Progress
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Class of {student.classYear} &bull; {student.intendedMajor || 'Undeclared'}
          </p>
        </div>
        <div className="p-6 space-y-6">
          <div>
            <div className="flex justify-between mb-2">
              <span
                className="text-sm font-semibold text-[#115740]"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Credits Earned
              </span>
              <span className="text-sm text-gray-500">
                {creditsEarned} / 120
              </span>
            </div>
            <div className="relative h-3 w-full rounded-full overflow-hidden bg-[#ede5cf]" style={{ border: '1px solid #d4c9a8' }}>
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${graduationProgress}%`,
                  background: 'linear-gradient(90deg, #B9975B, #d4b876)',
                }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>GPA</p>
              <p className="text-2xl font-bold text-[#115740]">{student.gpa.toFixed(2)}</p>
            </div>
            <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-3">
              <p className="text-xs text-gray-500" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>AP Credits</p>
              <p className="text-2xl font-bold text-[#115740]">{student.apCredits}</p>
            </div>
          </div>

          {declarationWindow && !student.declared && (
            <div className="flex items-start gap-2 p-3 rounded bg-yellow-50 border border-yellow-200">
              <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-yellow-900">Declaration Window Open</p>
                <p className="text-sm text-yellow-700">
                  You can now declare your major. Must declare before earning 54 credits.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Milestones */}
      <div className="border border-[#e8e4db] rounded bg-white">
        <div className="px-6 py-5 border-b border-[#e8e4db] bg-[#f7f5f0]">
          <h3
            className="text-[#115740] font-semibold text-lg"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            Milestones
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">Track your progress toward graduation</p>
        </div>
        <div className="p-6">
          <div className="space-y-3">
            {milestones.map((milestone) => (
              <div
                key={milestone.id}
                className="flex items-start gap-3 p-3 rounded hover:bg-[#f7f5f0] transition-colors"
              >
                {milestone.completed ? (
                  <CheckCircle2 className="h-5 w-5 text-[#115740] mt-0.5 flex-shrink-0" />
                ) : (
                  <Circle className="h-5 w-5 text-gray-300 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-[#262626]">{milestone.title}</p>
                    {!milestone.completed && milestone.deadline ? (
                      <Badge variant="warning">
                        Due {new Date(milestone.deadline).toLocaleDateString()}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm text-gray-500">{milestone.description}</p>
                  {milestone.credits && (
                    <div className="mt-2">
                      <div className="relative h-2 w-full rounded-full overflow-hidden bg-[#ede5cf]">
                        <div
                          className="h-full rounded-full transition-all duration-500 ease-out"
                          style={{
                            width: `${Math.min((milestone.credits.current / milestone.credits.required) * 100, 100)}%`,
                            background: 'linear-gradient(90deg, #B9975B, #d4b876)',
                          }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {milestone.credits.current} / {milestone.credits.required} credits
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
