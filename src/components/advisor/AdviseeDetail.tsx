'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Progress from '@/components/ui/Progress';
import { Advisee } from '@/types';
import { Mail, MessageSquare, FileText, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface AdviseeDetailProps {
  advisee: Advisee;
}

export default function AdviseeDetail({ advisee }: AdviseeDetailProps) {
  const hasRisks = Object.values(advisee.riskFlags).some(flag => flag);
  const declarationWindow = advisee.creditsEarned >= 39 && advisee.creditsEarned < 54;

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>{advisee.name}</CardTitle>
              <CardDescription>{advisee.email}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                <Mail className="h-4 w-4 mr-2" />
                Email
              </Button>
              <Button size="sm" variant="outline">
                <MessageSquare className="h-4 w-4 mr-2" />
                Message
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Class Year</p>
              <p className="text-xl font-bold">{advisee.classYear}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">GPA</p>
              <p className="text-xl font-bold">{advisee.gpa.toFixed(2)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Credits</p>
              <p className="text-xl font-bold">{advisee.creditsEarned}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Status</p>
              <Badge variant={advisee.declared ? 'success' : 'secondary'}>
                {advisee.declared ? 'Declared' : 'Pre-major'}
              </Badge>
            </div>
          </div>

          {advisee.intendedMajor && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Intended Major</p>
              <p className="font-medium">{advisee.intendedMajor}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Risk Flags */}
      {hasRisks && (
        <Card className="border-red-200 dark:border-red-800">
          <CardHeader>
            <CardTitle className="text-red-600 dark:text-red-400 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Risk Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {advisee.riskFlags.overloadRisk && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
                <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-red-900 dark:text-red-100">Overload Risk</p>
                  <p className="text-sm text-red-700 dark:text-red-300">
                    Student is taking a high credit load with multiple difficult courses
                  </p>
                  <Button size="sm" variant="outline" className="mt-2">
                    Review Schedule
                  </Button>
                </div>
              </div>
            )}

            {advisee.riskFlags.missingPrereqs && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-yellow-900 dark:text-yellow-100">Missing Prerequisites</p>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300">
                    Student may be missing required prerequisites for enrolled courses
                  </p>
                  <Button size="sm" variant="outline" className="mt-2">
                    Check Prerequisites
                  </Button>
                </div>
              </div>
            )}

            {advisee.riskFlags.gpaDip && (
              <div className="flex items-start gap-3 p-3 rounded-lg bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800">
                <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-orange-900 dark:text-orange-100">GPA Decline</p>
                  <p className="text-sm text-orange-700 dark:text-orange-300">
                    Student's GPA has decreased from previous semester
                  </p>
                  <Button size="sm" variant="outline" className="mt-2">
                    Schedule Check-in
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Degree Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Overall Progress</span>
              <span className="text-sm text-muted-foreground">
                {advisee.creditsEarned} / 120 credits
              </span>
            </div>
            <Progress value={advisee.creditsEarned} max={120} />
          </div>

          {declarationWindow && !advisee.declared && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800">
              <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-green-900 dark:text-green-100">
                  Ready to Declare Major
                </p>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Student is within declaration window (39-54 credits)
                </p>
                <Button size="sm" variant="outline" className="mt-2">
                  Send Declaration Reminder
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-lg border">
              <MessageSquare className="h-4 w-4 text-muted-foreground mt-1" />
              <div className="flex-1">
                <p className="text-sm font-medium">Chat Session</p>
                <p className="text-sm text-muted-foreground">
                  Asked about Business Analytics prerequisites
                </p>
                <p className="text-xs text-muted-foreground mt-1">2 days ago</p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-lg border">
              <FileText className="h-4 w-4 text-muted-foreground mt-1" />
              <div className="flex-1">
                <p className="text-sm font-medium">Schedule Review</p>
                <p className="text-sm text-muted-foreground">
                  Planned schedule for Spring 2025
                </p>
                <p className="text-xs text-muted-foreground mt-1">1 week ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3">
          <Button variant="outline">
            <FileText className="h-4 w-4 mr-2" />
            View Transcript
          </Button>
          <Button variant="outline">
            <MessageSquare className="h-4 w-4 mr-2" />
            View Chat History
          </Button>
          <Button variant="outline">
            <Mail className="h-4 w-4 mr-2" />
            Send Reminder
          </Button>
          <Button variant="outline">
            <CheckCircle2 className="h-4 w-4 mr-2" />
            Add Note
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
