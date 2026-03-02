'use client';
//TODO: introduce AP Credits Scraping 
// Determine completed courses via PDF parsing / Also determine potential majors via PDF
// Cleaner less harcoded slop

import { useState, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Search, Plus, Trash2, Check } from 'lucide-react';
import Input from '@/components/ui/Input';
import { searchCourses } from '@/lib/api-client';

interface StudentOnboardingProps {
  studentName: string;
  studentEmail: string;
  onClose: () => void;
  onComplete: () => void;
}

interface CourseEntry {
  code: string;
  title: string;
  credits: number;
  grade?: string;
  manual?: boolean;
}

const STEPS = ['Major', 'AP Credits', 'Past Courses', 'Current Courses'] as const;

const MAJORS = [
  'Undeclared',
  'Accounting',
  'Business Analytics - Data Science',
  'Business Analytics - Supply Chain',
  'Finance',
  'Marketing',
];

const GRADES_AP = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'P', 'W'];
const GRADES_IB = ['7', '6', '5', '4', '3', '2', '1'];

const AP_EXAMS = [
  { name: 'AP Microeconomics', credits: 3 },
  { name: 'AP Macroeconomics', credits: 3 },
  { name: 'AP Statistics', credits: 3 },
  { name: 'AP Calculus AB', credits: 4 },
  { name: 'AP Calculus BC', credits: 4 },
  { name: 'AP English Language', credits: 3 },
  { name: 'AP English Literature', credits: 3 },
  { name: 'AP Psychology', credits: 3 },
  { name: 'AP U.S. History', credits: 3 },
  { name: 'AP Computer Science A', credits: 3 },
];

const serif = 'Georgia, "Times New Roman", serif';

export default function StudentOnboarding({
  studentName,
  studentEmail,
  onClose,
  onComplete,
}: StudentOnboardingProps) {
  const [step, setStep] = useState(0);

  // Step 1: Major & Minor
  const [major, setMajor] = useState('Undeclared');
  const [minor, setMinor] = useState('');

  // Step 2: AP Credits
  const [selectedAPs, setSelectedAPs] = useState<Set<string>>(new Set());
  const [additionalApCredits, setAdditionalApCredits] = useState(0);

  // Step 3: Past Courses
  const [completedCourses, setCompletedCourses] = useState<CourseEntry[]>([]);
  const [pastSearchQuery, setPastSearchQuery] = useState('');
  const [pastSearchResults, setPastSearchResults] = useState<{ code: string; title: string; credits: number }[]>([]);
  const [pastSearching, setPastSearching] = useState(false);
  const [showManualPast, setShowManualPast] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const [manualTitle, setManualTitle] = useState('');
  const [manualCredits, setManualCredits] = useState('3');
  const [manualGrade, setManualGrade] = useState('A');

  // Step 4: Current Courses
  const [enrolledCourses, setEnrolledCourses] = useState<CourseEntry[]>([]);
  const [currentSearchQuery, setCurrentSearchQuery] = useState('');
  const [currentSearchResults, setCurrentSearchResults] = useState<{ code: string; title: string; credits: number }[]>([]);
  const [currentSearching, setCurrentSearching] = useState(false);

  const [submitting, setSubmitting] = useState(false);

  const totalApCredits = AP_EXAMS.filter((ap) => selectedAPs.has(ap.name)).reduce((sum, ap) => sum + ap.credits, 0) + additionalApCredits;

  // Debounced search
  const handleSearch = useCallback(
    async (query: string, target: 'past' | 'current') => {
      const setResults = target === 'past' ? setPastSearchResults : setCurrentSearchResults;
      const setSearching = target === 'past' ? setPastSearching : setCurrentSearching;

      if (query.length < 2) {
        setResults([]);
        return;
      }
      setSearching(true);
      try {
        const results = await searchCourses(query);
        setResults(results.map((c: any) => ({ code: c.code, title: c.title, credits: c.credits })));
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    },
    []
  );

  const addCompletedCourse = (course: { code: string; title: string; credits: number }) => {
    if (completedCourses.some((c) => c.code === course.code)) return;
    setCompletedCourses((prev) => [...prev, { ...course, grade: 'A' }]);
    setPastSearchQuery('');
    setPastSearchResults([]);
  };

  const addManualCourse = () => {
    if (!manualCode.trim()) return;
    setCompletedCourses((prev) => [
      ...prev,
      {
        code: manualCode.trim().toUpperCase(),
        title: manualTitle.trim() || manualCode.trim().toUpperCase(),
        credits: parseInt(manualCredits) || 3,
        grade: manualGrade,
        manual: true,
      },
    ]);
    setManualCode('');
    setManualTitle('');
    setManualCredits('3');
    setManualGrade('A');
    setShowManualPast(false);
  };

  const addEnrolledCourse = (course: { code: string; title: string; credits: number }) => {
    if (enrolledCourses.some((c) => c.code === course.code)) return;
    setEnrolledCourses((prev) => [...prev, { ...course }]);
    setCurrentSearchQuery('');
    setCurrentSearchResults([]);
  };

  const handleComplete = async () => {
    setSubmitting(true);
    // In demo mode we just redirect — backend profile already exists as demo-student
    // In production, this would POST the onboarding data
    onComplete();
  };

  const canProceed = () => {
    if (step === 0) return true; // Major can be undeclared
    if (step === 1) return true; // AP credits can be 0
    if (step === 2) return true; // Past courses can be empty (freshman)
    if (step === 3) return true; // Current courses can be empty
    return true;
  };

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/50 z-[60] transition-opacity" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 pointer-events-none">
        <div
          className="relative bg-white w-full max-w-[540px] max-h-[90vh] shadow-2xl pointer-events-auto border-t-4 border-[#B9975B] flex flex-col"
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
          <div className="px-8 pt-6 pb-4 flex-shrink-0">
            <h2
              className="text-[#115740] text-xl mb-1"
              style={{ fontFamily: serif }}
            >
              Welcome, {studentName || 'Student'}
            </h2>
            <p className="text-sm text-gray-500">
              Let&apos;s set up your academic profile. This helps us provide personalized advising.
            </p>
          </div>

          {/* Step indicator */}
          <div className="px-8 pb-4 flex-shrink-0">
            <div className="flex items-center gap-1">
              {STEPS.map((label, i) => (
                <div key={label} className="flex items-center flex-1">
                  <div className="flex items-center gap-1.5 flex-1">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                        i < step
                          ? 'bg-[#115740] text-white'
                          : i === step
                          ? 'bg-[#B9975B] text-white'
                          : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
                    </div>
                    <span
                      className={`text-xs hidden sm:block ${
                        i === step ? 'text-[#115740] font-semibold' : 'text-gray-400'
                      }`}
                    >
                      {label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={`h-px flex-1 mx-1 ${
                        i < step ? 'bg-[#115740]' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Content area — scrollable */}
          <div className="flex-1 overflow-y-auto px-8 pb-2 min-h-0">
            {/* Step 1: Major & Minor */}
            {step === 0 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1.5" style={{ fontFamily: serif }}>
                    Intended Major
                  </label>
                  <select
                    value={major}
                    onChange={(e) => setMajor(e.target.value)}
                    className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                  >
                    {MAJORS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">
                    Business majors declare after completing 39+ credits with required courses.
                  </p>
                </div>

                <div>
                  <label className="block text-sm text-gray-600 mb-1.5" style={{ fontFamily: serif }}>
                    Minor <span className="text-gray-400">(optional)</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="e.g. Computer Science, Psychology"
                    value={minor}
                    onChange={(e) => setMinor(e.target.value)}
                    className="border-gray-300 focus-visible:ring-[#115740]"
                  />
                </div>

                <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2" style={{ fontFamily: serif }}>
                    Class Year
                  </p>
                  <select
                    className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                    defaultValue="2027"
                  >
                    <option value="2025">2025 (Senior)</option>
                    <option value="2026">2026 (Junior)</option>
                    <option value="2027">2027 (Sophomore)</option>
                    <option value="2028">2028 (Freshman)</option>
                    <option value="2029">2029 (Incoming)</option>
                  </select>
                </div>
              </div>
            )}

            {/* Step 2: AP Credits */}
            {step === 1 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Select any AP exams you received credit for. These count toward your total credits earned.
                </p>

                <div className="space-y-1.5">
                  {AP_EXAMS.map((ap) => (
                    <label
                      key={ap.name}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded border cursor-pointer transition-colors ${
                        selectedAPs.has(ap.name)
                          ? 'border-[#115740] bg-[#115740]/5'
                          : 'border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedAPs.has(ap.name)}
                        onChange={() => {
                          setSelectedAPs((prev) => {
                            const next = new Set(prev);
                            if (next.has(ap.name)) next.delete(ap.name);
                            else next.add(ap.name);
                            return next;
                          });
                        }}
                        className="h-4 w-4 rounded border-gray-300 text-[#115740] focus:ring-[#115740]"
                      />
                      <span className="text-sm text-gray-700 flex-1">{ap.name}</span>
                      <span className="text-xs text-gray-400">{ap.credits} cr</span>
                    </label>
                  ))}
                </div>

                <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4">
                  <label className="block text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2" style={{ fontFamily: serif }}>
                    Additional AP/Transfer Credits
                  </label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="0"
                    value={additionalApCredits || ''}
                    onChange={(e) => setAdditionalApCredits(parseInt(e.target.value) || 0)}
                    className="border-gray-300 focus-visible:ring-[#115740] w-24"
                  />
                  <p className="text-xs text-gray-400 mt-1.5">
                    For AP exams or transfer credits not listed above.
                  </p>
                </div>

                <div className="flex items-center justify-between py-2 px-3 bg-[#115740]/5 rounded border border-[#115740]/10">
                  <span className="text-sm font-medium text-[#115740]">Total AP/Transfer Credits</span>
                  <span className="text-lg font-bold text-[#115740]">{totalApCredits}</span>
                </div>
              </div>
            )}

            {/* Step 3: Past Courses & Grades */}
            {step === 2 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Add courses you&apos;ve already completed. Search the catalog or add manually.
                </p>

                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search courses (e.g. BUAD 201, Accounting)"
                    value={pastSearchQuery}
                    onChange={(e) => {
                      setPastSearchQuery(e.target.value);
                      handleSearch(e.target.value, 'past');
                    }}
                    className="w-full h-10 pl-10 pr-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
                  />
                  {pastSearching && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">Searching...</div>
                  )}
                </div>

                {/* Search results dropdown */}
                {pastSearchResults.length > 0 && (
                  <div className="border border-gray-200 rounded max-h-40 overflow-y-auto divide-y divide-gray-100">
                    {pastSearchResults.map((course) => (
                      <button
                        key={course.code}
                        onClick={() => addCompletedCourse(course)}
                        className="w-full text-left px-3 py-2 hover:bg-[#f7f5f0] transition-colors flex items-center justify-between"
                        disabled={completedCourses.some((c) => c.code === course.code)}
                      >
                        <div>
                          <span className="text-sm font-medium text-[#115740]">{course.code}</span>
                          <span className="text-sm text-gray-500 ml-2">{course.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">{course.credits} cr</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Manual add toggle */}
                <button
                  onClick={() => setShowManualPast(!showManualPast)}
                  className="flex items-center gap-1.5 text-sm text-[#115740] hover:underline"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add course manually
                </button>

                {showManualPast && (
                  <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Course Code</label>
                        <Input
                          placeholder="e.g. BUAD 201"
                          value={manualCode}
                          onChange={(e) => setManualCode(e.target.value)}
                          className="border-gray-300 focus-visible:ring-[#115740]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Title (optional)</label>
                        <Input
                          placeholder="e.g. Intro to Accounting"
                          value={manualTitle}
                          onChange={(e) => setManualTitle(e.target.value)}
                          className="border-gray-300 focus-visible:ring-[#115740]"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Credits</label>
                        <Input
                          type="number"
                          min="1"
                          max="6"
                          value={manualCredits}
                          onChange={(e) => setManualCredits(e.target.value)}
                          className="border-gray-300 focus-visible:ring-[#115740]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Grade</label>
                        <select
                          value={manualGrade}
                          onChange={(e) => setManualGrade(e.target.value)}
                          className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                        >
                          {GRADES_AP.map((g) => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <button
                      onClick={addManualCourse}
                      disabled={!manualCode.trim()}
                      className="px-4 py-2 text-sm font-medium bg-[#115740] text-white rounded hover:bg-[#0d4632] transition-colors disabled:opacity-50"
                    >
                      Add Course
                    </button>
                  </div>
                )}

                {/* Added courses list */}
                {completedCourses.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold" style={{ fontFamily: serif }}>
                      Completed Courses ({completedCourses.length})
                    </p>
                    {completedCourses.map((course, idx) => (
                      <div
                        key={`${course.code}-${idx}`}
                        className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded bg-white"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-[#262626]">{course.code}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.credits} cr</span>
                        </div>
                        <select
                          value={course.grade || 'A'}
                          onChange={(e) => {
                            setCompletedCourses((prev) =>
                              prev.map((c, i) => (i === idx ? { ...c, grade: e.target.value } : c))
                            );
                          }}
                          className="h-8 px-2 rounded border border-gray-200 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-[#115740]"
                        >
                          {GRADES_AP.map((g) => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => setCompletedCourses((prev) => prev.filter((_, i) => i !== idx))}
                          className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Step 4: Currently Enrolled */}
            {step === 3 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Add courses you&apos;re currently enrolled in this semester.
                </p>

                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search courses (e.g. BUAD 301, Finance)"
                    value={currentSearchQuery}
                    onChange={(e) => {
                      setCurrentSearchQuery(e.target.value);
                      handleSearch(e.target.value, 'current');
                    }}
                    className="w-full h-10 pl-10 pr-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
                  />
                  {currentSearching && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">Searching...</div>
                  )}
                </div>

                {/* Search results */}
                {currentSearchResults.length > 0 && (
                  <div className="border border-gray-200 rounded max-h-40 overflow-y-auto divide-y divide-gray-100">
                    {currentSearchResults.map((course) => (
                      <button
                        key={course.code}
                        onClick={() => addEnrolledCourse(course)}
                        className="w-full text-left px-3 py-2 hover:bg-[#f7f5f0] transition-colors flex items-center justify-between"
                        disabled={enrolledCourses.some((c) => c.code === course.code)}
                      >
                        <div>
                          <span className="text-sm font-medium text-[#115740]">{course.code}</span>
                          <span className="text-sm text-gray-500 ml-2">{course.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">{course.credits} cr</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Enrolled courses list */}
                {enrolledCourses.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold" style={{ fontFamily: serif }}>
                      Currently Enrolled ({enrolledCourses.length})
                    </p>
                    {enrolledCourses.map((course, idx) => (
                      <div
                        key={`${course.code}-${idx}`}
                        className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded bg-white"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-[#262626]">{course.code}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.title}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.credits} cr</span>
                        </div>
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[#115740] text-white">
                          Enrolled
                        </span>
                        <button
                          onClick={() => setEnrolledCourses((prev) => prev.filter((_, i) => i !== idx))}
                          className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {enrolledCourses.length === 0 && (
                  <div className="text-center py-6 text-sm text-gray-400">
                    Search and add your current courses above, or skip this step.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer navigation */}
          <div className="px-8 py-4 border-t border-gray-200 flex items-center justify-between flex-shrink-0">
            {step > 0 ? (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
                Back
              </button>
            ) : (
              <button
                onClick={onClose}
                className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                Skip for now
              </button>
            )}

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                disabled={!canProceed()}
                className="flex items-center gap-1.5 px-5 py-2 bg-[#115740] text-white text-sm font-medium rounded hover:bg-[#0d4632] transition-colors disabled:opacity-50"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={submitting}
                className="flex items-center gap-1.5 px-5 py-2 bg-[#B9975B] text-white text-sm font-medium rounded hover:bg-[#a88649] transition-colors disabled:opacity-50"
              >
                {submitting ? 'Setting up...' : 'Complete Setup'}
                {!submitting && <Check className="h-4 w-4" />}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
