'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { Course } from '@/types';
import { BookOpen, Beaker, AlertTriangle } from 'lucide-react';

interface CourseListProps {
  title: string;
  description: string;
  courses: Course[];
  showGrades?: boolean;
}

export default function CourseList({ title, description, courses, showGrades }: CourseListProps) {
  const getDifficultyColor = (index: number) => {
    if (index >= 0.7) return 'text-red-600 dark:text-red-400';
    if (index >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getGradeColor = (grade?: string) => {
    if (!grade) return '';
    const gradeValue = grade.charAt(0);
    if (gradeValue === 'A') return 'text-green-600 dark:text-green-400';
    if (gradeValue === 'B') return 'text-blue-600 dark:text-blue-400';
    if (gradeValue === 'C') return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const totalCredits = courses.reduce((sum, course) => sum + course.credits, 0);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <Badge variant="secondary">{totalCredits} Credits</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {courses.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No courses to display</p>
          ) : (
            courses.map((course) => (
              <div
                key={course.code}
                className="flex items-start justify-between p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                    <span className="font-semibold">{course.code}</span>
                    {course.hasLab && (
                      <Beaker className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    )}
                    {course.prereqs && course.prereqs.length > 0 && (
                      <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                    )}
                  </div>
                  <p className="text-sm text-foreground mb-1">{course.title}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{course.credits} credits</span>
                    <span className={getDifficultyColor(course.difficultyIndex)}>
                      Difficulty: {(course.difficultyIndex * 10).toFixed(1)}/10
                    </span>
                    {course.term && <span>{course.term}</span>}
                  </div>
                  {course.prereqs && course.prereqs.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Prerequisites: {course.prereqs.join(', ')}
                    </p>
                  )}
                </div>
                <div className="flex flex-col items-end gap-2">
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
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {course.status}
                    </Badge>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
