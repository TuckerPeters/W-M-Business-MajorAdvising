'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Input from '@/components/ui/Input';
import { Advisee } from '@/types';
import { Search, AlertTriangle, TrendingDown, Clock, Mail } from 'lucide-react';

interface AdviseeListProps {
  advisees: Advisee[];
  onSelectAdvisee?: (advisee: Advisee) => void;
}

export default function AdviseeList({ advisees, onSelectAdvisee }: AdviseeListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'at-risk' | 'undeclared'>('all');

  const filteredAdvisees = advisees.filter(advisee => {
    const matchesSearch =
      advisee.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      advisee.email.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filter === 'at-risk') {
      return Object.values(advisee.riskFlags).some(flag => flag);
    }
    if (filter === 'undeclared') {
      return !advisee.declared;
    }
    return true;
  });

  const atRiskCount = advisees.filter(a => Object.values(a.riskFlags).some(flag => flag)).length;
  const undeclaredCount = advisees.filter(a => !a.declared).length;

  const getRiskIcons = (advisee: Advisee) => {
    const icons = [];
    if (advisee.riskFlags.overloadRisk) {
      icons.push(
        <AlertTriangle key="overload" className="h-4 w-4 text-red-600" aria-label="Overload Risk" />
      );
    }
    if (advisee.riskFlags.missingPrereqs) {
      icons.push(
        <AlertTriangle key="prereqs" className="h-4 w-4 text-yellow-600" aria-label="Missing Prerequisites" />
      );
    }
    if (advisee.riskFlags.gpaDip) {
      icons.push(
        <TrendingDown key="gpa" className="h-4 w-4 text-orange-600" aria-label="GPA Decline" />
      );
    }
    return icons;
  };

  const getDaysSinceContact = (date?: Date) => {
    if (!date) return null;
    const days = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
    return days;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>My Advisees</CardTitle>
        <CardDescription>
          {advisees.length} students • {atRiskCount} at risk • {undeclaredCount} undeclared
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search and Filters */}
        <div className="space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search advisees..."
              className="pl-9"
            />
          </div>

          <div className="flex gap-2">
            <Badge
              variant={filter === 'all' ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setFilter('all')}
            >
              All ({advisees.length})
            </Badge>
            <Badge
              variant={filter === 'at-risk' ? 'destructive' : 'outline'}
              className="cursor-pointer"
              onClick={() => setFilter('at-risk')}
            >
              At Risk ({atRiskCount})
            </Badge>
            <Badge
              variant={filter === 'undeclared' ? 'secondary' : 'outline'}
              className="cursor-pointer"
              onClick={() => setFilter('undeclared')}
            >
              Undeclared ({undeclaredCount})
            </Badge>
          </div>
        </div>

        {/* Advisee List */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {filteredAdvisees.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No advisees found
            </p>
          ) : (
            filteredAdvisees.map((advisee) => {
              const daysSinceContact = getDaysSinceContact(advisee.lastContact);
              const needsAttention = daysSinceContact && daysSinceContact > 14;

              return (
                <button
                  key={advisee.id}
                  onClick={() => onSelectAdvisee?.(advisee)}
                  className="w-full text-left p-4 rounded-lg border hover:bg-accent transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold">{advisee.name}</span>
                        {getRiskIcons(advisee)}
                        {needsAttention && (
                          <Clock className="h-4 w-4 text-muted-foreground" aria-label="Follow-up needed" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{advisee.email}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">GPA: {advisee.gpa.toFixed(2)}</p>
                      <p className="text-xs text-muted-foreground">{advisee.creditsEarned} credits</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant={advisee.declared ? 'success' : 'secondary'}>
                        {advisee.declared ? 'Declared' : 'Pre-major'}
                      </Badge>
                      {advisee.intendedMajor && (
                        <span className="text-xs text-muted-foreground">
                          {advisee.intendedMajor}
                        </span>
                      )}
                    </div>
                    {daysSinceContact !== null && (
                      <span className={`text-xs ${needsAttention ? 'text-orange-600 font-medium' : 'text-muted-foreground'}`}>
                        Last contact: {daysSinceContact}d ago
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
