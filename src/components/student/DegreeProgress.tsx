'use client';

import { useState, useEffect } from 'react';
import { Course } from '@/types';
import { getDegreeRequirements } from '@/lib/api-client';
import { CheckCircle2, Circle, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react';

interface DegreeReqCourse {
  code: string;
  title: string;
  credits: number;
}

interface CourseGroup {
  name: string;
  courses: DegreeReqCourse[];
}

interface Major {
  name: string;
  credits_required: number;
  required_courses: DegreeReqCourse[];
  elective_courses: DegreeReqCourse[];
  electives_required: number;
}

interface DegreeRequirements {
  prerequisites: CourseGroup;
  core_curriculum: CourseGroup[];
  majors: Major[];
  total_credits_required: number;
}

interface Props {
  completedCourses: Course[];
  currentCourses: Course[];
  plannedCourses: Course[];
  studentMajor?: string;
  creditsEarned: number;
  apCredits: number;
}

function normalizeCode(code: string) {
  return code.replace(/\s+/g, ' ').trim().toUpperCase();
}

function RequirementRow({ course, completed, inProgress, planned }: {
  course: DegreeReqCourse;
  completed: boolean;
  inProgress: boolean;
  planned: boolean;
}) {
  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded hover:bg-gray-50">
      {completed ? (
        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
      ) : inProgress ? (
        <div className="h-4 w-4 rounded-full border-2 border-[#B9975B] bg-[#B9975B]/20 flex-shrink-0" />
      ) : planned ? (
        <div className="h-4 w-4 rounded-full border-2 border-blue-400 bg-blue-50 flex-shrink-0" />
      ) : (
        <Circle className="h-4 w-4 text-gray-300 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <span className={`text-sm font-medium ${completed ? 'text-green-700' : inProgress ? 'text-[#B9975B]' : planned ? 'text-blue-600' : 'text-gray-700'}`}>
          {course.code}
        </span>
        <span className="text-sm text-gray-500 ml-2">{course.title}</span>
      </div>
      <span className="text-xs text-gray-400 flex-shrink-0">{course.credits}cr</span>
    </div>
  );
}

function RequirementSection({ title, courses, completedCodes, currentCodes, plannedCodes, defaultOpen = false }: {
  title: string;
  courses: DegreeReqCourse[];
  completedCodes: Set<string>;
  currentCodes: Set<string>;
  plannedCodes: Set<string>;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const done = courses.filter(c => completedCodes.has(normalizeCode(c.code))).length;
  const inProg = courses.filter(c => currentCodes.has(normalizeCode(c.code))).length;
  const total = courses.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-[#f7f5f0] hover:bg-[#eeebe4] transition-colors"
      >
        <div className="flex items-center gap-3">
          {open ? <ChevronDown className="h-4 w-4 text-gray-500" /> : <ChevronRight className="h-4 w-4 text-gray-500" />}
          <span className="font-medium text-[#115740] text-sm" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
            {title}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">{done}/{total} complete</span>
          <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#115740] rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </button>
      {open && (
        <div className="divide-y divide-gray-100">
          {courses.map(c => (
            <RequirementRow
              key={c.code}
              course={c}
              completed={completedCodes.has(normalizeCode(c.code))}
              inProgress={currentCodes.has(normalizeCode(c.code))}
              planned={plannedCodes.has(normalizeCode(c.code))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DegreeProgress({ completedCourses, currentCourses, plannedCourses, studentMajor, creditsEarned, apCredits }: Props) {
  const [reqs, setReqs] = useState<DegreeRequirements | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDegreeRequirements()
      .then(setReqs)
      .catch(err => console.error('Failed to load degree requirements:', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin h-8 w-8 border-4 border-[#115740] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!reqs) {
    return <p className="text-gray-500 py-8 text-center">Could not load degree requirements.</p>;
  }

  const completedCodes = new Set(completedCourses.map(c => normalizeCode(c.code)));
  const currentCodes = new Set(currentCourses.map(c => normalizeCode(c.code)));
  const plannedCodes = new Set(plannedCourses.map(c => normalizeCode(c.code)));

  // Credit calculations
  const totalCredits = reqs.total_credits_required;
  const currentCredits = currentCourses.reduce((s, c) => s + c.credits, 0);
  const plannedCredits = plannedCourses.reduce((s, c) => s + c.credits, 0);
  const projectedTotal = creditsEarned + currentCredits + plannedCredits;
  const remaining = Math.max(0, totalCredits - projectedTotal);

  // Count all requirement completions
  const prereqCourses = reqs.prerequisites?.courses || [];
  const prereqDone = prereqCourses.filter(c => completedCodes.has(normalizeCode(c.code))).length;

  const allCoreCourses = reqs.core_curriculum.flatMap(g => g.courses);
  const coreDone = allCoreCourses.filter(c => completedCodes.has(normalizeCode(c.code))).length;

  // Find selected major
  const selectedMajor = reqs.majors.find(m =>
    studentMajor && m.name.toLowerCase().includes(studentMajor.toLowerCase())
  );
  const majorReqCourses = selectedMajor?.required_courses || [];
  const majorDone = majorReqCourses.filter(c => completedCodes.has(normalizeCode(c.code))).length;

  // Semesters remaining estimate (15 credits/semester)
  const semestersRemaining = remaining > 0 ? Math.ceil(remaining / 15) : 0;

  return (
    <div className="space-y-6">
      {/* Credit Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Credits Earned</p>
          <p className="text-2xl font-bold text-[#115740]">{creditsEarned}</p>
          {apCredits > 0 && <p className="text-xs text-gray-400 mt-0.5">includes {apCredits} AP</p>}
        </div>
        <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">In Progress</p>
          <p className="text-2xl font-bold text-[#B9975B]">{currentCredits}</p>
          <p className="text-xs text-gray-400 mt-0.5">{currentCourses.length} courses</p>
        </div>
        <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Planned</p>
          <p className="text-2xl font-bold text-blue-600">{plannedCredits}</p>
          <p className="text-xs text-gray-400 mt-0.5">{plannedCourses.length} courses</p>
        </div>
        <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded-lg p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Remaining</p>
          <p className="text-2xl font-bold text-red-600">{remaining}</p>
          <p className="text-xs text-gray-400 mt-0.5">~{semestersRemaining} semester{semestersRemaining !== 1 ? 's' : ''}</p>
        </div>
      </div>

      {/* Overall progress bar */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-[#115740]" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
            Overall Degree Progress
          </span>
          <span className="text-sm text-gray-500">{projectedTotal} / {totalCredits} credits</span>
        </div>
        <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden flex">
          <div className="h-full bg-[#115740]" style={{ width: `${Math.min(100, (creditsEarned / totalCredits) * 100)}%` }} />
          <div className="h-full bg-[#B9975B]" style={{ width: `${Math.min(100 - (creditsEarned / totalCredits) * 100, (currentCredits / totalCredits) * 100)}%` }} />
          <div className="h-full bg-blue-400" style={{ width: `${Math.min(100 - ((creditsEarned + currentCredits) / totalCredits) * 100, (plannedCredits / totalCredits) * 100)}%` }} />
        </div>
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#115740] inline-block" /> Completed</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#B9975B] inline-block" /> In Progress</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-400 inline-block" /> Planned</span>
        </div>
      </div>

      {/* Alerts */}
      {remaining > 0 && remaining <= 30 && (
        <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">Approaching Graduation</p>
            <p className="text-sm text-amber-700">You need {remaining} more credits ({semestersRemaining} semester{semestersRemaining !== 1 ? 's' : ''}). Plan your remaining courses carefully.</p>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center p-3 border border-gray-200 rounded-lg">
          <p className="text-lg font-bold text-[#115740]">{prereqDone}/{prereqCourses.length}</p>
          <p className="text-xs text-gray-500">Pre-Major Prereqs</p>
        </div>
        <div className="text-center p-3 border border-gray-200 rounded-lg">
          <p className="text-lg font-bold text-[#115740]">{coreDone}/{allCoreCourses.length}</p>
          <p className="text-xs text-gray-500">Business Core</p>
        </div>
        <div className="text-center p-3 border border-gray-200 rounded-lg">
          <p className="text-lg font-bold text-[#115740]">{majorDone}/{majorReqCourses.length}</p>
          <p className="text-xs text-gray-500">{selectedMajor?.name || 'Major'} Courses</p>
        </div>
      </div>

      {/* Detailed Requirements */}
      <div className="space-y-3">
        <h3 className="text-[#115740] font-semibold text-lg" style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}>
          Degree Requirements Checklist
        </h3>

        <RequirementSection
          title="Pre-Major Prerequisites"
          courses={prereqCourses}
          completedCodes={completedCodes}
          currentCodes={currentCodes}
          plannedCodes={plannedCodes}
          defaultOpen
        />

        {reqs.core_curriculum.map(group => (
          <RequirementSection
            key={group.name}
            title={group.name}
            courses={group.courses}
            completedCodes={completedCodes}
            currentCodes={currentCodes}
            plannedCodes={plannedCodes}
          />
        ))}

        {selectedMajor && (
          <>
            <RequirementSection
              title={`${selectedMajor.name} — Required Courses`}
              courses={selectedMajor.required_courses}
              completedCodes={completedCodes}
              currentCodes={currentCodes}
              plannedCodes={plannedCodes}
              defaultOpen
            />
            {selectedMajor.elective_courses.length > 0 && (
              <RequirementSection
                title={`${selectedMajor.name} — Electives (pick ${selectedMajor.electives_required})`}
                courses={selectedMajor.elective_courses}
                completedCodes={completedCodes}
                currentCodes={currentCodes}
                plannedCodes={plannedCodes}
              />
            )}
          </>
        )}

        {!selectedMajor && reqs.majors.map(major => (
          <RequirementSection
            key={major.name}
            title={`${major.name} Major`}
            courses={[...major.required_courses, ...major.elective_courses]}
            completedCodes={completedCodes}
            currentCodes={currentCodes}
            plannedCodes={plannedCodes}
          />
        ))}
      </div>
    </div>
  );
}
