'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Progress from '@/components/ui/Progress';
import Badge from '@/components/ui/Badge';
import { Student, Milestone } from '@/types';
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface ProgressPanelProps {
  student: Student;
  milestones: Milestone[];
}

export default function ProgressPanel({ student, milestones }: ProgressPanelProps) {
  const graduationProgress = (student.creditsEarned / 120) * 100;
  const declarationWindow = student.creditsEarned >= 39 && student.creditsEarned < 54;

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Academic Progress</CardTitle>
          <CardDescription>
            Class of {student.classYear} • {student.intendedMajor || 'Undeclared'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Credits Earned</span>
              <span className="text-sm text-muted-foreground">
                {student.creditsEarned} / 120
              </span>
            </div>
            <Progress value={student.creditsEarned} max={120} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">GPA</p>
              <p className="text-2xl font-bold">{student.gpa.toFixed(2)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">AP Credits</p>
              <p className="text-2xl font-bold">{student.apCredits}</p>
            </div>
          </div>

          {declarationWindow && !student.declared && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800">
              <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                  Declaration Window Open
                </p>
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  You can now declare your major. Must declare before earning 54 credits.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Milestones */}
      <Card>
        <CardHeader>
          <CardTitle>Milestones</CardTitle>
          <CardDescription>Track your progress toward graduation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {milestones.map((milestone) => (
              <div
                key={milestone.id}
                className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent transition-colors"
              >
                {milestone.completed ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{milestone.title}</p>
                    {milestone.completed ? (
                      <Badge variant="success">Complete</Badge>
                    ) : milestone.deadline ? (
                      <Badge variant="warning">
                        Due {milestone.deadline.toLocaleDateString()}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-sm text-muted-foreground">{milestone.description}</p>
                  {milestone.credits && (
                    <div className="mt-2">
                      <Progress
                        value={milestone.credits.current}
                        max={milestone.credits.required}
                        className="h-2"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        {milestone.credits.current} / {milestone.credits.required} credits
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
