export type UserRole = 'student' | 'advisor';

export interface Student {
  id: string;
  userId: string;
  name: string;
  email: string;
  classYear: number;
  gpa: number;
  creditsEarned: number;
  declared: boolean;
  intendedMajor?: string;
  apCredits: number;
  holds: string[];
  updatedAt: Date;
}

export interface Course {
  code: string;
  title: string;
  credits: number;
  dept: string;
  level: number;
  hasLab: boolean;
  difficultyIndex: number;
  prereqs: string[];
  description?: string;
  term?: string;
  grade?: string;
  status?: 'enrolled' | 'planned' | 'completed';
}

export interface Citation {
  title: string;
  url: string;
  version: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  risks?: string[];
  nextSteps?: string[];
  timestamp: Date;
}

export interface ScheduleScore {
  score: number;
  rationale: string;
  suggestedSwaps: string[];
  warnings: string[];
}

export interface Advisee {
  id: string;
  name: string;
  email: string;
  classYear: number;
  gpa: number;
  creditsEarned: number;
  declared: boolean;
  intendedMajor?: string;
  riskFlags: {
    overloadRisk: boolean;
    missingPrereqs: boolean;
    gpaDip: boolean;
  };
  lastContact?: Date;
}

export interface AdvisorNote {
  id: string;
  studentId: string;
  advisorId: string;
  note: string;
  visibility: 'private' | 'shared';
  createdAt: Date;
}

export interface Milestone {
  id: string;
  title: string;
  description: string;
  deadline?: Date;
  completed: boolean;
  credits?: {
    current: number;
    required: number;
  };
}
