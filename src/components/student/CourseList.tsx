'use client';

import Badge from '@/components/ui/Badge';
import { Course } from '@/types';
import { BookOpen, Beaker, AlertTriangle, Clock, MapPin } from 'lucide-react';

function formatTerm(term?: string): string {
  if (!term) return '';
  const year = term.slice(0, 4);
  const code = term.slice(4);
  const season = code === '01' ? 'Spring' : code === '02' ? 'Spring' : code === '09' ? 'Fall' : code === '06' ? 'Summer' : '';
  return season ? `${season} ${year}` : term;
}

interface CourseListProps {
  title: string;
  description: string;
  courses: Course[];
  showGrades?: boolean;
  compact?: boolean;
}

export default function CourseList({ title, description, courses, showGrades, compact }: CourseListProps) {

  const getGradeColor = (grade?: string) => {
    if (!grade) return '';
    const gradeValue = grade.charAt(0);
    if (gradeValue === 'A') return 'text-[#115740]';
    if (gradeValue === 'B') return 'text-blue-600';
    if (gradeValue === 'C') return 'text-[#B9975B]';
    return 'text-red-600';
  };

  const totalCredits = courses.reduce((sum, course) => sum + course.credits, 0);

  return (
    <div className="border border-[#e8e4db] rounded bg-white">
      <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
        <div className="flex items-center justify-between">
          <div>
            <h3
              className="text-[#115740] font-semibold text-lg"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              {title}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">{description}</p>
          </div>
          <Badge variant="secondary">{totalCredits} Credits</Badge>
        </div>
      </div>
      <div className={compact ? 'p-4' : 'p-6'}>
        {courses.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No courses to display</p>
        ) : compact ? (
          <div className="divide-y divide-[#e8e4db]">
            {courses.map((course, idx) => (
              <div
                key={`${course.code}-${course.term}-${idx}`}
                className="flex items-center justify-between py-2.5 px-2 hover:bg-[#f7f5f0] transition-colors rounded"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="font-semibold text-sm text-[#262626] w-24 flex-shrink-0">{course.code}</span>
                  <span className="text-sm text-gray-600 truncate">{course.title}</span>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {course.hasLab && <Beaker className="h-3.5 w-3.5 text-[#B9975B]" />}
                    {course.prereqs && course.prereqs.length > 0 && <AlertTriangle className="h-3.5 w-3.5 text-yellow-600" />}
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                  <span className="text-xs text-gray-500">{course.credits} credits</span>
                  {course.meetingDays && course.meetingTime ? (
                    <span className="text-xs text-gray-400">{course.meetingDays} {course.meetingTime}</span>
                  ) : course.term ? (
                    <span className="text-xs text-gray-400">{formatTerm(course.term)}</span>
                  ) : null}
                  {showGrades && course.grade && (
                    <span className={`text-sm font-bold w-6 text-right ${getGradeColor(course.grade)}`}>
                      {course.grade}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {courses.map((course, idx) => (
              <div
                key={`${course.code}-${course.term}-${idx}`}
                className="flex items-center justify-between p-3 rounded border border-[#e8e4db] hover:bg-[#f7f5f0] transition-colors"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <BookOpen className="h-4 w-4 text-[#115740] flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[#262626]">{course.code}{course.sectionNumber ? ` - ${course.sectionNumber}` : ''}</span>
                      {course.hasLab && <Beaker className="h-3.5 w-3.5 text-[#B9975B]" />}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5 flex-wrap">
                      <span>{course.credits} credits</span>
                      {course.meetingDays && course.meetingTime && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {course.meetingDays} {course.meetingTime}
                        </span>
                      )}
                      {(course.building || course.room) && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {[course.building, course.room].filter(Boolean).join(' ')}
                        </span>
                      )}
                      {!course.meetingDays && !course.meetingTime && course.term && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTerm(course.term)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  {showGrades && course.grade && (
                    <span className={`text-lg font-bold ${getGradeColor(course.grade)}`}>
                      {course.grade}
                    </span>
                  )}
                  {course.status && (
                    <Badge
                      variant={
                        course.status === 'completed'
                          ? 'success'
                          : course.status === 'enrolled'
                          ? 'success'
                          : 'secondary'
                      }
                    >
                      {course.status.charAt(0).toUpperCase() + course.status.slice(1)}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
