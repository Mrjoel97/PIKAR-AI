// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

export interface Course {
  id: string;
  title: string;
  description: string | null;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  duration_minutes: number;
  lessons_count: number;
  thumbnail_gradient: string | null;
  is_recommended: boolean;
  sort_order: number;
  created_at: string;
}

export interface LearningProgress {
  id: string;
  user_id: string;
  course_id: string;
  progress_percent: number;
  status: 'not_started' | 'in_progress' | 'completed';
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
  learning_courses?: Course;
}

export async function getCourses(category?: string): Promise<Course[]> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : '';
  const response = await fetchWithAuth(`/learning/courses${qs}`);
  return response.json();
}

export async function getProgress(): Promise<LearningProgress[]> {
  const response = await fetchWithAuth('/learning/progress');
  return response.json();
}

export async function startCourse(courseId: string): Promise<LearningProgress> {
  const response = await fetchWithAuth(`/learning/progress/${courseId}/start`, {
    method: 'POST',
  });
  return response.json();
}

export async function updateProgress(
  courseId: string,
  progressPercent: number,
): Promise<LearningProgress> {
  const response = await fetchWithAuth(`/learning/progress/${courseId}`, {
    method: 'PATCH',
    body: JSON.stringify({ progress_percent: progressPercent }),
  });
  return response.json();
}
