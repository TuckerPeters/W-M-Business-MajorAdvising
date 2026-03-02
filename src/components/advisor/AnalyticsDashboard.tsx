'use client';

import { Advisee } from '@/types';
import { AdvisorAlert } from '@/lib/api-client';
import {
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Users,
  GraduationCap,
  AlertCircle,
  ShieldAlert,
  BookOpen,
} from 'lucide-react';
import Badge from '@/components/ui/Badge';

const serif = 'Georgia, "Times New Roman", serif';

interface AnalyticsDashboardProps {
  advisees: Advisee[];
  alerts: AdvisorAlert[];
  commonQuestions: { text: string; count: number }[];
}

/* ─── Helpers ─────────────────────────────────────── */

function getGPADistribution(advisees: Advisee[]) {
  return [
    { label: '3.5–4.0', min: 3.5, max: 4.01, color: '#115740' },
    { label: '3.0–3.49', min: 3.0, max: 3.5, color: '#1a7a5a' },
    { label: '2.5–2.99', min: 2.5, max: 3.0, color: '#B9975B' },
    { label: '2.0–2.49', min: 2.0, max: 2.5, color: '#d4a843' },
    { label: '<2.0', min: 0, max: 2.0, color: '#c0392b' },
  ].map(r => ({
    ...r,
    count: advisees.filter(a => a.gpa >= r.min && a.gpa < r.max).length,
  }));
}

function getCreditDistribution(advisees: Advisee[]) {
  return [
    { label: 'Freshman', sub: '0–30 credits', min: 0, max: 31 },
    { label: 'Sophomore', sub: '31–60 credits', min: 31, max: 61 },
    { label: 'Junior', sub: '61–90 credits', min: 61, max: 91 },
    { label: 'Senior', sub: '91–120 credits', min: 91, max: 121 },
  ].map(r => ({
    ...r,
    count: advisees.filter(a => a.creditsEarned >= r.min && a.creditsEarned < r.max).length,
  }));
}

function getClassYearDistribution(advisees: Advisee[]) {
  const years = [2026, 2027, 2028, 2029];
  return years.map(y => ({
    label: `'${String(y).slice(2)}`,
    year: y,
    count: advisees.filter(a => a.classYear === y).length,
  }));
}

function getSeverityStyles(severity: string) {
  switch (severity.toLowerCase()) {
    case 'high': return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', badge: 'bg-red-600' };
    case 'medium': return { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', badge: 'bg-amber-500' };
    default: return { bg: 'bg-sky-50', border: 'border-sky-200', text: 'text-sky-800', badge: 'bg-sky-500' };
  }
}

/* ─── SVG Donut Chart ──────────────────────────────── */

function DonutChart({ segments, size = 160, strokeWidth = 22 }: {
  segments: { value: number; color: string; label: string }[];
  size?: number;
  strokeWidth?: number;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;
  let offset = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
      {/* Background track */}
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke="#e8e4db" strokeWidth={strokeWidth}
      />
      {segments.map((seg, i) => {
        const pct = seg.value / total;
        const dashLen = pct * circumference;
        const dashOffset = -offset * circumference;
        offset += pct;
        return (
          <circle
            key={i}
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${dashLen} ${circumference - dashLen}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="butt"
            className="transition-all duration-700 ease-out"
          />
        );
      })}
    </svg>
  );
}

/* ─── Vertical Bar Chart ───────────────────────────── */

function BarChart({ bars, height = 140, barColor }: {
  bars: { label: string; sub?: string; count: number }[];
  height?: number;
  barColor?: string | ((index: number) => string);
}) {
  const maxVal = Math.max(...bars.map(b => b.count), 1);

  return (
    <div className="flex items-end justify-around gap-2" style={{ height }}>
      {bars.map((bar, i) => {
        const barH = Math.max((bar.count / maxVal) * (height - 36), bar.count > 0 ? 8 : 2);
        const color = typeof barColor === 'function' ? barColor(i) : (barColor || '#115740');
        return (
          <div key={bar.label} className="flex flex-col items-center gap-1 flex-1 min-w-0">
            <span className="text-xs font-bold text-[#262626]">{bar.count}</span>
            <div
              className="w-full max-w-[40px] rounded-t transition-all duration-700 ease-out"
              style={{ height: barH, background: color }}
            />
            <div className="text-center mt-1">
              <p className="text-[11px] font-medium text-[#262626] leading-tight">{bar.label}</p>
              {bar.sub && <p className="text-[9px] text-gray-400 leading-tight">{bar.sub}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Main Component ───────────────────────────────── */

export default function AnalyticsDashboard({ advisees, alerts, commonQuestions }: AnalyticsDashboardProps) {
  const total = advisees.length;
  const declaredCount = advisees.filter(a => a.declared).length;
  const undeclaredCount = total - declaredCount;
  const overloadCount = advisees.filter(a => a.riskFlags.overloadRisk).length;
  const prereqCount = advisees.filter(a => a.riskFlags.missingPrereqs).length;
  const gpaRiskCount = advisees.filter(a => a.riskFlags.gpaDip).length;
  const atRiskCount = advisees.filter(a => Object.values(a.riskFlags).some(f => f)).length;
  const healthyCount = total - atRiskCount;
  const avgGPA = total > 0 ? advisees.reduce((s, a) => s + a.gpa, 0) / total : 0;
  const highGPA = advisees.filter(a => a.gpa >= 3.5).length;

  const gpaDistribution = getGPADistribution(advisees);
  const creditDistribution = getCreditDistribution(advisees);
  const classYearDistribution = getClassYearDistribution(advisees);

  const declaredPct = total > 0 ? Math.round((declaredCount / total) * 100) : 0;
  const healthyPct = total > 0 ? Math.round((healthyCount / total) * 100) : 0;

  return (
    <div className="space-y-6">

      {/* ── Row 1: Summary Stat Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Advisees', value: total, icon: Users, iconColor: 'text-[#B9975B]', valueColor: 'text-[#115740]' },
          { label: 'Average GPA', value: avgGPA.toFixed(2), icon: TrendingUp, iconColor: 'text-[#B9975B]', valueColor: 'text-[#115740]', sub: `${highGPA} above 3.5` },
          { label: 'At Risk', value: atRiskCount, icon: ShieldAlert, iconColor: 'text-red-400', valueColor: atRiskCount > 0 ? 'text-red-600' : 'text-[#115740]', sub: atRiskCount > 0 ? `${Math.round((atRiskCount / total) * 100)}% of advisees` : 'None flagged' },
          { label: 'Declared', value: `${declaredCount}/${total}`, icon: GraduationCap, iconColor: 'text-[#B9975B]', valueColor: 'text-[#115740]', sub: `${declaredPct}% declaration rate` },
        ].map((card) => (
          <div
            key={card.label}
            className="relative overflow-hidden bg-white border border-[#e8e4db] rounded-lg p-5"
          >
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#115740] to-[#B9975B]" />
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider mb-1" style={{ fontFamily: serif }}>{card.label}</p>
                <p className={`text-3xl font-bold ${card.valueColor}`}>{card.value}</p>
                {card.sub && <p className="text-[11px] text-gray-400 mt-1">{card.sub}</p>}
              </div>
              <div className="p-2 rounded-lg bg-[#f7f5f0]">
                <card.icon className={`h-5 w-5 ${card.iconColor}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Donut Charts + GPA Bars ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Declaration Status — Donut */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              Declaration Status
            </h3>
          </div>
          <div className="p-6 flex flex-col items-center">
            <div className="relative">
              <DonutChart
                segments={[
                  { value: declaredCount, color: '#115740', label: 'Declared' },
                  { value: undeclaredCount, color: '#B9975B', label: 'Pre-major' },
                ]}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-[#115740]">{declaredPct}%</span>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">Declared</span>
              </div>
            </div>
            <div className="flex items-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#115740]" />
                <span className="text-xs text-gray-600">Declared ({declaredCount})</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#B9975B]" />
                <span className="text-xs text-gray-600">Pre-major ({undeclaredCount})</span>
              </div>
            </div>
          </div>
        </div>

        {/* Risk Health — Donut */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              Risk Overview
            </h3>
          </div>
          <div className="p-6 flex flex-col items-center">
            <div className="relative">
              <DonutChart
                segments={[
                  { value: healthyCount, color: '#115740', label: 'Healthy' },
                  { value: overloadCount, color: '#c0392b', label: 'Overload' },
                  { value: prereqCount, color: '#e67e22', label: 'Prereqs' },
                  { value: gpaRiskCount, color: '#f39c12', label: 'GPA Dip' },
                ]}
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-[#115740]">{healthyPct}%</span>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">On Track</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-5 gap-y-1 mt-4">
              {[
                { color: '#115740', label: 'On Track', count: healthyCount },
                { color: '#c0392b', label: 'Overload', count: overloadCount },
                { color: '#e67e22', label: 'Prereqs', count: prereqCount },
                { color: '#f39c12', label: 'GPA Dip', count: gpaRiskCount },
              ].map(item => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: item.color }} />
                  <span className="text-xs text-gray-600">{item.label} ({item.count})</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Class Year — Bar Chart */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              Class Year Breakdown
            </h3>
          </div>
          <div className="p-6">
            <BarChart
              bars={classYearDistribution}
              barColor={(i) => ['#115740', '#1a7a5a', '#B9975B', '#d4b876'][i] || '#115740'}
            />
          </div>
        </div>
      </div>

      {/* ── Row 3: GPA Distribution + Credits Progress ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* GPA Distribution — Vertical Bars */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              GPA Distribution
            </h3>
            <p className="text-[11px] text-gray-400 mt-0.5">Students grouped by GPA range</p>
          </div>
          <div className="p-6">
            <BarChart
              bars={gpaDistribution.map(d => ({ label: d.label, count: d.count }))}
              height={160}
              barColor={(i) => gpaDistribution[i]?.color || '#115740'}
            />
          </div>
        </div>

        {/* Credits Distribution — Vertical Bars */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              Credits Progress
            </h3>
            <p className="text-[11px] text-gray-400 mt-0.5">Students grouped by credits earned</p>
          </div>
          <div className="p-6">
            <BarChart
              bars={creditDistribution}
              height={160}
              barColor={(i) => ['#115740', '#1a7a5a', '#B9975B', '#d4b876'][i] || '#115740'}
            />
          </div>
        </div>
      </div>

      {/* ── Row 4: Risk Details + Active Alerts ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Risk Details */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
            <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
              Risk Breakdown
            </h3>
          </div>
          <div className="p-6 space-y-4">
            {[
              { label: 'Overload Risk', count: overloadCount, color: '#c0392b', bgColor: 'bg-red-50', borderColor: 'border-red-100', icon: AlertTriangle, iconColor: 'text-red-500', desc: 'High credit load or difficult course combination' },
              { label: 'Missing Prerequisites', count: prereqCount, color: '#e67e22', bgColor: 'bg-amber-50', borderColor: 'border-amber-100', icon: AlertCircle, iconColor: 'text-amber-500', desc: 'Enrolled without required prerequisites' },
              { label: 'GPA Decline', count: gpaRiskCount, color: '#f39c12', bgColor: 'bg-orange-50', borderColor: 'border-orange-100', icon: TrendingDown, iconColor: 'text-orange-500', desc: 'GPA trending below 2.0 threshold' },
            ].map((risk) => {
              const pct = total > 0 ? (risk.count / total) * 100 : 0;
              return (
                <div key={risk.label} className={`${risk.bgColor} ${risk.borderColor} border rounded-lg p-4`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <risk.icon className={`h-4 w-4 ${risk.iconColor}`} />
                      <span className="text-sm font-semibold text-[#262626]">{risk.label}</span>
                    </div>
                    <span className="text-lg font-bold" style={{ color: risk.color }}>{risk.count}</span>
                  </div>
                  <p className="text-[11px] text-gray-500 mb-2">{risk.desc}</p>
                  <div className="h-2 rounded-full bg-white/70 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700 ease-out"
                      style={{ width: `${pct}%`, background: risk.color, minWidth: risk.count > 0 ? '8px' : '0' }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-400 mt-1">{risk.count} of {total} students ({Math.round(pct)}%)</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Active Alerts */}
        <div className="border border-[#e8e4db] rounded-lg bg-white">
          <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg flex items-center justify-between">
            <div>
              <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
                Active Alerts
              </h3>
              <p className="text-[11px] text-gray-400 mt-0.5">Automated risk notifications</p>
            </div>
            {alerts.length > 0 && (
              <span className="text-xs font-bold text-white bg-red-500 rounded-full px-2 py-0.5">
                {alerts.length}
              </span>
            )}
          </div>
          <div className="max-h-[380px] overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="p-3 rounded-full bg-green-50 mb-3">
                  <BookOpen className="h-6 w-6 text-green-500" />
                </div>
                <p className="text-sm font-medium text-gray-600">All Clear</p>
                <p className="text-xs text-gray-400 mt-1">No active alerts for your advisees</p>
              </div>
            ) : (
              <div className="divide-y divide-[#e8e4db]">
                {alerts.map((alert, i) => {
                  const styles = getSeverityStyles(alert.severity);
                  return (
                    <div key={i} className="px-5 py-3.5 flex items-start gap-3 hover:bg-[#f7f5f0] transition-colors">
                      <div className={`mt-0.5 p-1 rounded ${styles.bg}`}>
                        {alert.severity === 'high'
                          ? <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                          : <AlertCircle className="h-3.5 w-3.5 text-amber-600" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-[#262626]">{alert.studentName}</p>
                          <span className={`text-[9px] font-bold uppercase tracking-wider text-white px-1.5 py-0.5 rounded ${styles.badge}`}>
                            {alert.severity}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">{alert.message}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Row 5: Common Questions ── */}
      <div className="border border-[#e8e4db] rounded-lg bg-white">
        <div className="px-6 py-4 border-b border-[#e8e4db] bg-[#f7f5f0] rounded-t-lg">
          <h3 className="text-[#115740] font-semibold text-sm uppercase tracking-wider" style={{ fontFamily: serif }}>
            Trending Student Questions
          </h3>
          <p className="text-[11px] text-gray-400 mt-0.5">Most frequently asked questions, clustered by similarity</p>
        </div>
        <div className="p-6">
          {commonQuestions.length > 0 ? (
            <div className="space-y-3">
              {commonQuestions.map((q, i) => {
                const maxCount = Math.max(...commonQuestions.map(cq => cq.count), 1);
                const pct = (q.count / maxCount) * 100;
                return (
                  <div key={i} className="group">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-[#115740] text-white flex items-center justify-center text-[10px] font-bold mt-0.5">
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[#262626] leading-snug">{q.text}</p>
                        <div className="flex items-center gap-3 mt-2">
                          <div className="flex-1 h-1.5 rounded-full bg-[#f7f5f0] overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-700 ease-out"
                              style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #115740, #B9975B)' }}
                            />
                          </div>
                          <Badge variant="secondary">
                            {q.count} {q.count === 1 ? 'time' : 'times'}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-6">No similar questions yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
