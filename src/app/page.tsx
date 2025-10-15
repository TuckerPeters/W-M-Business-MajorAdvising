'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { GraduationCap, Users, ArrowRight } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-yellow-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="flex items-center justify-center mb-6">
            <GraduationCap className="h-16 w-16 text-primary" />
          </div>
          <h1 className="text-5xl font-bold mb-4">
            University Business Advising Platform
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Your 24/7 intelligent advising assistant for course planning, degree requirements,
            and major declaration guidance
          </p>
        </div>

        {/* Role Selection */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Student Portal */}
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-primary">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 rounded-lg bg-primary/10">
                  <GraduationCap className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="text-2xl">Student Portal</CardTitle>
              </div>
              <CardDescription className="text-base">
                Access your personalized advising dashboard
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Track your progress toward graduation</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Chat with AI advisor for instant answers</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Build and balance your course schedule</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Get milestone and deadline reminders</span>
                </li>
              </ul>
              <Link href="/student">
                <Button className="w-full" size="lg">
                  Enter Student Portal
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Advisor Portal */}
          <Card className="hover:shadow-lg transition-shadow cursor-pointer border-2 hover:border-primary">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 rounded-lg bg-primary/10">
                  <Users className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="text-2xl">Advisor Portal</CardTitle>
              </div>
              <CardDescription className="text-base">
                Oversee and support your advisees
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>360° view of advisee progress and risks</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Review and override AI recommendations</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Send targeted reminders and nudges</span>
                </li>
                <li className="flex items-start gap-2">
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>Access chat history and transcripts</span>
                </li>
              </ul>
              <Link href="/advisor">
                <Button className="w-full" size="lg">
                  Enter Advisor Portal
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Features */}
        <div className="mt-16 max-w-4xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>Key Features</CardTitle>
              <CardDescription>
                Built with GPT-5, Model Context Protocol, and modern web technologies
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <h3 className="font-semibold">AI-Powered Guidance</h3>
                  <p className="text-sm text-muted-foreground">
                    Get instant, source-grounded answers about credits, requirements, and planning
                  </p>
                </div>
                <div className="space-y-2">
                  <h3 className="font-semibold">Smart Scheduling</h3>
                  <p className="text-sm text-muted-foreground">
                    Balanced-schedule recommendations that avoid overload and conflicts
                  </p>
                </div>
                <div className="space-y-2">
                  <h3 className="font-semibold">Advisor Oversight</h3>
                  <p className="text-sm text-muted-foreground">
                    Full transparency with review, correction, and alert capabilities
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
