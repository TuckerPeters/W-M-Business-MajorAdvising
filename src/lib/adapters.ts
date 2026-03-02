import { CourseResponse } from '@/types/backend';
import { Course } from '@/types';

/**
 * Converts backend CourseResponse to frontend Course type
 */
export function adaptCourse(backendCourse: CourseResponse): Course {
  // Extract course number for level
  const courseNum = parseInt(backendCourse.course_number) || 0;

  // Check if any section has lab indicator
  const hasLab = backendCourse.sections.some(
    s => s.section_number.toLowerCase().includes('l')
  );

  // Calculate difficulty based on course level (rough estimate)
  let difficultyIndex = 5; // default medium
  if (courseNum < 200) difficultyIndex = 3;
  else if (courseNum < 300) difficultyIndex = 5;
  else if (courseNum < 400) difficultyIndex = 7;
  else difficultyIndex = 9;

  return {
    code: backendCourse.course_code,
    title: backendCourse.title,
    credits: backendCourse.credits,
    dept: backendCourse.subject_code,
    level: courseNum,
    hasLab,
    difficultyIndex,
    prereqs: [], // Backend doesn't provide prerequisites yet
    description: backendCourse.description,
  };
}

/**
 * Converts array of backend courses to frontend courses
 */
export function adaptCourses(backendCourses: CourseResponse[]): Course[] {
  return backendCourses.map(adaptCourse);
}
