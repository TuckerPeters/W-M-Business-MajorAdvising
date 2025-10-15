'use client';

import { useState } from 'react';
import Link from 'next/link';
import AdviseeList from '@/components/advisor/AdviseeList';
import AdviseeDetail from '@/components/advisor/AdviseeDetail';
import Button from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import { mockAdvisees } from '@/data/mockData';
import { Advisee } from '@/types';
import {
  Users,
  Home,
  AlertTriangle,
  TrendingUp,
  MessageSquare,
  Menu,
  X,
} from 'lucide-react';

export default function AdvisorDashboard() {
  const [selectedAdvisee, setSelectedAdvisee] = useState<Advisee | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const atRiskCount = mockAdvisees.filter(a =>
    Object.values(a.riskFlags).some(flag => flag)
  ).length;
  const undeclaredCount = mockAdvisees.filter(a => !a.declared).length;
  const avgGPA = mockAdvisees.reduce((sum, a) => sum + a.gpa, 0) / mockAdvisees.length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden"
              >
                {sidebarOpen ? <X /> : <Menu />}
              </button>
              <Users className="h-8 w-8 text-primary" />
              <div>
                <h1 className="text-xl font-bold">Advisor Dashboard</h1>
                <p className="text-sm text-muted-foreground">Faculty Advising Portal</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {selectedAdvisee && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedAdvisee(null)}
                  className="hidden md:flex"
                >
                  Back to List
                </Button>
              )}
              <Link href="/">
                <Button variant="outline" size="sm">
                  <Home className="h-4 w-4 mr-2" />
                  Home
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        {!selectedAdvisee ? (
          <div className="space-y-6">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Total Advisees</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{mockAdvisees.length}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>At Risk</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <div className="text-3xl font-bold text-red-600">{atRiskCount}</div>
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Undeclared</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{undeclaredCount}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Average GPA</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <div className="text-3xl font-bold">{avgGPA.toFixed(2)}</div>
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Advisee List */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <AdviseeList
                  advisees={mockAdvisees}
                  onSelectAdvisee={setSelectedAdvisee}
                />
              </div>

              {/* Quick Actions */}
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Quick Actions</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Button variant="outline" className="w-full justify-start">
                      <MessageSquare className="h-4 w-4 mr-2" />
                      Broadcast Reminder
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <AlertTriangle className="h-4 w-4 mr-2" />
                      View All Risks
                    </Button>
                    <Button variant="outline" className="w-full justify-start">
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Analytics Dashboard
                    </Button>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Common Questions</CardTitle>
                    <CardDescription>Most asked this week</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="p-2 rounded border text-sm">
                      <p className="font-medium mb-1">When should I declare?</p>
                      <Badge variant="secondary">Asked 23 times</Badge>
                    </div>
                    <div className="p-2 rounded border text-sm">
                      <p className="font-medium mb-1">Business Analytics prereqs?</p>
                      <Badge variant="secondary">Asked 18 times</Badge>
                    </div>
                    <div className="p-2 rounded border text-sm">
                      <p className="font-medium mb-1">AP credits count?</p>
                      <Badge variant="secondary">Asked 15 times</Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <Button
              variant="ghost"
              onClick={() => setSelectedAdvisee(null)}
              className="mb-4"
            >
              ← Back to Advisee List
            </Button>
            <AdviseeDetail advisee={selectedAdvisee} />
          </div>
        )}
      </div>
    </div>
  );
}
