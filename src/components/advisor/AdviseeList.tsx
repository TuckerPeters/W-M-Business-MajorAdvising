'use client';

import { useState } from 'react';
import { Advisee } from '@/types';
import { Search, AlertTriangle, TrendingDown, Clock } from 'lucide-react';

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
        <AlertTriangle key="overload" className="h-3.5 w-3.5 text-red-600" aria-label="Overload Risk" />
      );
    }
    if (advisee.riskFlags.missingPrereqs) {
      icons.push(
        <AlertTriangle key="prereqs" className="h-3.5 w-3.5 text-yellow-600" aria-label="Missing Prerequisites" />
      );
    }
    if (advisee.riskFlags.gpaDip) {
      icons.push(
        <TrendingDown key="gpa" className="h-3.5 w-3.5 text-orange-600" aria-label="GPA Decline" />
      );
    }
    return icons;
  };

  const getDaysSinceContact = (date?: Date | string) => {
    if (!date) return null;
    const d = typeof date === 'string' ? new Date(date) : date;
    const days = Math.max(0, Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24)));
    return days;
  };

  const filters = [
    { key: 'all' as const, label: `All (${advisees.length})` },
    { key: 'at-risk' as const, label: `At Risk (${atRiskCount})` },
    { key: 'undeclared' as const, label: `Undeclared (${undeclaredCount})` },
  ];

  return (
    <div className="border border-[#e8e4db] rounded bg-white">
      <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0]">
        <h3
          className="text-[#115740] font-semibold text-lg"
          style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
        >
          My Advisees
        </h3>
        <p className="text-sm text-gray-500 mt-0.5">
          {advisees.length} students &bull; {atRiskCount} at risk &bull; {undeclaredCount} undeclared
        </p>
      </div>
      <div className="p-4 space-y-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search advisees..."
            className="w-full h-9 pl-9 pr-3 rounded border border-[#e8e4db] bg-white text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-1.5">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                filter === f.key
                  ? 'bg-[#115740] text-white border-[#115740]'
                  : 'border-[#e8e4db] text-gray-600 hover:bg-[#f7f5f0]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Advisee List */}
        <div className="max-h-[600px] overflow-y-auto divide-y divide-[#e8e4db]">
          {filteredAdvisees.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No advisees found
            </p>
          ) : (
            filteredAdvisees.map((advisee) => {
              const daysSinceContact = getDaysSinceContact(advisee.lastContact);
              const needsAttention = daysSinceContact !== null && daysSinceContact > 14;

              return (
                <button
                  key={advisee.id}
                  onClick={() => onSelectAdvisee?.(advisee)}
                  className="w-full text-left py-3 px-3 hover:bg-[#f7f5f0] transition-colors rounded"
                >
                  <div className="flex items-start justify-between mb-1.5">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-semibold text-[#262626]">{advisee.name}</span>
                        {getRiskIcons(advisee)}
                        {needsAttention && (
                          <Clock className="h-3.5 w-3.5 text-orange-500" aria-label="Follow-up needed" />
                        )}
                      </div>
                      <p className="text-xs text-gray-500">{advisee.email}</p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-3">
                      <p className="text-sm font-bold text-[#115740]">{advisee.gpa.toFixed(2)}</p>
                      <p className="text-xs text-gray-500">{advisee.creditsEarned} credits</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        advisee.declared
                          ? 'bg-[#115740] text-white'
                          : 'bg-[#B9975B]/20 text-[#8a6e3b]'
                      }`}>
                        {advisee.declared ? 'Declared' : 'Pre-major'}
                      </span>
                      {advisee.intendedMajor && (
                        <span className="text-xs text-gray-500">
                          {advisee.intendedMajor}
                        </span>
                      )}
                    </div>
                    {daysSinceContact !== null && (
                      <span className={`text-xs ${needsAttention ? 'text-orange-600 font-medium' : 'text-gray-400'}`}>
                        {daysSinceContact === 0 ? 'Today' : daysSinceContact === 1 ? '1d ago' : `${daysSinceContact}d ago`}
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
