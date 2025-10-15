'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Progress from '@/components/ui/Progress';
import { Course, ScheduleScore } from '@/types';
import { Plus, X, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

interface ScheduleBuilderProps {
  availableCourses: Course[];
  currentCourses?: Course[];
}

export default function ScheduleBuilder({ availableCourses, currentCourses = [] }: ScheduleBuilderProps) {
  const [selectedCourses, setSelectedCourses] = useState<Course[]>(currentCourses);

  const calculateScheduleScore = (): ScheduleScore => {
    const totalCredits = selectedCourses.reduce((sum, c) => sum + c.credits, 0);
    const avgDifficulty = selectedCourses.reduce((sum, c) => sum + c.difficultyIndex, 0) / selectedCourses.length || 0;
    const labCount = selectedCourses.filter(c => c.hasLab).length;
    const quantCourses = selectedCourses.filter(c => c.dept === 'MATH' || c.dept === 'STAT').length;

    let score = 100;
    const warnings: string[] = [];
    const suggestedSwaps: string[] = [];

    // Credit overload
    if (totalCredits > 18) {
      score -= 20;
      warnings.push('Credit overload: Consider reducing to 15-18 credits');
    } else if (totalCredits > 15) {
      score -= 5;
      warnings.push('High credit load: Monitor workload carefully');
    }

    // Too many labs
    if (labCount > 2) {
      score -= 15;
      warnings.push('Too many lab courses: Consider moving one to next semester');
    }

    // Too many quant courses
    if (quantCourses > 2) {
      score -= 15;
      warnings.push('Heavy quant load: Balance with non-quantitative courses');
    }

    // High average difficulty
    if (avgDifficulty > 0.7) {
      score -= 20;
      warnings.push('Very challenging schedule: Consider balancing difficulty');
    } else if (avgDifficulty > 0.6) {
      score -= 10;
    }

    // Suggestions
    if (avgDifficulty > 0.7) {
      const easierCourses = availableCourses.filter(c =>
        c.difficultyIndex < 0.5 && !selectedCourses.find(sc => sc.code === c.code)
      );
      if (easierCourses.length > 0) {
        suggestedSwaps.push(`Consider replacing a difficult course with ${easierCourses[0].code}`);
      }
    }

    score = Math.max(0, Math.min(100, score));

    return {
      score,
      rationale: score >= 80 ? 'Well-balanced schedule' : score >= 60 ? 'Moderately challenging schedule' : 'Consider adjusting for better balance',
      suggestedSwaps,
      warnings,
    };
  };

  const scheduleScore = calculateScheduleScore();
  const totalCredits = selectedCourses.reduce((sum, c) => sum + c.credits, 0);
  const avgDifficulty = selectedCourses.reduce((sum, c) => sum + c.difficultyIndex, 0) / selectedCourses.length || 0;

  const addCourse = (course: Course) => {
    if (!selectedCourses.find(c => c.code === course.code)) {
      setSelectedCourses([...selectedCourses, { ...course, status: 'planned' }]);
    }
  };

  const removeCourse = (courseCode: string) => {
    setSelectedCourses(selectedCourses.filter(c => c.code !== courseCode));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Schedule Score */}
      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle>Schedule Balance Score</CardTitle>
          <CardDescription>Analyzes workload, difficulty, and distribution</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Overall Balance</span>
              <span className="text-2xl font-bold">{scheduleScore.score}/100</span>
            </div>
            <Progress value={scheduleScore.score} max={100} />
            <p className="text-sm text-muted-foreground mt-2">{scheduleScore.rationale}</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Total Credits</p>
              <p className="text-xl font-bold">{totalCredits}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Avg Difficulty</p>
              <p className="text-xl font-bold">{(avgDifficulty * 10).toFixed(1)}/10</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Lab Courses</p>
              <p className="text-xl font-bold">{selectedCourses.filter(c => c.hasLab).length}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Courses</p>
              <p className="text-xl font-bold">{selectedCourses.length}</p>
            </div>
          </div>

          {scheduleScore.warnings.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                Warnings
              </p>
              {scheduleScore.warnings.map((warning, idx) => (
                <div key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span>•</span>
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          )}

          {scheduleScore.suggestedSwaps.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-semibold">Suggestions</p>
              {scheduleScore.suggestedSwaps.map((swap, idx) => (
                <div key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span>•</span>
                  <span>{swap}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Selected Courses */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Planned Schedule</CardTitle>
          <CardDescription>Your courses for next semester</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {selectedCourses.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No courses selected. Add courses from the available list.
              </p>
            ) : (
              selectedCourses.map((course) => (
                <div
                  key={course.code}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{course.code}</span>
                      <Badge variant="secondary">{course.credits} cr</Badge>
                      {course.hasLab && <Badge variant="outline">Lab</Badge>}
                    </div>
                    <p className="text-sm text-muted-foreground">{course.title}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeCourse(course.code)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Available Courses */}
      <Card>
        <CardHeader>
          <CardTitle>Available Courses</CardTitle>
          <CardDescription>Click to add to schedule</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {availableCourses
              .filter(c => !selectedCourses.find(sc => sc.code === c.code))
              .map((course) => (
                <button
                  key={course.code}
                  onClick={() => addCourse(course)}
                  className="w-full text-left p-3 rounded-lg border hover:bg-accent transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm">{course.code}</span>
                    <Plus className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-xs text-muted-foreground mb-1">{course.title}</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">{course.credits} cr</Badge>
                    <span className={`text-xs ${
                      course.difficultyIndex >= 0.7 ? 'text-red-600' :
                      course.difficultyIndex >= 0.5 ? 'text-yellow-600' :
                      'text-green-600'
                    }`}>
                      {(course.difficultyIndex * 10).toFixed(1)}/10
                    </span>
                  </div>
                </button>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
