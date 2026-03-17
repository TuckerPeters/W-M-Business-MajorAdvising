'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useRequireAuth } from '@/lib/use-require-auth';
import { useAuth } from '@/lib/auth-context';
import ProgressPanel from '@/components/student/ProgressPanel';
import CourseList from '@/components/student/CourseList';
import ChatInterface from '@/components/student/ChatInterface';
import ScheduleBuilder from '@/components/student/ScheduleBuilder';
import DegreeProgress from '@/components/student/DegreeProgress';
import { Course } from '@/types';
import {
  getStudentProfile,
  getCourseProgress,
  getCourseCatalog,
  addPlannedCourse,
  deletePlannedCourse,
  getNextTermCode,
} from '@/lib/api-client';
import {
  BookOpen,
  Calendar,
  MessageSquare,
  LogOut,
  BarChart3,
} from 'lucide-react';

const isDemo = process.env.NEXT_PUBLIC_DEBUG === 'true';

const sidebarItems = [
  { key: 'overview' as const, label: 'Overview', icon: BookOpen },
  { key: 'degree' as const, label: 'Degree Progress', icon: BarChart3 },
  { key: 'schedule' as const, label: 'Schedule Builder', icon: Calendar },
  { key: 'chat' as const, label: 'AI Advisor', icon: MessageSquare },
];

const VALID_STUDENT_TABS = ['overview', 'degree', 'schedule', 'chat'] as const;
type StudentTab = typeof VALID_STUDENT_TABS[number];

function getInitialTab<T extends string>(validTabs: readonly T[], fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  const hash = window.location.hash.replace('#', '');
  return (validTabs as readonly string[]).includes(hash) ? (hash as T) : fallback;
}

export default function StudentDashboard() {
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useRequireAuth();
  const { signOut } = useAuth();

  const [activeTab, setActiveTab] =
    useState<StudentTab>(() => getInitialTab(VALID_STUDENT_TABS, 'overview'));

  // Sync tab to URL hash
  useEffect(() => {
    window.location.hash = activeTab;
  }, [activeTab]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);

  const [student, setStudent] = useState<any>(null);
  const [currentCourses, setCurrentCourses] = useState<Course[]>([]);
  const [completedCourses, setCompletedCourses] = useState<Course[]>([]);
  const [plannedCourses, setPlannedCourses] = useState<Course[]>([]);
  const [milestones, setMilestones] = useState<any[]>([]);
  const [availableCourses, setAvailableCourses] = useState<Course[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const [nextTerm, setNextTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;

    async function fetchDashboard() {
      try {
        const [profile, progress, termCode] = await Promise.all([
          getStudentProfile(),
          getCourseProgress(),
          getNextTermCode(),
        ]);

        setStudent(profile);
        setCurrentCourses(progress.currentCourses || []);
        setCompletedCourses(progress.completedCourses || []);
        setPlannedCourses(progress.plannedCourses || []);
        setMilestones(progress.milestones || []);
        setNextTerm(termCode);

      } catch (error) {
        console.error('Dashboard fetch failed:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchDashboard();
  }, [isAuthenticated]);

  const handleCourseAdded = useCallback(async (course: Course) => {
    const saved = await addPlannedCourse({
      courseCode: course.code,
      courseName: course.title,
      term: nextTerm,
      credits: course.credits,
      sectionNumber: course.sectionNumber,
      crn: course.crn,
      instructor: course.instructor,
      meetingDays: course.meetingDays,
      meetingTime: course.meetingTime,
      building: course.building,
      room: course.room,
    });
    setPlannedCourses(prev => [...prev, saved]);
    return saved;
  }, [nextTerm]);

  const handleCourseRemoved = useCallback(async (course: Course) => {
    if (!course.enrollmentId) return false;
    await deletePlannedCourse(course.enrollmentId);
    setPlannedCourses(prev => prev.filter(c => c.enrollmentId !== course.enrollmentId));
    return true;
  }, []);

  // Lazy-load course catalog only when Schedule Builder tab is opened
  useEffect(() => {
    if (activeTab === 'schedule' && !catalogLoaded && nextTerm) {
      getCourseCatalog(nextTerm).then((catalog) => {
        setAvailableCourses(catalog.courses || []);
        setCatalogLoaded(true);
      }).catch((err) => console.error('Catalog fetch failed:', err));
    }
  }, [activeTab, catalogLoaded, nextTerm]);

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <div className="animate-spin h-10 w-10 border-4 border-[#115740] border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-white">
      {/* Green accent bar */}
      <div className="h-1.5 bg-[#115740]" />

      {/* Demo banner */}
      {isDemo && (
        <div className="bg-[#B9975B]/15 border-b border-[#B9975B]/30 px-6 py-2">
          <div className="max-w-7xl mx-auto flex items-center justify-center gap-2 text-xs text-[#8a7040]">
            <span className="font-semibold">Demo Mode</span>
            <span className="text-[#8a7040]/60">|</span>
            <span>Viewing as demo student &mdash; Sarah Chen</span>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-[72px]">
          <div className="flex items-center gap-3">
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

            {student && (
              <span className="hidden sm:inline text-sm text-gray-500 border-l border-gray-300 pl-3 ml-1">
                {student.name}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1">
            <Link
              href="/"
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
            >
              Home
            </Link>
            <button
              onClick={async () => { if (!isDemo) await signOut(); router.push('/'); }}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-[#115740] hover:bg-[#115740]/5 rounded transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">{isDemo ? 'Home' : 'Logout'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="max-w-7xl mx-auto px-6 pt-6 pb-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-400">
          <Link href="/" className="hover:text-[#115740]">Home</Link>
          <span>/</span>
          <span className="text-gray-600">Student Dashboard</span>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4 mb-6">
        <div className="border-b border-gray-200 flex overflow-x-auto scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0">
          {sidebarItems.map((item) => (
            <button
              key={item.key}
              onClick={() => setActiveTab(item.key)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-5 py-3 text-xs sm:text-sm font-medium border-b-2 transition-colors -mb-px whitespace-nowrap ${
                activeTab === item.key
                  ? 'border-[#115740] text-[#115740]'
                  : 'border-transparent text-gray-500 hover:text-[#115740] hover:border-gray-300'
              }`}
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              <item.icon className="h-4 w-4 flex-shrink-0" />
              <span className="hidden sm:inline">{item.label}</span>
              <span className="sm:hidden">{item.label.split(' ')[0]}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main layout */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pb-16">
        <main>
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-2"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Academic Overview
              </h2>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                  {student && (
                    <ProgressPanel
                      student={student}
                      milestones={milestones}
                      completedCourses={completedCourses}
                    />
                  )}
                </div>

                <div className="lg:col-span-2 space-y-6">
                  <CourseList
                    title="Current Courses"
                    description="Active Semester"
                    courses={currentCourses}
                  />

                  <CourseList
                    title="Completed Courses"
                    description="Academic History"
                    courses={completedCourses}
                    showGrades
                    compact
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'degree' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Degree Progress
              </h2>
              <DegreeProgress
                completedCourses={completedCourses}
                currentCourses={currentCourses}
                plannedCourses={plannedCourses}
                studentMajor={student?.intendedMajor}
                creditsEarned={student?.creditsEarned || 0}
                apCredits={student?.apCredits || 0}
              />
            </>
          )}

          {activeTab === 'schedule' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                Schedule Builder
              </h2>
              <ScheduleBuilder
                availableCourses={availableCourses}
                plannedCourses={plannedCourses}
                completedCourses={completedCourses}
                currentCourses={currentCourses}
                studentMajor={student?.intendedMajor}
                creditsEarned={student?.creditsEarned || 0}
                classYear={student?.classYear || 2027}
                onCourseAdded={handleCourseAdded}
                onCourseRemoved={handleCourseRemoved}
              />
            </>
          )}

          {activeTab === 'chat' && (
            <>
              <h2
                className="text-[#115740] text-2xl sm:text-3xl mb-6"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                AI Academic Advisor
              </h2>
              <div className="h-[calc(100vh-280px)]">
                <ChatInterface
                  activeConversationId={activeConversationId}
                  onConversationChange={setActiveConversationId}
                />
              </div>
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
