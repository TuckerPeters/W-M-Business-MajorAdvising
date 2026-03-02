'use client';

import { useDroppable } from '@dnd-kit/core';
import Badge from '@/components/ui/Badge';
import TimelineCourseCard from './TimelineCourseCard';
import { Course, SemesterColumn } from '@/types';

interface SemesterColumnProps {
  semester: SemesterColumn;
  onRemoveCourse?: (courseCode: string) => void;
  onCourseClick?: (course: Course) => void;
  isDropTarget?: boolean;
  isInvalidTarget?: boolean;
  isDragActive?: boolean;
}

const statusConfig: Record<string, { label: string; badge: 'success' | 'warning' | 'secondary' | 'outline'; bgClass: string }> = {
  completed: { label: 'Completed', badge: 'success', bgClass: 'bg-[#f7f5f0]' },
  current: { label: 'In Progress', badge: 'warning', bgClass: 'bg-[#f7f5f0]' },
  planned: { label: 'Planned', badge: 'secondary', bgClass: 'bg-white' },
  future: { label: 'Future', badge: 'outline', bgClass: 'bg-white' },
};

export default function SemesterColumnComponent({
  semester,
  onRemoveCourse,
  onCourseClick,
  isDropTarget = false,
  isInvalidTarget = false,
  isDragActive = false,
}: SemesterColumnProps) {
  const isEditable = semester.status === 'planned' || semester.status === 'future';

  const { setNodeRef, isOver } = useDroppable({
    id: `semester:${semester.id}`,
    disabled: !isEditable,
  });

  const totalCredits = semester.courses.reduce((sum, c) => sum + c.credits, 0);
  const config = statusConfig[semester.status] || statusConfig.future;

  // Border styles during drag
  let borderClass = 'border-[#e8e4db]';
  if (isDragActive && isEditable) {
    if (isOver && isDropTarget) {
      borderClass = 'border-[#115740] border-2 shadow-lg shadow-[#115740]/10';
    } else if (isDropTarget) {
      borderClass = 'border-[#115740]/40 border-dashed border-2';
    } else if (isInvalidTarget) {
      borderClass = 'border-red-300 border-dashed border-2 opacity-50';
    }
  }

  return (
    <div
      ref={setNodeRef}
      className={`rounded border ${borderClass} ${config.bgClass} transition-all duration-200`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#e8e4db]">
        <div className="flex items-center gap-2.5">
          <h4
            className="text-[#115740] font-semibold text-sm"
            style={{ fontFamily: 'Georgia, "Times New Roman", serif' }}
          >
            {semester.term}
          </h4>
          <Badge variant={config.badge}>{config.label}</Badge>
        </div>
        <span className="text-xs text-gray-500">
          {totalCredits} credit{totalCredits !== 1 ? 's' : ''}
          {semester.courses.length > 0 && ` · ${semester.courses.length} course${semester.courses.length !== 1 ? 's' : ''}`}
        </span>
      </div>

      {/* Course cards */}
      <div className="p-3">
        {semester.courses.length === 0 ? (
          <div className={`text-center py-4 text-sm ${
            isDragActive && isDropTarget
              ? 'text-[#115740] font-medium'
              : 'text-gray-400'
          }`}>
            {isDragActive && isDropTarget
              ? 'Drop course here'
              : isEditable
              ? 'No courses — drag from catalog or click to add'
              : 'No courses'}
          </div>
        ) : (
          <div className="space-y-1.5">
            {semester.courses.map((course, idx) => (
              <TimelineCourseCard
                key={`${course.code}-${idx}`}
                course={course}
                draggable={isEditable}
                dragId={`${semester.id}:${course.code}`}
                dragData={{ course, sourceSemesterId: semester.id }}
                onClick={onCourseClick ? () => onCourseClick(course) : undefined}
                onRemove={isEditable && onRemoveCourse ? () => onRemoveCourse(course.code) : undefined}
              />
            ))}
          </div>
        )}

        {/* Drop hint when dragging over empty droppable */}
        {isDragActive && isDropTarget && isOver && semester.courses.length > 0 && (
          <div className="mt-2 py-2 border-2 border-dashed border-[#115740]/30 rounded text-center text-xs text-[#115740] font-medium">
            Drop here to add
          </div>
        )}
      </div>
    </div>
  );
}
