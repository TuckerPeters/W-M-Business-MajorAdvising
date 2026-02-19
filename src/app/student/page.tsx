'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import ProgressPanel from '@/components/student/ProgressPanel';
import CourseList from '@/components/student/CourseList';
import ChatInterface from '@/components/student/ChatInterface';
import ScheduleBuilder from '@/components/student/ScheduleBuilder';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Course } from '@/types';
import {
  mockStudent,
  mockCompletedCourses,
  mockCurrentCourses,
  mockAvailableCourses,
  mockMilestones,
  mockChatMessages,
} from '@/data/mockData';
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
  const [activeTab, setActiveTab] = useState<'overview' | 'schedule' | 'chat'>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [availableCourses, setAvailableCourses] = useState<Course[]>(mockAvailableCourses);
  const [loading, setLoading] = useState(true);
  const [isUsingBackend, setIsUsingBackend] = useState(false);

  // Fetch available courses from backend on mount
  useEffect(() => {
    async function fetchCourses() {
      try {
        const response = await fetch('/api/courses?limit=200');
        const data = await response.json();

        if (data.courses && data.courses.length > 0) {
          setAvailableCourses(data.courses);
          setIsUsingBackend(data.isFromBackend || false);
        }
      } catch (error) {
        console.error('Error fetching courses:', error);
        // Keep using mock data on error
      } finally {
        setLoading(false);
      }
    }

    fetchCourses();
  }, []);

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
                <h1 className="text-xl font-bold">W&M Business Advising</h1>
                <p className="text-sm text-muted-foreground">{mockStudent.name}</p>
              </div>
            </div>
            <Link href="/">
              <Button variant="outline" size="sm">
                <Home className="h-4 w-4 mr-2" />
                Home
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        {/* Backend Status Banner */}
        {!loading && isUsingBackend && (
          <div className="mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-green-100 text-green-800">Live Data</Badge>
              <span className="text-sm text-green-800 dark:text-green-200">
                Connected to course catalog backend
              </span>
            </div>
          </div>
        )}
        {!loading && !isUsingBackend && (
          <div className="mb-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-yellow-600" />
              <span className="text-sm text-yellow-800 dark:text-yellow-200">
                Using demo data - backend unavailable
              </span>
            </div>
          </div>
        )}

        <div className="flex flex-col md:flex-row gap-6">
          {/* Sidebar Navigation */}
          <aside
            className={`${
              sidebarOpen ? 'block' : 'hidden'
            } md:block md:w-64 space-y-2`}
          >
            <Button
              variant={activeTab === 'overview' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => {
                setActiveTab('overview');
                setSidebarOpen(false);
              }}
            >
              <BookOpen className="h-4 w-4 mr-2" />
              Overview
            </Button>
            <Button
              variant={activeTab === 'schedule' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => {
                setActiveTab('schedule');
                setSidebarOpen(false);
              }}
            >
              <Calendar className="h-4 w-4 mr-2" />
              Schedule Builder
            </Button>
            <Button
              variant={activeTab === 'chat' ? 'default' : 'ghost'}
              className="w-full justify-start"
              onClick={() => {
                setActiveTab('chat');
                setSidebarOpen(false);
              }}
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
                    <ProgressPanel student={mockStudent} milestones={mockMilestones} />
                  </div>
                  <div className="lg:col-span-2 space-y-6">
                    <CourseList
                      title="Current Courses"
                      description="Fall 2024"
                      courses={mockCurrentCourses}
                    />
                    <CourseList
                      title="Completed Courses"
                      description="Your academic history"
                      courses={mockCompletedCourses}
                      showGrades
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'schedule' && (
              loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center space-y-3">
                    <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div>
                    <p className="text-sm text-muted-foreground">Loading courses...</p>
                  </div>
                </div>
              ) : (
                <ScheduleBuilder
                  availableCourses={availableCourses}
                  currentCourses={mockCurrentCourses}
                />
              )
            )}

            {activeTab === 'chat' && (
              <div className="h-[calc(100vh-200px)]">
                <ChatInterface initialMessages={mockChatMessages} />
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
