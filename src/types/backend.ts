// Backend API Response Types

export interface SectionResponse {
  crn: string;
  section_number: string;
  instructor: string;
  status: string;
  capacity: number;
  enrolled: number;
  available: number;
  meeting_days?: string;
  meeting_time?: string;
  building?: string;
  room?: string;
}

export interface CourseResponse {
  course_code: string;
  subject_code: string;
  course_number: string;
  title: string;
  description?: string;
  credits: number;
  attributes: string[];
  sections: SectionResponse[];
}

export interface CourseListResponse {
  courses: CourseResponse[];
  total: number;
  term_code: string;
}

export interface SearchResponse {
  results: CourseResponse[];
  total: number;
  query: string;
}

export interface SubjectResponse {
  subjects: string[];
  total: number;
}

export interface TermInfo {
  current: {
    term_code: string;
    display_name: string;
    is_registration: boolean;
  };
  next_transition: {
    date: string;
    next_term: string;
    next_semester: string;
  };
  is_registration_period: boolean;
}
