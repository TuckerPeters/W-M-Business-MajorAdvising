'use client';

import { useState, useCallback, useMemo } from 'react';
import { X, ChevronLeft, ChevronRight, Search, Plus, Trash2, Check } from 'lucide-react';
import { createUserWithEmailAndPassword, updateProfile } from 'firebase/auth';
import { getAuthInstance } from '@/lib/firebase';
import Input from '@/components/ui/Input';
import { searchCourses } from '@/lib/api-client';

interface StudentOnboardingProps {
  studentName: string;
  studentEmail: string;
  studentPassword?: string;
  onClose: () => void;
  onComplete: () => void;
}

interface CourseEntry {
  code: string;
  title: string;
  credits: number;
  grade?: string;
  manual?: boolean;
  fromAP?: boolean;
}

const STEPS = ['Major', 'AP/IB Credits', 'Past Courses', 'Current Courses'] as const;

// Majors & concentrations from backend curriculum_scraper.py
// (Mason School of Business Majors Curriculum Guide 2025-2026)
const MAJORS = [
  'Undeclared',
  'Accounting',
  'Business Analytics - Data Science',
  'Business Analytics - Supply Chain',
  'Finance',
  'Marketing',
];

const CONCENTRATIONS = [
  'Accounting',
  'Business Analytics',
  'Consulting',
  'Finance',
  'Management & Organizational Leadership',
  'Innovation & Entrepreneurship',
  'Supply Chain Analytics',
  'Marketing',
  'Sustainability',
];

const GRADES = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'P', 'W'];

/* ================================================================
   AP & IB exam → W&M course equivalents
   Source: AP_Credits_Info.pdf (Pre-Matriculation Test Credits 2025-2026)
   Filtered: entries with "Departmental Review" are excluded
   ================================================================ */

interface ExamCredit {
  exam: string;
  type: 'AP' | 'IB';
  score: string;
  courses: { code: string; credits: number }[];
}

const EXAM_CREDITS: ExamCredit[] = [
  // ===== AP EXAMS =====
  { exam: 'African American Studies', type: 'AP', score: '3-5', courses: [{ code: 'AFST 1XX', credits: 3 }] },
  { exam: 'Art History', type: 'AP', score: '5', courses: [{ code: 'ARTH 251', credits: 3 }, { code: 'ARTH 252', credits: 3 }] },
  { exam: 'Biology', type: 'AP', score: '5', courses: [{ code: 'BIOL 203', credits: 3 }, { code: 'BIOL 203L', credits: 1 }, { code: 'BIOL 204', credits: 3 }, { code: 'BIOL 204L', credits: 1 }] },
  { exam: 'Calculus AB', type: 'AP', score: '4-5', courses: [{ code: 'MATH 111', credits: 4 }] },
  { exam: 'Calculus BC', type: 'AP', score: '4-5', courses: [{ code: 'MATH 111', credits: 4 }, { code: 'MATH 112', credits: 4 }] },
  { exam: 'Calculus BC', type: 'AP', score: '3', courses: [{ code: 'MATH 111', credits: 4 }] },
  { exam: 'Pre-Calculus', type: 'AP', score: '3-5', courses: [{ code: 'MATH 103', credits: 3 }] },
  { exam: 'Chemistry', type: 'AP', score: '5', courses: [{ code: 'CHEM 103', credits: 3 }, { code: 'CHEM 103L', credits: 1 }, { code: 'CHEM Elective', credits: 3 }, { code: 'CHEM 254', credits: 1 }] },
  { exam: 'Chemistry', type: 'AP', score: '4', courses: [{ code: 'CHEM 103', credits: 3 }, { code: 'CHEM 103L', credits: 1 }] },
  { exam: 'Chinese Language', type: 'AP', score: '5', courses: [{ code: 'CHIN 205', credits: 4 }, { code: 'CHIN 206', credits: 4 }] },
  { exam: 'Chinese Language', type: 'AP', score: '4', courses: [{ code: 'CHIN 205', credits: 4 }] },
  { exam: 'Chinese Language', type: 'AP', score: '3', courses: [{ code: 'CHIN 202', credits: 4 }] },
  { exam: 'Comparative Government & Politics', type: 'AP', score: '4-5', courses: [{ code: 'GOVT 203', credits: 3 }] },
  { exam: 'Computer Science A', type: 'AP', score: '4-5', courses: [{ code: 'CSCI 141', credits: 4 }] },
  { exam: 'Computer Science Principles', type: 'AP', score: '4-5', courses: [{ code: 'CSCI 131', credits: 3 }] },
  { exam: 'English Literature & Composition', type: 'AP', score: '3-5', courses: [{ code: 'ENGL 1XX', credits: 3 }] },
  { exam: 'English Language & Composition', type: 'AP', score: '3-5', courses: [{ code: 'WRIT 101', credits: 3 }] },
  { exam: 'Environmental Science', type: 'AP', score: '5', courses: [{ code: 'ENSP 101', credits: 4 }] },
  { exam: 'European History', type: 'AP', score: '5', courses: [{ code: 'HIST 111', credits: 3 }, { code: 'HIST 112', credits: 3 }] },
  { exam: 'French Language', type: 'AP', score: '5', courses: [{ code: 'FREN 206', credits: 3 }, { code: 'FREN 210', credits: 3 }] },
  { exam: 'French Language', type: 'AP', score: '4', courses: [{ code: 'FREN 206', credits: 3 }] },
  { exam: 'French Language', type: 'AP', score: '3', courses: [{ code: 'FREN 206', credits: 3 }] },
  { exam: 'German Language', type: 'AP', score: '5', courses: [{ code: 'GRMN 210', credits: 3 }, { code: 'GRMN 210', credits: 3 }] },
  { exam: 'German Language', type: 'AP', score: '4', courses: [{ code: 'GRMN 210', credits: 3 }] },
  { exam: 'German Language', type: 'AP', score: '3', courses: [{ code: 'GRMN 202', credits: 3 }] },
  { exam: 'Human Geography', type: 'AP', score: '4-5', courses: [{ code: 'HIST 1XX', credits: 3 }] },
  { exam: 'Japanese Language & Culture', type: 'AP', score: '5', courses: [{ code: 'JAPN 202', credits: 4 }] },
  { exam: 'Japanese Language & Culture', type: 'AP', score: '4', courses: [{ code: 'JAPN 1XX', credits: 3 }] },
  { exam: 'Latin Language', type: 'AP', score: '5', courses: [{ code: 'LATN 201', credits: 3 }, { code: 'LATN 202', credits: 3 }] },
  { exam: 'Latin Language', type: 'AP', score: '4', courses: [{ code: 'LATN 102', credits: 4 }] },
  { exam: 'Latin Language', type: 'AP', score: '3', courses: [{ code: 'LATN 101', credits: 4 }] },
  { exam: 'Macroeconomics', type: 'AP', score: '4-5', courses: [{ code: 'ECON 102', credits: 3 }] },
  { exam: 'Microeconomics', type: 'AP', score: '4-5', courses: [{ code: 'ECON 101', credits: 3 }] },
  { exam: 'Music Theory', type: 'AP', score: '5', courses: [{ code: 'MUSC 201', credits: 3 }, { code: 'MUSC 201L', credits: 1 }] },
  { exam: 'Physics 1', type: 'AP', score: '5', courses: [{ code: 'PHYS 107', credits: 3 }, { code: 'PHYS 107L', credits: 1 }] },
  { exam: 'Physics 2', type: 'AP', score: '5', courses: [{ code: 'PHYS 108', credits: 3 }, { code: 'PHYS 108L', credits: 1 }] },
  { exam: 'Physics C: Mechanics', type: 'AP', score: '5', courses: [{ code: 'PHYS 101', credits: 3 }, { code: 'PHYS 101L', credits: 1 }] },
  { exam: 'Physics C: E&M', type: 'AP', score: '5', courses: [{ code: 'PHYS 102', credits: 3 }, { code: 'PHYS 102L', credits: 1 }] },
  { exam: 'Psychology', type: 'AP', score: '5', courses: [{ code: 'PSYC 201', credits: 3 }, { code: 'PSYC 202', credits: 3 }] },
  { exam: 'Spanish Language & Culture', type: 'AP', score: '5', courses: [{ code: 'HISP 206', credits: 3 }, { code: 'HISP 207', credits: 3 }] },
  { exam: 'Spanish Language & Culture', type: 'AP', score: '4', courses: [{ code: 'HISP 206', credits: 3 }] },
  { exam: 'Spanish Language & Culture', type: 'AP', score: '3', courses: [{ code: 'HISP 202', credits: 3 }] },
  { exam: 'Spanish Literature & Culture', type: 'AP', score: '5', courses: [{ code: 'HISP 207', credits: 3 }, { code: 'HISP 208', credits: 3 }] },
  { exam: 'Spanish Literature & Culture', type: 'AP', score: '4', courses: [{ code: 'HISP 207', credits: 3 }] },
  { exam: 'Spanish Literature & Culture', type: 'AP', score: '3', courses: [{ code: 'HISP 202', credits: 3 }] },
  { exam: 'Statistics', type: 'AP', score: '4-5', courses: [{ code: 'MATH 106', credits: 3 }] },
  { exam: 'US Government & Politics', type: 'AP', score: '4-5', courses: [{ code: 'GOVT 201', credits: 3 }] },
  { exam: 'US History', type: 'AP', score: '5', courses: [{ code: 'HIST 121', credits: 3 }, { code: 'HIST 122', credits: 3 }] },
  { exam: 'World History', type: 'AP', score: '5', courses: [{ code: 'HIST 1XX', credits: 3 }, { code: 'HIST 192', credits: 3 }] },

  // ===== IB EXAMS =====
  { exam: 'Arabic B (SL)', type: 'IB', score: '5-7', courses: [{ code: 'ARAB 201', credits: 3 }] },
  { exam: 'Arabic B (HL)', type: 'IB', score: '4-7', courses: [{ code: 'ARAB 202', credits: 3 }] },
  { exam: 'Biology (HL)', type: 'IB', score: '5-7', courses: [{ code: 'BIOL Elective', credits: 4 }] },
  { exam: 'Chemistry (SL)', type: 'IB', score: '7', courses: [{ code: 'CHEM 103', credits: 3 }, { code: 'CHEM 103L', credits: 1 }] },
  { exam: 'Chemistry (HL)', type: 'IB', score: '6-7', courses: [{ code: 'CHEM 103', credits: 3 }, { code: 'CHEM 103L', credits: 1 }, { code: 'CHEM Elective', credits: 3 }, { code: 'CHEM 254', credits: 1 }] },
  { exam: 'Chemistry (HL)', type: 'IB', score: '5', courses: [{ code: 'CHEM 103', credits: 3 }, { code: 'CHEM 103L', credits: 1 }] },
  { exam: 'Chinese - Mandarin B (SL)', type: 'IB', score: '6-7', courses: [{ code: 'CHIN 205', credits: 4 }] },
  { exam: 'Chinese - Mandarin B (SL)', type: 'IB', score: '5', courses: [{ code: 'CHIN 202', credits: 3 }] },
  { exam: 'Chinese - Mandarin B (HL)', type: 'IB', score: '6-7', courses: [{ code: 'CHIN 205', credits: 4 }, { code: 'CHIN 206', credits: 4 }] },
  { exam: 'Chinese - Mandarin B (HL)', type: 'IB', score: '5', courses: [{ code: 'CHIN 205', credits: 4 }] },
  { exam: 'Chinese - Mandarin B (HL)', type: 'IB', score: '4', courses: [{ code: 'CHIN 202', credits: 3 }] },
  { exam: 'Computer Science (SL)', type: 'IB', score: '6-7', courses: [{ code: 'CSCI 141', credits: 4 }] },
  { exam: 'Computer Science (HL)', type: 'IB', score: '6-7', courses: [{ code: 'CSCI 141', credits: 4 }, { code: 'CSCI 241', credits: 3 }] },
  { exam: 'Computer Science (HL)', type: 'IB', score: '5', courses: [{ code: 'CSCI 141', credits: 4 }] },
  { exam: 'Dance (SL)', type: 'IB', score: '5-7', courses: [{ code: 'DANC 155', credits: 1 }] },
  { exam: 'Dance (HL)', type: 'IB', score: '4-7', courses: [{ code: 'DANC 155', credits: 1 }] },
  { exam: 'Economics (HL)', type: 'IB', score: '6-7', courses: [{ code: 'ECON 101', credits: 3 }, { code: 'ECON 102', credits: 3 }] },
  { exam: 'English Literature (SL)', type: 'IB', score: '5-7', courses: [{ code: 'WRIT 101', credits: 3 }] },
  { exam: 'English Literature (HL)', type: 'IB', score: '4-7', courses: [{ code: 'ENGL 1XX', credits: 3 }] },
  { exam: 'English Language and Literature (SL)', type: 'IB', score: '5-7', courses: [{ code: 'WRIT 101', credits: 3 }] },
  { exam: 'English Language and Literature (HL)', type: 'IB', score: '4-7', courses: [{ code: 'ENGL 1XX', credits: 3 }] },
  { exam: 'Environmental Systems and Societies (SL)', type: 'IB', score: '6-7', courses: [{ code: 'ENSP 101', credits: 4 }] },
  { exam: 'Film (SL)', type: 'IB', score: '5-7', courses: [{ code: 'FMST 1XX', credits: 3 }] },
  { exam: 'Film (HL)', type: 'IB', score: '4-7', courses: [{ code: 'FMST 1XX', credits: 3 }] },
  { exam: 'French B (SL)', type: 'IB', score: '6-7', courses: [{ code: 'FREN 1XX', credits: 3 }] },
  { exam: 'French B (HL)', type: 'IB', score: '6-7', courses: [{ code: 'FREN 206', credits: 3 }, { code: 'FREN 210', credits: 3 }] },
  { exam: 'French B (HL)', type: 'IB', score: '5', courses: [{ code: 'FREN 206', credits: 3 }] },
  { exam: 'German B (HL)', type: 'IB', score: '6-7', courses: [{ code: 'GRMN 210', credits: 3 }, { code: 'GRMN 210', credits: 3 }] },
  { exam: 'German B (HL)', type: 'IB', score: '5', courses: [{ code: 'GRMN 210', credits: 3 }] },
  { exam: 'Global Politics (HL)', type: 'IB', score: '6-7', courses: [{ code: 'GOVT 204', credits: 3 }] },
  { exam: 'Greek (SL)', type: 'IB', score: '4-7', courses: [{ code: 'GREK 102', credits: 4 }] },
  { exam: 'Greek (HL)', type: 'IB', score: '6-7', courses: [{ code: 'GREK 201', credits: 3 }, { code: 'GREK 202', credits: 3 }] },
  { exam: 'Greek (HL)', type: 'IB', score: '4-5', courses: [{ code: 'GREK 102', credits: 4 }] },
  { exam: 'History: Africa and the Middle East (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HIST Elective', credits: 6 }] },
  { exam: 'History: Americas (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HIST 122', credits: 3 }, { code: 'HIST Elective', credits: 3 }] },
  { exam: 'History: Europe (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HIST 112', credits: 3 }, { code: 'HIST Elective', credits: 3 }] },
  { exam: 'History: SE Asia/Oceania (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HIST Elective', credits: 6 }] },
  { exam: 'History: World (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HIST 192', credits: 3 }, { code: 'HIST Elective', credits: 3 }] },
  { exam: 'Latin (SL)', type: 'IB', score: '5-7', courses: [{ code: 'LATN 102', credits: 4 }] },
  { exam: 'Latin (HL)', type: 'IB', score: '6-7', courses: [{ code: 'LATN 201', credits: 3 }, { code: 'LATN 202', credits: 3 }] },
  { exam: 'Latin (HL)', type: 'IB', score: '4-5', courses: [{ code: 'LATN 102', credits: 4 }] },
  { exam: 'Literature & Performance (SL)', type: 'IB', score: '5-7', courses: [{ code: 'ENGL 1XX', credits: 3 }] },
  { exam: 'Japanese B (HL)', type: 'IB', score: '7', courses: [{ code: 'JAPN 202', credits: 4 }] },
  { exam: 'Japanese B (HL)', type: 'IB', score: '6', courses: [{ code: 'JAPN 1XX', credits: 3 }] },
  { exam: 'Japanese B (HL)', type: 'IB', score: '5', courses: [{ code: 'JAPN 1XX', credits: 3 }] },
  { exam: 'Mathematics (HL)', type: 'IB', score: '7', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }, { code: 'MATH 112', credits: 4 }] },
  { exam: 'Mathematics (HL)', type: 'IB', score: '6', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }] },
  { exam: 'Mathematics (HL)', type: 'IB', score: '5', courses: [{ code: 'MATH 106', credits: 3 }] },
  { exam: 'Mathematics: Analysis (HL)', type: 'IB', score: '7', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }, { code: 'MATH 112', credits: 4 }] },
  { exam: 'Mathematics: Analysis (HL)', type: 'IB', score: '6', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }] },
  { exam: 'Mathematics: Analysis (HL)', type: 'IB', score: '5', courses: [{ code: 'MATH 106', credits: 3 }] },
  { exam: 'Mathematics: Applications (HL)', type: 'IB', score: '7', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 108', credits: 4 }] },
  { exam: 'Mathematics: Applications (HL)', type: 'IB', score: '6', courses: [{ code: 'MATH 106', credits: 3 }] },
  { exam: 'Mathematics: Further (HL)', type: 'IB', score: '7', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }, { code: 'MATH 112', credits: 4 }] },
  { exam: 'Mathematics: Further (HL)', type: 'IB', score: '6', courses: [{ code: 'MATH 106', credits: 3 }, { code: 'MATH 111', credits: 4 }] },
  { exam: 'Mathematics: Further (HL)', type: 'IB', score: '5', courses: [{ code: 'MATH 106', credits: 3 }] },
  { exam: 'Philosophy (SL)', type: 'IB', score: '5', courses: [{ code: 'PHIL 2XX', credits: 3 }] },
  { exam: 'Philosophy (HL)', type: 'IB', score: '4-7', courses: [{ code: 'PHIL 2XX', credits: 3 }] },
  { exam: 'Physics (HL)', type: 'IB', score: '6-7', courses: [{ code: 'PHYS 107', credits: 3 }, { code: 'PHYS 107L', credits: 1 }, { code: 'PHYS 108', credits: 3 }, { code: 'PHYS 108L', credits: 1 }] },
  { exam: 'Psychology (HL)', type: 'IB', score: '6-7', courses: [{ code: 'PSYC 201', credits: 3 }, { code: 'PSYC 202', credits: 3 }] },
  { exam: 'Russian B (SL)', type: 'IB', score: '6-7', courses: [{ code: 'RUSN 102', credits: 3 }] },
  { exam: 'Russian B (HL)', type: 'IB', score: '6-7', courses: [{ code: 'RUSN 202', credits: 3 }] },
  { exam: 'Social & Cultural Anthropology (SL)', type: 'IB', score: '5-7', courses: [{ code: 'ANTH 350', credits: 3 }] },
  { exam: 'Social & Cultural Anthropology (HL)', type: 'IB', score: '4-7', courses: [{ code: 'ANTH 350', credits: 3 }] },
  { exam: 'Spanish B (SL)', type: 'IB', score: '6-7', courses: [{ code: 'HISP 206', credits: 3 }] },
  { exam: 'Spanish B (SL)', type: 'IB', score: '5', courses: [{ code: 'HISP 1XX', credits: 3 }] },
  { exam: 'Spanish B (HL)', type: 'IB', score: '6-7', courses: [{ code: 'HISP 207', credits: 3 }, { code: 'HISP 206', credits: 3 }] },
  { exam: 'Spanish B (HL)', type: 'IB', score: '5', courses: [{ code: 'HISP 206', credits: 3 }] },
  { exam: 'Spanish B (HL)', type: 'IB', score: '4', courses: [{ code: 'HISP 1XX', credits: 3 }] },
  { exam: 'Theatre (SL)', type: 'IB', score: '5-7', courses: [{ code: 'THEA 411', credits: 2 }] },
  { exam: 'Theatre (HL)', type: 'IB', score: '4-7', courses: [{ code: 'THEA 411', credits: 3 }] },
  { exam: 'World Religions (SL)', type: 'IB', score: '5-7', courses: [{ code: 'RELG 208', credits: 3 }] },
];

/* ================================================================
   Score matching helpers
   ================================================================ */

// Get unique exam names for the checklist
function getUniqueExamNames(type: 'AP' | 'IB'): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const entry of EXAM_CREDITS) {
    if (entry.type === type && !seen.has(entry.exam)) {
      seen.add(entry.exam);
      result.push(entry.exam);
    }
  }
  return result;
}

// Parse score range like '3-5' → { min: 3, max: 5 }
function parseScoreRange(score: string): { min: number; max: number } {
  const parts = score.split('-').map(Number);
  return { min: parts[0], max: parts[parts.length - 1] };
}

// Find the best matching entry for a student's score
function findMatchingEntry(type: 'AP' | 'IB', examName: string, studentScore: number): ExamCredit | null {
  const entries = EXAM_CREDITS.filter((e) => e.type === type && e.exam === examName);
  let best: ExamCredit | null = null;
  let bestCredits = 0;
  for (const entry of entries) {
    const { min, max } = parseScoreRange(entry.score);
    if (studentScore >= min && studentScore <= max) {
      const total = entry.courses.reduce((s, c) => s + c.credits, 0);
      if (total > bestCredits) {
        best = entry;
        bestCredits = total;
      }
    }
  }
  return best;
}

// Get minimum required score for any credit on this exam
function getMinScore(type: 'AP' | 'IB', examName: string): number {
  const entries = EXAM_CREDITS.filter((e) => e.type === type && e.exam === examName);
  let min = Infinity;
  for (const entry of entries) {
    const { min: lo } = parseScoreRange(entry.score);
    if (lo < min) min = lo;
  }
  return min;
}

const AP_EXAM_NAMES = getUniqueExamNames('AP');
const IB_EXAM_NAMES = getUniqueExamNames('IB');

const serif = 'Georgia, "Times New Roman", serif';

export default function StudentOnboarding({
  studentName,
  studentEmail,
  studentPassword,
  onClose,
  onComplete,
}: StudentOnboardingProps) {
  const [step, setStep] = useState(0);

  // Step 1
  const [major, setMajor] = useState('');
  const [concentration, setConcentration] = useState('');
  const [minor, setMinor] = useState('');
  const [classYear, setClassYear] = useState('');

  // Step 2: exam name → student score (0 = selected but no score yet)
  const [examScores, setExamScores] = useState<Record<string, number>>({});
  const [additionalCredits, setAdditionalCredits] = useState(0);
  const [examTab, setExamTab] = useState<'AP' | 'IB'>('AP');

  // Step 3
  const [completedCourses, setCompletedCourses] = useState<CourseEntry[]>([]);
  const [pastSearchQuery, setPastSearchQuery] = useState('');
  const [pastSearchResults, setPastSearchResults] = useState<{ code: string; title: string; credits: number }[]>([]);
  const [pastSearching, setPastSearching] = useState(false);
  const [showManualPast, setShowManualPast] = useState(false);
  const [manualCode, setManualCode] = useState('');
  const [manualTitle, setManualTitle] = useState('');
  const [manualCredits, setManualCredits] = useState('');
  const [manualGrade, setManualGrade] = useState('');

  // Step 4
  const [enrolledCourses, setEnrolledCourses] = useState<CourseEntry[]>([]);
  const [currentSearchQuery, setCurrentSearchQuery] = useState('');
  const [currentSearchResults, setCurrentSearchResults] = useState<{ code: string; title: string; credits: number }[]>([]);
  const [currentSearching, setCurrentSearching] = useState(false);

  const [submitting, setSubmitting] = useState(false);

  // Derive courses from exam scores
  const examCourses = useMemo((): CourseEntry[] => {
    const courses: CourseEntry[] = [];
    const addedCodes = new Set<string>();
    for (const [key, score] of Object.entries(examScores)) {
      if (!score) continue; // no score selected yet
      const [type, ...nameParts] = key.split('|');
      const examName = nameParts.join('|');
      const entry = findMatchingEntry(type as 'AP' | 'IB', examName, score);
      if (!entry) continue; // score too low
      for (const c of entry.courses) {
        if (!addedCodes.has(c.code)) {
          addedCodes.add(c.code);
          courses.push({
            code: c.code,
            title: `${entry.type} Credit: ${entry.exam}`,
            credits: c.credits,
            grade: entry.type,
            fromAP: true,
          });
        }
      }
    }
    return courses;
  }, [examScores]);

  // Merge exam courses with manually added courses
  const allCompleted = useMemo(() => {
    const manual = completedCourses.filter((c) => !c.fromAP);
    return [...examCourses, ...manual];
  }, [examCourses, completedCourses]);

  const totalExamCredits = examCourses.reduce((sum, c) => sum + c.credits, 0) + additionalCredits;

  const toggleExam = (type: 'AP' | 'IB', examName: string) => {
    const key = `${type}|${examName}`;
    setExamScores((prev) => {
      const next = { ...prev };
      if (key in next) {
        delete next[key];
      } else {
        next[key] = 0; // selected, awaiting score
      }
      return next;
    });
  };

  const setExamScore = (type: 'AP' | 'IB', examName: string, score: number) => {
    const key = `${type}|${examName}`;
    setExamScores((prev) => ({ ...prev, [key]: score }));
  };

  const handleSearch = useCallback(
    async (query: string, target: 'past' | 'current') => {
      const setResults = target === 'past' ? setPastSearchResults : setCurrentSearchResults;
      const setSearching = target === 'past' ? setPastSearching : setCurrentSearching;
      if (query.length < 2) { setResults([]); return; }
      setSearching(true);
      try {
        const results = await searchCourses(query);
        setResults(results.map((c: any) => ({ code: c.code, title: c.title, credits: c.credits })));
      } catch { setResults([]); } finally { setSearching(false); }
    },
    []
  );

  const addCompletedCourse = (course: { code: string; title: string; credits: number }) => {
    if (completedCourses.some((c) => c.code === course.code)) return;
    setCompletedCourses((prev) => [...prev, { ...course, grade: '' }]);
    setPastSearchQuery('');
    setPastSearchResults([]);
  };

  const addManualCourse = () => {
    if (!manualCode.trim()) return;
    setCompletedCourses((prev) => [
      ...prev,
      {
        code: manualCode.trim().toUpperCase(),
        title: manualTitle.trim() || manualCode.trim().toUpperCase(),
        credits: parseInt(manualCredits) || 3,
        grade: manualGrade || '',
        manual: true,
      },
    ]);
    setManualCode('');
    setManualTitle('');
    setManualCredits('');
    setManualGrade('');
    setShowManualPast(false);
  };

  const addEnrolledCourse = (course: { code: string; title: string; credits: number }) => {
    if (enrolledCourses.some((c) => c.code === course.code)) return;
    setEnrolledCourses((prev) => [...prev, { ...course }]);
    setCurrentSearchQuery('');
    setCurrentSearchResults([]);
  };

  const handleComplete = async () => {
    setSubmitting(true);
    try {
      // If email/password signup, create the Firebase account now (deferred until onboarding is done)
      if (studentPassword) {
        const auth = getAuthInstance();
        if (auth) {
          const userCredential = await createUserWithEmailAndPassword(auth, studentEmail, studentPassword);
          await updateProfile(userCredential.user, { displayName: studentName });
        }
      }
      onComplete();
    } catch {
      // Account creation failed — still complete onboarding flow
      onComplete();
    }
  };

  const examNameList = examTab === 'AP' ? AP_EXAM_NAMES : IB_EXAM_NAMES;
  const scoreOptions = examTab === 'AP' ? [1, 2, 3, 4, 5] : [1, 2, 3, 4, 5, 6, 7];

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-[60] transition-opacity" onClick={onClose} />

      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 pointer-events-none">
        <div
          className="relative bg-white w-full max-w-[540px] max-h-[90vh] shadow-2xl pointer-events-auto border-t-4 border-[#B9975B] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={onClose} className="absolute top-4 right-4 p-1.5 hover:bg-gray-100 rounded transition-colors z-10">
            <X className="h-5 w-5 text-gray-500" />
          </button>

          {/* Header */}
          <div className="px-8 pt-6 pb-4 flex-shrink-0">
            <h2 className="text-[#115740] text-xl mb-1" style={{ fontFamily: serif }}>
              Welcome, {studentName || 'Student'}
            </h2>
            <p className="text-sm text-gray-500">
              Let&apos;s set up your academic profile. This helps us provide personalized advising.
            </p>
          </div>

          {/* Step indicator */}
          <div className="px-8 pb-4 flex-shrink-0">
            <div className="flex items-center gap-1">
              {STEPS.map((label, i) => (
                <div key={label} className="flex items-center flex-1">
                  <div className="flex items-center gap-1.5 flex-1">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                      i < step ? 'bg-[#115740] text-white' : i === step ? 'bg-[#B9975B] text-white' : 'bg-gray-200 text-gray-500'
                    }`}>
                      {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
                    </div>
                    <span className={`text-xs hidden sm:block ${i === step ? 'text-[#115740] font-semibold' : 'text-gray-400'}`}>
                      {label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && <div className={`h-px flex-1 mx-1 ${i < step ? 'bg-[#115740]' : 'bg-gray-200'}`} />}
                </div>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-8 pb-2 min-h-0">

            {/* ===== Step 1: Major & Minor ===== */}
            {step === 0 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1.5" style={{ fontFamily: serif }}>Intended Major</label>
                  <select
                    value={major}
                    onChange={(e) => setMajor(e.target.value)}
                    className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                  >
                    <option value="" disabled>Select a major...</option>
                    {MAJORS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">Business majors declare after completing 39+ credits with required courses.</p>
                </div>

                <div>
                  <label className="block text-sm text-gray-600 mb-1.5" style={{ fontFamily: serif }}>
                    Concentration <span className="text-gray-400">(optional)</span>
                  </label>
                  <select
                    value={concentration}
                    onChange={(e) => setConcentration(e.target.value)}
                    className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                  >
                    <option value="">None</option>
                    {CONCENTRATIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-600 mb-1.5" style={{ fontFamily: serif }}>
                    Minor <span className="text-gray-400">(optional)</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="e.g. Computer Science, Psychology"
                    value={minor}
                    onChange={(e) => setMinor(e.target.value)}
                    className="border-gray-300 focus-visible:ring-[#115740]"
                  />
                </div>

                <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2" style={{ fontFamily: serif }}>Class Year</p>
                  <select
                    value={classYear}
                    onChange={(e) => setClassYear(e.target.value)}
                    className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white"
                  >
                    <option value="" disabled>Select your class year...</option>
                    <option value="2025">2025 (Senior)</option>
                    <option value="2026">2026 (Junior)</option>
                    <option value="2027">2027 (Sophomore)</option>
                    <option value="2028">2028 (Freshman)</option>
                    <option value="2029">2029 (Incoming)</option>
                  </select>
                </div>
              </div>
            )}

            {/* ===== Step 2: AP/IB Credits ===== */}
            {step === 1 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Select exams and enter your score. Courses are awarded based on W&amp;M&apos;s credit policy.
                </p>

                <div className="flex border-b border-gray-200">
                  {(['AP', 'IB'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setExamTab(t)}
                      className={`flex-1 py-2 text-sm font-medium transition-colors ${
                        examTab === t ? 'text-[#115740] border-b-2 border-[#115740]' : 'text-gray-400 hover:text-gray-600'
                      }`}
                    >
                      {t} Exams ({(t === 'AP' ? AP_EXAM_NAMES : IB_EXAM_NAMES).length})
                    </button>
                  ))}
                </div>

                <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
                  {examNameList.map((examName) => {
                    const key = `${examTab}|${examName}`;
                    const isSelected = key in examScores;
                    const studentScore = examScores[key] || 0;
                    const minRequired = getMinScore(examTab, examName);
                    const matched = studentScore ? findMatchingEntry(examTab, examName, studentScore) : null;
                    const noCredit = studentScore > 0 && !matched;

                    return (
                      <div key={key}>
                        <label
                          className={`flex items-center gap-3 px-3 py-2.5 rounded-t border cursor-pointer transition-colors ${
                            isSelected ? 'border-[#115740] bg-[#115740]/5 border-b-0' : 'border-gray-200 hover:bg-gray-50 rounded-b'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleExam(examTab, examName)}
                            className="h-4 w-4 rounded border-gray-300 text-[#115740] focus:ring-[#115740]"
                          />
                          <span className="text-sm text-gray-700 flex-1">{examName}</span>
                          <span className="text-xs text-gray-400 flex-shrink-0">min {minRequired}</span>
                        </label>

                        {isSelected && (
                          <div className="border border-[#115740] border-t-0 rounded-b px-3 py-2.5 bg-[#115740]/5 space-y-2">
                            <div className="flex items-center gap-3">
                              <label className="text-xs text-gray-600">Your score:</label>
                              <select
                                value={studentScore || ''}
                                onChange={(e) => setExamScore(examTab, examName, parseInt(e.target.value) || 0)}
                                className="h-8 px-2 rounded border border-gray-300 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-[#115740]"
                              >
                                <option value="" disabled>Select...</option>
                                {scoreOptions.map((s) => <option key={s} value={s}>{s}</option>)}
                              </select>
                              {noCredit && (
                                <span className="text-xs text-red-500">Score below minimum ({minRequired}) — no credit</span>
                              )}
                            </div>
                            {matched && (
                              <div className="flex flex-wrap gap-1">
                                {matched.courses.map((c) => (
                                  <span key={c.code} className="inline-flex text-[10px] bg-[#115740]/10 text-[#115740] px-1.5 py-0.5 rounded">
                                    {c.code} ({c.credits} credits)
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4">
                  <label className="block text-xs text-gray-500 uppercase tracking-wider font-semibold mb-2" style={{ fontFamily: serif }}>
                    Additional Transfer Credits
                  </label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="0"
                    value={additionalCredits || ''}
                    onChange={(e) => setAdditionalCredits(parseInt(e.target.value) || 0)}
                    className="border-gray-300 focus-visible:ring-[#115740] w-24"
                  />
                  <p className="text-xs text-gray-400 mt-1.5">For transfer credits not covered by AP/IB exams.</p>
                </div>

                <div className="flex items-center justify-between py-2 px-3 bg-[#115740]/5 rounded border border-[#115740]/10">
                  <span className="text-sm font-medium text-[#115740]">Total Exam/Transfer Credits</span>
                  <span className="text-lg font-bold text-[#115740]">{totalExamCredits}</span>
                </div>
              </div>
            )}

            {/* ===== Step 3: Past Courses ===== */}
            {step === 2 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  Add courses you&apos;ve completed. AP/IB courses are added automatically from Step 2.
                </p>

                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search courses (e.g. BUAD 201, Accounting)"
                    value={pastSearchQuery}
                    onChange={(e) => { setPastSearchQuery(e.target.value); handleSearch(e.target.value, 'past'); }}
                    className="w-full h-10 pl-10 pr-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
                  />
                  {pastSearching && <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">Searching...</div>}
                </div>

                {pastSearchResults.length > 0 && (
                  <div className="border border-gray-200 rounded max-h-40 overflow-y-auto divide-y divide-gray-100">
                    {pastSearchResults.map((course) => (
                      <button
                        key={course.code}
                        onClick={() => addCompletedCourse(course)}
                        className="w-full text-left px-3 py-2 hover:bg-[#f7f5f0] transition-colors flex items-center justify-between"
                        disabled={allCompleted.some((c) => c.code === course.code)}
                      >
                        <div>
                          <span className="text-sm font-medium text-[#115740]">{course.code}</span>
                          <span className="text-sm text-gray-500 ml-2">{course.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">{course.credits} credits</span>
                      </button>
                    ))}
                  </div>
                )}

                <button onClick={() => setShowManualPast(!showManualPast)} className="flex items-center gap-1.5 text-sm text-[#115740] hover:underline">
                  <Plus className="h-3.5 w-3.5" />
                  Add course manually
                </button>

                {showManualPast && (
                  <div className="bg-[#f7f5f0] border border-[#e8e4db] rounded p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Course Code</label>
                        <Input placeholder="e.g. BUAD 201" value={manualCode} onChange={(e) => setManualCode(e.target.value)} className="border-gray-300 focus-visible:ring-[#115740]" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Title (optional)</label>
                        <Input placeholder="e.g. Intro to Accounting" value={manualTitle} onChange={(e) => setManualTitle(e.target.value)} className="border-gray-300 focus-visible:ring-[#115740]" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Credits</label>
                        <Input type="number" min="1" max="6" placeholder="3" value={manualCredits} onChange={(e) => setManualCredits(e.target.value)} className="border-gray-300 focus-visible:ring-[#115740]" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Grade</label>
                        <select value={manualGrade} onChange={(e) => setManualGrade(e.target.value)} className="w-full h-10 px-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent bg-white">
                          <option value="" disabled>Select...</option>
                          {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                        </select>
                      </div>
                    </div>
                    <button onClick={addManualCourse} disabled={!manualCode.trim()} className="px-4 py-2 text-sm font-medium bg-[#115740] text-white rounded hover:bg-[#0d4632] transition-colors disabled:opacity-50">
                      Add Course
                    </button>
                  </div>
                )}

                {allCompleted.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold" style={{ fontFamily: serif }}>
                      Completed Courses ({allCompleted.length})
                    </p>
                    {allCompleted.map((course, idx) => (
                      <div
                        key={`${course.code}-${idx}`}
                        className={`flex items-center gap-2 px-3 py-2 border rounded ${
                          course.fromAP ? 'border-[#B9975B]/30 bg-[#B9975B]/5' : 'border-gray-200 bg-white'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-[#262626]">{course.code}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.credits} credits</span>
                        </div>
                        {course.fromAP ? (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[#B9975B] text-white">
                            {course.grade}
                          </span>
                        ) : (
                          <select
                            value={course.grade || ''}
                            onChange={(e) => {
                              const manualIdx = completedCourses.findIndex((c) => c === completedCourses.filter((cc) => !cc.fromAP)[idx - examCourses.length]);
                              setCompletedCourses((prev) => prev.map((c, i) => (i === manualIdx ? { ...c, grade: e.target.value } : c)));
                            }}
                            className="h-8 px-2 rounded border border-gray-200 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-[#115740]"
                          >
                            <option value="" disabled>Grade</option>
                            {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                          </select>
                        )}
                        {!course.fromAP && (
                          <button
                            onClick={() => {
                              const nonAP = completedCourses.filter((c) => !c.fromAP);
                              const actualIdx = idx - examCourses.length;
                              const target = nonAP[actualIdx];
                              setCompletedCourses((prev) => prev.filter((c) => c !== target));
                            }}
                            className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ===== Step 4: Currently Enrolled ===== */}
            {step === 3 && (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">Add courses you&apos;re currently enrolled in this semester.</p>

                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search courses (e.g. BUAD 301, Finance)"
                    value={currentSearchQuery}
                    onChange={(e) => { setCurrentSearchQuery(e.target.value); handleSearch(e.target.value, 'current'); }}
                    className="w-full h-10 pl-10 pr-3 rounded border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#115740] focus:border-transparent"
                  />
                  {currentSearching && <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">Searching...</div>}
                </div>

                {currentSearchResults.length > 0 && (
                  <div className="border border-gray-200 rounded max-h-40 overflow-y-auto divide-y divide-gray-100">
                    {currentSearchResults.map((course) => (
                      <button
                        key={course.code}
                        onClick={() => addEnrolledCourse(course)}
                        className="w-full text-left px-3 py-2 hover:bg-[#f7f5f0] transition-colors flex items-center justify-between"
                        disabled={enrolledCourses.some((c) => c.code === course.code)}
                      >
                        <div>
                          <span className="text-sm font-medium text-[#115740]">{course.code}</span>
                          <span className="text-sm text-gray-500 ml-2">{course.title}</span>
                        </div>
                        <span className="text-xs text-gray-400">{course.credits} credits</span>
                      </button>
                    ))}
                  </div>
                )}

                {enrolledCourses.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold" style={{ fontFamily: serif }}>
                      Currently Enrolled ({enrolledCourses.length})
                    </p>
                    {enrolledCourses.map((course, idx) => (
                      <div key={`${course.code}-${idx}`} className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded bg-white">
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-[#262626]">{course.code}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.title}</span>
                          <span className="text-xs text-gray-400 ml-2">{course.credits} credits</span>
                        </div>
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[#115740] text-white">Enrolled</span>
                        <button
                          onClick={() => setEnrolledCourses((prev) => prev.filter((_, i) => i !== idx))}
                          className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {enrolledCourses.length === 0 && (
                  <div className="text-center py-6 text-sm text-gray-400">Search and add your current courses above to continue.</div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-8 py-4 border-t border-gray-200 flex items-center justify-between flex-shrink-0">
            {step > 0 ? (
              <button onClick={() => setStep((s) => s - 1)} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors">
                <ChevronLeft className="h-4 w-4" /> Back
              </button>
            ) : (
              <button onClick={onClose} className="text-sm text-gray-400 hover:text-gray-600 transition-colors">Skip for now</button>
            )}

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                className="flex items-center gap-1.5 px-5 py-2 bg-[#115740] text-white text-sm font-medium rounded hover:bg-[#0d4632] transition-colors"
              >
                Next <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={submitting || enrolledCourses.length === 0}
                className="flex items-center gap-1.5 px-5 py-2 bg-[#B9975B] text-white text-sm font-medium rounded hover:bg-[#a88649] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Setting up...' : enrolledCourses.length === 0 ? 'Add Current Courses' : 'Complete Setup'}
                {!submitting && enrolledCourses.length > 0 && <Check className="h-4 w-4" />}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
