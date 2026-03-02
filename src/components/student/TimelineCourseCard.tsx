'use client';

import { useDraggable } from '@dnd-kit/core';
import { X } from 'lucide-react';
import { Course } from '@/types';

interface TimelineCourseCardProps {
  course: Course;
  draggable?: boolean;
  dragId?: string;
  dragData?: { course: Course; sourceSemesterId: string };
  onClick?: () => void;
  onRemove?: () => void;
  categoryBadge?: string;
  className?: string;
}

export default function TimelineCourseCard({
  course,
  draggable = false,
  dragId,
  dragData,
  onClick,
  onRemove,
  categoryBadge,
  className = '',
}: TimelineCourseCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: dragId || course.code,
    data: dragData,
    disabled: !draggable,
  });

  return (
    <div
      ref={draggable ? setNodeRef : undefined}
      {...(draggable ? { ...listeners, ...attributes } : {})}
      onClick={onClick}
      className={`
        relative flex items-center justify-between px-3 py-2 rounded border bg-white
        transition-all text-sm
        ${isDragging ? 'opacity-40 border-[#B9975B] shadow-md' : 'border-[#e8e4db] hover:border-[#B9975B]/60'}
        ${draggable ? 'cursor-grab active:cursor-grabbing' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="font-semibold text-[#115740] truncate">{course.code}</span>
        {categoryBadge && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#B9975B]/15 text-[#8a6e3b] font-medium flex-shrink-0">
            {categoryBadge}
          </span>
        )}
        {course.hasLab && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#115740]/10 text-[#115740] font-medium flex-shrink-0">
            Lab
          </span>
        )}
      </div>
      <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
        <span className="text-xs text-gray-400">{course.credits}cr</span>
        {onRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="p-0.5 rounded hover:bg-red-50 text-gray-300 hover:text-red-500 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
