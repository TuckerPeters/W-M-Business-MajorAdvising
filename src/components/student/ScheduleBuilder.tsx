'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  DragStartEvent,
  DragEndEvent,
  useDroppable,
} from '@dnd-kit/core';
import Badge from '@/components/ui/Badge';
import TimelineCourseCard from './TimelineCourseCard';
import { Course, Section } from '@/types';
import {
  AlertTriangle,
  Search,
  ChevronDown,
  ChevronRight,
  Clock,
  MapPin,
  User,
  X,
  Filter,
} from 'lucide-react';

/* =========================================================
   Time Parsing Utilities
========================================================= */

interface TimeSlot {
  day: string;          // "M" | "T" | "W" | "R" | "F"
  startMin: number;     // minutes from midnight
  endMin: number;
}

const DAY_LABELS: Record<string, string> = {
  M: 'Mon', T: 'Tue', W: 'Wed', R: 'Thu', F: 'Fri',
};
const DAY_ORDER = ['M', 'T', 'W', 'R', 'F'];

/**
 * Parse a single time token like "9", "9:30", "11a", "12:20p", "5:00pm"
 * Returns { hour, minute, ampm } where ampm is 'a'|'p'|''
 */
function parseTimePart(s: string): { hour: number; minute: number; ampm: string } | null {
  const m = s.trim().match(/^(\d{1,2})(?::(\d{2}))?\s*(a|p|am|pm)?$/i);
  if (!m) return null;
  return {
    hour: parseInt(m[1]),
    minute: m[2] ? parseInt(m[2]) : 0,
    ampm: (m[3] || '')[0]?.toLowerCase() || '',
  };
}

/** Convert hour + minute + am/pm to minutes from midnight */
function toMinutes(h: number, m: number, ampm: string): number {
  if (ampm === 'a' && h === 12) h = 0;
  else if (ampm === 'p' && h < 12) h += 12;
  return h * 60 + m;
}

/**
 * Parse a time range like "9:30-10:50a", "2-3:20p", "11a-12:20p", "9-11:50a"
 * The am/pm on the end time applies to start too unless start has its own.
 */
function parseTimeRange(time: string): { startMin: number; endMin: number } | null {
  if (!time) return null;
  const parts = time.split('-');
  if (parts.length !== 2) return null;

  const start = parseTimePart(parts[0]);
  const end = parseTimePart(parts[1]);
  if (!start || !end) return null;

  // Resolve AM/PM: end's suffix is authoritative if start has none
  const endAmpm = end.ampm || '';
  const startAmpm = start.ampm || '';

  let endMin = toMinutes(end.hour, end.minute, endAmpm);

  // For start: use its own ampm if present, otherwise infer from end
  let startMin: number;
  if (startAmpm) {
    startMin = toMinutes(start.hour, start.minute, startAmpm);
  } else if (endAmpm) {
    // Try same period first
    const samePeriod = toMinutes(start.hour, start.minute, endAmpm);
    if (samePeriod <= endMin) {
      startMin = samePeriod;
    } else {
      // Start is in the opposite period (e.g., 11-12:20p → 11am to 12:20pm)
      const oppPeriod = toMinutes(start.hour, start.minute, endAmpm === 'p' ? 'a' : 'p');
      startMin = oppPeriod;
    }
  } else {
    // No AM/PM at all — heuristic: times < 7 are PM
    startMin = start.hour * 60 + start.minute;
    if (start.hour < 7) startMin += 12 * 60;
    if (end.hour < 7) endMin += 12 * 60;
  }

  if (endMin <= startMin) return null; // sanity check
  return { startMin, endMin };
}

/** Expand "MWF" → ["M","W","F"], "TR" → ["T","R"] */
function expandDays(days: string): string[] {
  if (!days) return [];
  return days.split('').filter((d) => DAY_ORDER.includes(d));
}

/**
 * Get all time slots for a course.
 * Handles compound patterns like "TR 2-3:20p" (days in meetingDays, time in meetingTime)
 * and semicolon-separated entries like "2-3:20p; W 4:30-5:50p" where extra day+time
 * segments appear in the meetingTime field.
 */
function getCourseSlots(course: Course): TimeSlot[] {
  if (!course.meetingDays && !course.meetingTime) return [];

  const slots: TimeSlot[] = [];
  const days = course.meetingDays || '';
  const time = course.meetingTime || '';

  // Split on semicolons for compound meeting patterns
  // e.g. meetingDays="TR", meetingTime="2-3:20p; W 4:30-5:50p"
  const segments = time.split(';').map((s) => s.trim()).filter(Boolean);

  if (segments.length === 0) return [];

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    // Check if segment starts with day letters (e.g., "W 4:30-5:50p")
    const dayTimeMatch = seg.match(/^([MTWRF]+)\s+(.+)$/);

    let segDays: string;
    let segTime: string;
    if (dayTimeMatch) {
      segDays = dayTimeMatch[1];
      segTime = dayTimeMatch[2];
    } else if (i === 0) {
      // First segment uses the meetingDays field
      segDays = days;
      segTime = seg;
    } else {
      // Subsequent segments without days — skip (shouldn't happen)
      continue;
    }

    const range = parseTimeRange(segTime);
    if (!range) continue;

    expandDays(segDays).forEach((d) => {
      slots.push({ day: d, startMin: range.startMin, endMin: range.endMin });
    });
  }

  return slots;
}

/** Check if two time slots overlap */
function slotsOverlap(a: TimeSlot, b: TimeSlot): boolean {
  return a.day === b.day && a.startMin < b.endMin && b.startMin < a.endMin;
}

/** Check if a course overlaps with any in a list */
function courseOverlapsWithAny(course: Course, existing: Course[]): boolean {
  const newSlots = getCourseSlots(course);
  if (newSlots.length === 0) return false;
  for (const ex of existing) {
    const exSlots = getCourseSlots(ex);
    for (const ns of newSlots) {
      for (const es of exSlots) {
        if (slotsOverlap(ns, es)) return true;
      }
    }
  }
  return false;
}

/** Find all overlap pairs among courses */
function findOverlaps(courses: Course[]): Set<string> {
  const overlapping = new Set<string>();
  for (let i = 0; i < courses.length; i++) {
    for (let j = i + 1; j < courses.length; j++) {
      const slotsA = getCourseSlots(courses[i]);
      const slotsB = getCourseSlots(courses[j]);
      for (const a of slotsA) {
        for (const b of slotsB) {
          if (slotsOverlap(a, b)) {
            overlapping.add(courses[i].code);
            overlapping.add(courses[j].code);
          }
        }
      }
    }
  }
  return overlapping;
}

/* =========================================================
   Calendar Droppable Zone
========================================================= */
function CalendarDropZone({ children }: { children: React.ReactNode }) {
  const { setNodeRef } = useDroppable({ id: 'semester:planned' });
  return (
    <div ref={setNodeRef} className="flex-1 flex flex-col min-w-0">
      {children}
    </div>
  );
}

/* =========================================================
   Weekly Calendar Grid Component
========================================================= */

const CALENDAR_START = 8 * 60;   // 8:00 AM
const CALENDAR_END = 21 * 60;    // 9:00 PM
const DAY_HEADER_HEIGHT = 32;    // px for day header row

function formatHour(mins: number): string {
  const h = Math.floor(mins / 60);
  const suffix = h >= 12 ? 'PM' : 'AM';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12} ${suffix}`;
}

interface CalendarBlockProps {
  course: Course;
  slot: TimeSlot;
  isOverlapping: boolean;
  colorVariant: 'green' | 'gold';
  hourHeight: number;
  onRemove: () => void;
}

const blockColors = {
  green: 'bg-[#115740]/10 border-[#115740]/40 text-[#115740]',
  gold: 'bg-[#B9975B]/15 border-[#B9975B]/50 text-[#6b5a2e]',
  overlap: 'bg-red-50 border-red-400 text-red-800',
};

function CalendarBlock({ course, slot, isOverlapping, colorVariant, hourHeight, onRemove }: CalendarBlockProps) {
  const top = ((slot.startMin - CALENDAR_START) / 60) * hourHeight;
  const height = ((slot.endMin - slot.startMin) / 60) * hourHeight;

  return (
    <div
      className={`absolute left-0.5 right-0.5 rounded border text-[10px] leading-tight overflow-hidden transition-colors group ${
        isOverlapping ? blockColors.overlap : blockColors[colorVariant]
      }`}
      style={{ top: `${top}px`, height: `${Math.max(height, 16)}px` }}
    >
      <div className="px-1 py-0.5 h-full flex flex-col justify-between relative">
        <div>
          <div className="font-bold truncate">{course.code}</div>
          {height > 28 && (
            <div className="truncate opacity-70 text-[9px]">{course.meetingTime}</div>
          )}
          {height > 42 && course.building && (
            <div className="truncate opacity-60 text-[9px]">{course.building} {course.room}</div>
          )}
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute top-0 right-0 p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100 text-gray-400 hover:text-red-500 transition-all"
        >
          <X className="h-2.5 w-2.5" />
        </button>
      </div>
    </div>
  );
}

interface WeeklyCalendarProps {
  courses: Course[];
  overlappingCodes: Set<string>;
  onRemoveCourse: (code: string) => void;
}

function WeeklyCalendar({ courses, overlappingCodes, onRemoveCourse }: WeeklyCalendarProps) {
  const totalHours = (CALENDAR_END - CALENDAR_START) / 60;
  const hours = Array.from({ length: totalHours }, (_, i) => CALENDAR_START + i * 60);

  // Measure container and compute hourHeight to exactly fill available space
  const containerRef = useRef<HTMLDivElement>(null);
  const [hourHeight, setHourHeight] = useState(28);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const compute = () => {
      const available = el.clientHeight - DAY_HEADER_HEIGHT - 5;
      const h = Math.max(20, available / totalHours);
      setHourHeight(h);
    };
    compute();
    const observer = new ResizeObserver(compute);
    observer.observe(el);
    return () => observer.disconnect();
  }, [totalHours]);

  // Assign alternating green/gold colors per course
  const colorMap = useMemo(() => {
    const map: Record<string, 'green' | 'gold'> = {};
    const variants: ('green' | 'gold')[] = ['green', 'gold'];
    courses.forEach((c, i) => { map[c.code] = variants[i % 2]; });
    return map;
  }, [courses]);

  // Group slots by day
  const slotsByDay: Record<string, { course: Course; slot: TimeSlot }[]> = {};
  DAY_ORDER.forEach((d) => { slotsByDay[d] = []; });
  courses.forEach((course) => {
    getCourseSlots(course).forEach((slot) => {
      if (slotsByDay[slot.day]) {
        slotsByDay[slot.day].push({ course, slot });
      }
    });
  });

  return (
    <div ref={containerRef} className="border border-[#e8e4db] rounded bg-white flex-1 min-h-0 overflow-hidden">
      <div className="flex h-full min-w-[600px]">
        {/* Time gutter */}
        <div className="w-14 flex-shrink-0 border-r border-[#e8e4db] bg-[#f7f5f0]">
          <div style={{ height: `${DAY_HEADER_HEIGHT}px` }} className="border-b border-[#e8e4db]" />
          {hours.map((h) => (
            <div
              key={h}
              className="border-b border-[#e8e4db] text-[10px] text-gray-400 text-right pr-2 pt-0.5"
              style={{ height: `${hourHeight}px` }}
            >
              {formatHour(h)}
            </div>
          ))}
        </div>

        {/* Day columns */}
        {DAY_ORDER.map((day) => (
          <div key={day} className="flex-1 min-w-0 border-r border-[#e8e4db] last:border-r-0">
            {/* Day header */}
            <div
              style={{ height: `${DAY_HEADER_HEIGHT}px` }}
              className="border-b border-[#e8e4db] bg-[#f7f5f0] flex items-center justify-center"
            >
              <span
                className="text-xs font-semibold text-[#115740]"
                style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
              >
                {DAY_LABELS[day]}
              </span>
            </div>
            {/* Time grid + blocks */}
            <div className="relative">
              {hours.map((h) => (
                <div
                  key={h}
                  className="border-b border-[#e8e4db]/60"
                  style={{ height: `${hourHeight}px` }}
                />
              ))}
              {/* Course blocks */}
              {slotsByDay[day].map(({ course, slot }, idx) => (
                <CalendarBlock
                  key={`${course.code}-${idx}`}
                  course={course}
                  slot={slot}
                  isOverlapping={overlappingCodes.has(course.code)}
                  colorVariant={colorMap[course.code] || 'green'}
                  hourHeight={hourHeight}
                  onRemove={() => onRemoveCourse(course.code)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =========================================================
   Main ScheduleBuilder
========================================================= */

interface ScheduleBuilderProps {
  availableCourses: Course[];
  plannedCourses?: Course[];
  onCourseAdded?: (course: Course) => Promise<Course | null>;
  onCourseRemoved?: (course: Course) => Promise<boolean>;
}

export default function ScheduleBuilder({
  availableCourses,
  plannedCourses = [],
  onCourseAdded,
  onCourseRemoved,
}: ScheduleBuilderProps) {
  // Enrich planned courses with meeting data from available courses' sections
  const enrichedPlanned = useMemo(() => {
    return plannedCourses.map((pc) => {
      if (pc.meetingDays && pc.meetingTime) return pc; // already has meeting data
      // Try to find matching section from available courses
      const avail = availableCourses.find((c) => c.code === pc.code);
      if (!avail?.sections) return pc;
      // Match by section number or CRN
      const section = pc.sectionNumber
        ? avail.sections.find((s) => s.sectionNumber === pc.sectionNumber)
        : pc.crn
        ? avail.sections.find((s) => s.crn === pc.crn)
        : avail.sections[0]; // fallback to first section
      if (!section) return pc;
      return {
        ...pc,
        meetingDays: pc.meetingDays || section.meetingDays,
        meetingTime: pc.meetingTime || section.meetingTime,
        building: pc.building || section.building,
        room: pc.room || section.room,
        instructor: pc.instructor || section.instructor,
        sectionNumber: pc.sectionNumber || section.sectionNumber,
        crn: pc.crn || section.crn,
      };
    });
  }, [plannedCourses, availableCourses]);

  const [selectedCourses, setSelectedCourses] = useState<Course[]>([]);
  const initializedRef = useRef(false);

  // Initialize from enriched planned courses once data is available
  useEffect(() => {
    if (!initializedRef.current && enrichedPlanned.length > 0) {
      initializedRef.current = true;
      setSelectedCourses(enrichedPlanned);
    }
  }, [enrichedPlanned]);

  const [searchQuery, setSearchQuery] = useState('');
  const [deptFilter, setDeptFilter] = useState<string>('all');
  const [expandedDepts, setExpandedDepts] = useState<Set<string>>(new Set());
  const [sectionPickerCourse, setSectionPickerCourse] = useState<Course | null>(null);
  const [hideOverlapping, setHideOverlapping] = useState(false);

  // DnD state
  const [activeDragCourse, setActiveDragCourse] = useState<Course | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor),
  );

  const totalCredits = selectedCourses.reduce((sum, c) => sum + c.credits, 0);
  const allPlannedCodes = new Set(selectedCourses.map((c) => c.code));

  // Detect overlaps among planned courses
  const overlappingCodes = useMemo(() => findOverlaps(selectedCourses), [selectedCourses]);

  // Schedule score
  const scheduleScore = useMemo(() => {
    if (selectedCourses.length === 0) {
      return { score: 0, rationale: 'Add courses to see your schedule balance score', warnings: [] as string[] };
    }
    let score = 100;
    const warnings: string[] = [];
    if (totalCredits > 18) {
      score -= 20;
      warnings.push('Credit overload: Consider reducing to 15-18 credits');
    } else if (totalCredits > 15) {
      score -= 5;
      warnings.push('High credit load: Monitor workload carefully');
    }
    const labCount = selectedCourses.filter((c) => c.hasLab).length;
    if (labCount > 2) {
      score -= 15;
      warnings.push('Too many lab courses: Consider moving one to next semester');
    }
    if (overlappingCodes.size > 0) {
      score -= overlappingCodes.size * 10;
      warnings.push(`${overlappingCodes.size} course${overlappingCodes.size > 1 ? 's have' : ' has'} time conflicts`);
    }
    score = Math.max(0, Math.min(100, score));
    return {
      score,
      rationale: score >= 80 ? 'Well-balanced schedule' : score >= 60 ? 'Moderately challenging schedule' : 'Consider adjusting for better balance',
      warnings,
    };
  }, [selectedCourses, totalCredits, overlappingCodes]);

  // Persist helpers — merge API response with local data so meeting times aren't lost
  const persistAdd = async (course: Course): Promise<Course> => {
    if (!onCourseAdded) return course;
    try {
      const saved = await onCourseAdded(course);
      if (!saved) return course;
      // Merge: keep local meeting data if the API response has nulls
      return {
        ...saved,
        meetingDays: saved.meetingDays || course.meetingDays,
        meetingTime: saved.meetingTime || course.meetingTime,
        building: saved.building || course.building,
        room: saved.room || course.room,
        sectionNumber: saved.sectionNumber || course.sectionNumber,
        crn: saved.crn || course.crn,
        instructor: saved.instructor || course.instructor,
      };
    } catch (err) {
      console.error('Failed to save course:', err);
      return course;
    }
  };

  const handleAddCourse = (course: Course) => {
    if (selectedCourses.find((c) => c.code === course.code)) return;
    const sections = course.sections || [];
    if (sections.length > 1) {
      setSectionPickerCourse(course);
    } else if (sections.length === 1) {
      addCourseWithSection(course, sections[0]);
    } else {
      const planned = { ...course, status: 'planned' as const };
      setSelectedCourses((prev) => [...prev, planned]);
      persistAdd(planned).then((saved) => {
        setSelectedCourses((prev) => prev.map((c) => (c.code === saved.code ? saved : c)));
      });
    }
  };

  const addCourseWithSection = (course: Course, section: Section) => {
    if (selectedCourses.find((c) => c.code === course.code)) return;
    const planned: Course = {
      ...course,
      status: 'planned',
      sectionNumber: section.sectionNumber,
      crn: section.crn,
      instructor: section.instructor,
      meetingDays: section.meetingDays,
      meetingTime: section.meetingTime,
      building: section.building,
      room: section.room,
    };
    setSelectedCourses((prev) => [...prev, planned]);
    persistAdd(planned).then((saved) => {
      setSelectedCourses((prev) => prev.map((c) => (c.code === saved.code ? saved : c)));
    });
    setSectionPickerCourse(null);
  };

  const removeCourse = async (courseCode: string) => {
    const course = selectedCourses.find((c) => c.code === courseCode);
    setSelectedCourses((prev) => prev.filter((c) => c.code !== courseCode));
    if (course && onCourseRemoved) {
      try {
        await onCourseRemoved(course);
      } catch (err) {
        console.error('Failed to delete course:', err);
        setSelectedCourses((prev) => [...prev, course]);
      }
    }
  };

  // DnD handlers
  const handleDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current as { course: Course; sourceSemesterId: string } | undefined;
    if (!data) return;
    setActiveDragCourse(data.course);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { over } = event;
    const data = event.active.data.current as { course: Course; sourceSemesterId: string } | undefined;
    if (!data) { setActiveDragCourse(null); return; }

    if (over && String(over.id) === 'semester:planned' && data.sourceSemesterId === 'catalog') {
      handleAddCourse(data.course);
    }
    setActiveDragCourse(null);
  };

  // Filter available courses
  const unselectedCourses = availableCourses.filter((c) => !allPlannedCodes.has(c.code));

  const departments = useMemo(() => {
    return [...new Set(unselectedCourses.map((c) => c.dept))].filter(Boolean).sort();
  }, [unselectedCourses]);

  const filteredCourses = useMemo(() => {
    let courses = unselectedCourses;
    if (deptFilter !== 'all') {
      courses = courses.filter((c) => c.dept === deptFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      courses = courses.filter(
        (c) => c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q),
      );
    }
    // Filter out courses that would overlap with existing schedule
    if (hideOverlapping) {
      courses = courses.filter((c) => {
        // Check all sections — if any section doesn't overlap, keep the course
        const sections = c.sections || [];
        if (sections.length > 0) {
          return sections.some((s) => {
            const testCourse = { ...c, meetingDays: s.meetingDays, meetingTime: s.meetingTime };
            return !courseOverlapsWithAny(testCourse, selectedCourses);
          });
        }
        // No sections — check the course's own time
        return !courseOverlapsWithAny(c, selectedCourses);
      });
    }
    return courses;
  }, [unselectedCourses, deptFilter, searchQuery, hideOverlapping, selectedCourses]);

  // Group by dept for sidebar
  const groupedCatalog = useMemo(() => {
    const groups: Record<string, Course[]> = {};
    filteredCourses.forEach((c) => {
      if (!groups[c.dept]) groups[c.dept] = [];
      groups[c.dept].push(c);
    });
    return groups;
  }, [filteredCourses]);
  const sortedDepts = Object.keys(groupedCatalog).sort();

  const toggleDept = (dept: string) => {
    setExpandedDepts((prev) => {
      const next = new Set(prev);
      if (next.has(dept)) next.delete(dept);
      else next.add(dept);
      return next;
    });
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveDragCourse(null)}
    >
      <div className="flex gap-5" style={{ height: 'calc(100vh - 14rem)' }}>
        {/* ====== Catalog Sidebar ====== */}
        <div className="w-72 flex-shrink-0 border border-[#e8e4db] rounded bg-white flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-[#e8e4db] bg-[#f7f5f0] space-y-2.5">
            <h3
              className="text-[#115740] font-semibold text-sm"
              style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
            >
              Course Catalog
            </h3>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search courses..."
                className="w-full h-8 pl-9 pr-3 rounded border border-[#e8e4db] bg-white text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
              />
            </div>
            {/* Filters row */}
            <div className="flex items-center gap-2">
              <div className="flex flex-wrap gap-1 flex-1">
                <button
                  onClick={() => setDeptFilter('all')}
                  className={`px-2 py-0.5 text-[11px] rounded-full border transition-colors ${
                    deptFilter === 'all'
                      ? 'bg-[#115740] text-white border-[#115740]'
                      : 'border-[#e8e4db] text-gray-600 hover:bg-[#f7f5f0]'
                  }`}
                >
                  All
                </button>
                {departments.map((dept) => (
                  <button
                    key={dept}
                    onClick={() => setDeptFilter(dept === deptFilter ? 'all' : dept)}
                    className={`px-2 py-0.5 text-[11px] rounded-full border transition-colors ${
                      deptFilter === dept
                        ? 'bg-[#115740] text-white border-[#115740]'
                        : 'border-[#e8e4db] text-gray-600 hover:bg-[#f7f5f0]'
                    }`}
                  >
                    {dept}
                  </button>
                ))}
              </div>
            </div>
            {/* Hide overlapping toggle */}
            {selectedCourses.length > 0 && (
              <button
                onClick={() => setHideOverlapping(!hideOverlapping)}
                className={`w-full text-[11px] flex items-center justify-center gap-1.5 py-1.5 rounded border transition-colors ${
                  hideOverlapping
                    ? 'bg-[#115740] text-white border-[#115740]'
                    : 'border-[#e8e4db] text-gray-500 hover:bg-[#f7f5f0]'
                }`}
              >
                <Filter className="h-3 w-3" />
                {hideOverlapping ? 'Showing non-conflicting only' : 'Hide conflicting courses'}
              </button>
            )}
          </div>

          {/* Grouped course list */}
          <div className="flex-1 overflow-y-auto p-2">
            {sortedDepts.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-6">No courses match</p>
            )}
            {sortedDepts.map((dept) => {
              const courses = groupedCatalog[dept];
              const isExpanded = expandedDepts.has(dept);
              return (
                <div key={dept} className="mb-0.5">
                  <button
                    onClick={() => toggleDept(dept)}
                    className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded hover:bg-[#f7f5f0] transition-colors text-left"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                    )}
                    <span className="font-medium text-sm text-[#262626] flex-1">{dept}</span>
                    <span className="text-[11px] text-gray-400">{courses.length}</span>
                  </button>
                  {isExpanded && (
                    <div className="space-y-1 pl-1.5 pr-0.5 pb-1">
                      {courses.map((course, idx) => (
                        <TimelineCourseCard
                          key={`${course.code}-${idx}`}
                          course={course}
                          draggable
                          dragId={`catalog:${course.code}`}
                          dragData={{ course, sourceSemesterId: 'catalog' }}
                          onClick={() => handleAddCourse(course)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ====== Main Content: Score Bar + Weekly Calendar ====== */}
        <CalendarDropZone>
          {/* Score Bar */}
          <div className="border border-[#e8e4db] rounded bg-white flex-shrink-0 mb-3">
            <div className="px-5 py-3">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-3">
                  <span
                    className="text-base font-semibold text-[#115740]"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    Schedule Balance
                  </span>
                  <span className="text-xl font-bold text-[#115740]">
                    {scheduleScore.score}
                    <span className="text-sm font-normal text-gray-400">/100</span>
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">
                    <strong className="text-[#115740]">{totalCredits}</strong> credits
                  </span>
                  <span className="text-sm text-gray-600">
                    <strong className="text-[#115740]">{selectedCourses.length}</strong> courses
                  </span>
                  {overlappingCodes.size > 0 && (
                    <Badge variant="destructive" className="text-xs">
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      {overlappingCodes.size} conflict{overlappingCodes.size > 1 ? 's' : ''}
                    </Badge>
                  )}
                </div>
              </div>
              <div
                className="relative h-2.5 w-full rounded-full overflow-hidden"
                style={{ background: '#ede5cf', border: '1px solid #d4c9a8' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${Math.min(Math.max(scheduleScore.score, 0), 100)}%`,
                    background: 'linear-gradient(90deg, #B9975B, #d4b876)',
                  }}
                />
              </div>

              {scheduleScore.warnings.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {scheduleScore.warnings.map((w, i) => (
                    <span
                      key={i}
                      className="text-[11px] text-yellow-800 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded flex items-center gap-1"
                    >
                      <AlertTriangle className="h-2.5 w-2.5" />
                      {w}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Weekly Calendar + Course List sidebar */}
          <div className="flex-1 flex gap-3 min-h-0">
            {selectedCourses.length === 0 ? (
              <div className="flex-1 border-2 border-dashed border-[#e8e4db] rounded flex items-center justify-center">
                <div className="text-center text-gray-400">
                  <Clock className="h-10 w-10 mx-auto mb-3 text-[#e8e4db]" />
                  <p className="text-sm font-medium">Your weekly schedule is empty</p>
                  <p className="text-xs mt-1">Drag courses from the catalog or click to add them</p>
                </div>
              </div>
            ) : (
              <WeeklyCalendar
                courses={selectedCourses.filter((c) => getCourseSlots(c).length > 0)}
                overlappingCodes={overlappingCodes}
                onRemoveCourse={removeCourse}
              />
            )}

            {/* Right sidebar: all courses running total */}
            {selectedCourses.length > 0 && (
              <div className="w-48 flex-shrink-0 border border-[#e8e4db] rounded bg-white flex flex-col overflow-hidden">
                <div className="px-3 py-2 border-b border-[#e8e4db] bg-[#f7f5f0]">
                  <h4
                    className="text-[#115740] font-semibold text-xs"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    My Courses
                  </h4>
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    {selectedCourses.length} course{selectedCourses.length !== 1 ? 's' : ''} · {totalCredits} credits
                  </p>
                </div>
                <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
                  {selectedCourses.map((course, idx) => {
                    const hasTime = getCourseSlots(course).length > 0;
                    return (
                      <div
                        key={`${course.code}-${idx}`}
                        className={`flex items-center justify-between px-2 py-1.5 rounded border text-[11px] group ${
                          !hasTime
                            ? 'bg-[#B9975B]/10 border-[#B9975B]/30'
                            : 'bg-white border-[#e8e4db]'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-[#115740] truncate">{course.code}</div>
                          <div className="text-[10px] text-gray-400 truncate">
                            {hasTime
                              ? `${course.meetingDays} ${course.meetingTime}`
                              : 'No time assigned'}
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0 ml-1">
                          <span className="text-[10px] text-gray-400">{course.credits}cr</span>
                          <button
                            onClick={() => removeCourse(course.code)}
                            className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 text-gray-300 hover:text-red-500 transition-all"
                          >
                            <X className="h-2.5 w-2.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </CalendarDropZone>

        {/* DragOverlay */}
        <DragOverlay dropAnimation={null}>
          {activeDragCourse ? (
            <div className="shadow-xl rotate-2 scale-105 opacity-90">
              <TimelineCourseCard course={activeDragCourse} />
            </div>
          ) : null}
        </DragOverlay>
      </div>

      {/* Section Picker Modal */}
      {sectionPickerCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col overflow-hidden">
            <div className="bg-[#115740] px-6 py-4 rounded-t-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h3
                    className="text-white font-semibold text-lg"
                    style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
                  >
                    Select a Section
                  </h3>
                  <p className="text-white/70 text-sm mt-0.5">
                    {sectionPickerCourse.code} &mdash; {sectionPickerCourse.title}
                  </p>
                </div>
                <button
                  onClick={() => setSectionPickerCourse(null)}
                  className="p-1.5 hover:bg-white/20 rounded transition-colors"
                >
                  <X className="h-4 w-4 text-white/80" />
                </button>
              </div>
            </div>
            <div className="p-4 overflow-y-auto space-y-3 bg-[#f7f5f0]">
              {(sectionPickerCourse.sections || []).map((section) => {
                const seatPercent =
                  section.capacity > 0 ? (section.enrolled / section.capacity) * 100 : 0;
                const isFull = section.available <= 0;
                const isLow = !isFull && section.available <= 3;
                // Check if this section would conflict
                const wouldConflict = courseOverlapsWithAny(
                  { ...sectionPickerCourse, meetingDays: section.meetingDays, meetingTime: section.meetingTime },
                  selectedCourses,
                );
                return (
                  <button
                    key={section.crn}
                    onClick={() => addCourseWithSection(sectionPickerCourse, section)}
                    className={`w-full text-left p-4 rounded-lg border-2 bg-white transition-all hover:shadow-md ${
                      isFull
                        ? 'border-red-200 opacity-60 hover:border-red-300'
                        : wouldConflict
                        ? 'border-red-300 hover:border-red-400'
                        : 'border-[#e8e4db] hover:border-[#B9975B]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-semibold text-[#115740] text-base">
                        {sectionPickerCourse.code} - {section.sectionNumber}
                      </span>
                      <div className="flex items-center gap-2">
                        {wouldConflict && !isFull && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                            Time conflict
                          </span>
                        )}
                        <span
                          className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                            isFull
                              ? 'bg-red-100 text-red-700'
                              : isLow
                              ? 'bg-[#B9975B]/20 text-[#8a6e3b]'
                              : 'bg-[#115740]/10 text-[#115740]'
                          }`}
                        >
                          {isFull ? 'Full' : `${section.available} seats open`}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2 text-sm">
                      {section.instructor && (
                        <div className="flex items-center gap-2.5">
                          <User className="h-4 w-4 text-[#B9975B]" />
                          <span className="text-[#262626] font-medium">{section.instructor}</span>
                        </div>
                      )}
                      {section.meetingDays && section.meetingTime && (
                        <div className="flex items-center gap-2.5">
                          <Clock className="h-4 w-4 text-[#115740]" />
                          <span className="text-[#262626]">
                            {section.meetingDays} {section.meetingTime}
                          </span>
                        </div>
                      )}
                      {(section.building || section.room) && (
                        <div className="flex items-center gap-2.5">
                          <MapPin className="h-4 w-4 text-[#115740]" />
                          <span className="text-[#262626]">
                            {[section.building, section.room].filter(Boolean).join(' ')}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="mt-3 pt-3 border-t border-[#e8e4db]">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs text-gray-500">CRN: {section.crn}</span>
                        <span className="text-xs text-gray-500">
                          {section.enrolled}/{section.capacity} enrolled
                        </span>
                      </div>
                      <div className="relative h-1.5 w-full rounded-full overflow-hidden bg-[#ede5cf]">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(seatPercent, 100)}%`,
                            background: isFull
                              ? '#ef4444'
                              : isLow
                              ? '#B9975B'
                              : 'linear-gradient(90deg, #115740, #1a7a5a)',
                          }}
                        />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </DndContext>
  );
}
