'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import ProgressPanel from '@/components/student/ProgressPanel';
import CourseList from '@/components/student/CourseList';
import ChatInterface from '@/components/student/ChatInterface';
import ScheduleBuilder from '@/components/student/ScheduleBuilder';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Course } from '@/types';
import {
  getStudentProfile,
  getCourseProgress,
  getCourseCatalog,
} from '@/lib/api-client';
import {
  GraduationCap,
  Home,
  BookOpen,
  Calendar,
  MessageSquare,
  Menu,
  X,
  AlertCircle,
} from 'lucide-react';

export default function StudentDashboard() {
  const router = useRouter();

  const [activeTab, setActiveTab] =
    useState<'overview' | 'schedule' | 'chat'>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [student, setStudent] = useState<any>(null);
  const [currentCourses, setCurrentCourses] = useState<Course[]>([]);
  const [completedCourses, setCompletedCourses] = useState<Course[]>([]);
  const [milestones, setMilestones] = useState<any[]>([]);
  const [availableCourses, setAvailableCourses] = useState<Course[]>([]);

  const [loading, setLoading] = useState(true);
  const [isUsingBackend, setIsUsingBackend] = useState(false);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const [profile, progress, catalog] = await Promise.all([
          getStudentProfile(),
          getCourseProgress(),
          getCourseCatalog(),
        ]);

        setStudent(profile);
        setCurrentCourses(progress.currentCourses || []);
        setCompletedCourses(progress.completedCourses || []);
        setMilestones(progress.milestones || []);
        setAvailableCourses(catalog.courses || []);

        setIsUsingBackend(true);
      } catch (error) {
        console.error('Dashboard fetch failed:', error);
        setIsUsingBackend(false);
      } finally {
        setLoading(false);
      }
    }

    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-10 w-10 border-4 border-primary border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden"
              >
                {sidebarOpen ? <X /> : <Menu />}
              </button>

              <GraduationCap className="h-8 w-8 text-primary" />

              <div>
                <h1 className="text-xl font-bold">
                  W&M Business Advising
                </h1>
                <p className="text-sm text-muted-foreground">
                  {student?.name}
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <Link href="/">
                <Button variant="outline" size="sm">
                  <Home className="h-4 w-4 mr-2" />
                  Home
                </Button>
              </Link>

              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/login')}
              >
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        {/* Backend Status Banner */}
        {isUsingBackend ? (
          <div className="mb-4 p-3 rounded-lg bg-green-50 border border-green-200">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                Live Data
              </Badge>
              <span className="text-sm">
                Connected to backend services
              </span>
            </div>
          </div>
        ) : (
          <div className="mb-4 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              <span className="text-sm">
                Backend unavailable
              </span>
            </div>
          </div>
        )}

        <div className="flex flex-col md:flex-row gap-6">
          {/* Sidebar */}
          <aside
            className={`${sidebarOpen ? 'block' : 'hidden'
              } md:block md:w-64 space-y-2`}
          >
            <Button
              variant={activeTab === 'overview' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => setActiveTab('overview')}
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Overview
            </Button>

            <Button
              variant={activeTab === 'schedule' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => setActiveTab('schedule')}
            >
              <Calendar className="h-4 w-4 mr-2" />
              Schedule Builder
            </Button>

            <Button
              variant={activeTab === 'chat' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Ask Advisor
            </Button>
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-1">
                    {student && (
                      <ProgressPanel
                        student={student}
                        milestones={milestones}
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
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'schedule' && (
              <ScheduleBuilder
                availableCourses={availableCourses}
                currentCourses={currentCourses}
              />
            )}

            {activeTab === 'chat' && (
              <div className="h-[calc(100vh-200px)]">
                <ChatInterface />
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}