// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

export interface Department {
  id: string;
  name: string;
  type: string;
  status: 'RUNNING' | 'PAUSED' | 'ERROR';
  state: Record<string, unknown>;
  last_heartbeat: string;
}

export interface DepartmentActivity {
  id: string;
  name: string;
  type: string;
  status: 'RUNNING' | 'PAUSED' | 'ERROR';
  last_heartbeat: string | null;
  trigger_count: number;
  decision_count_24h: number;
  active_workflows: number;
  last_cycle_metrics: Record<string, unknown> | null;
}

export interface ActivityFeedItem {
  department_id: string;
  department_name: string;
  decision_type: string;
  decision_logic: string | null;
  outcome: string;
  timestamp: string;
}

export interface DepartmentActivityResponse {
  departments: DepartmentActivity[];
  activity_feed: ActivityFeedItem[];
}

export interface ProactiveTrigger {
  id: string;
  department_id: string;
  name: string;
  condition_type: string;
  action_type: string;
  enabled: boolean;
  last_triggered_at: string | null;
  cooldown_hours: number;
  max_triggers_per_day: number;
}

export interface DecisionLogEntry {
  id: string;
  department_id: string;
  department_name?: string;
  cycle_timestamp: string;
  decision_type: string;
  decision_logic: string | null;
  outcome: string;
  error_message: string | null;
}

export interface InterDeptRequest {
  id: string;
  from_department_id: string;
  to_department_id: string;
  from_department_name?: string;
  to_department_name?: string;
  request_type: string;
  priority: number;
  status: string;
  created_at: string;
}

export async function listDepartments(): Promise<Department[]> {
  const response = await fetchWithAuth('/departments');
  return response.json();
}

export async function getDepartmentActivity(): Promise<DepartmentActivityResponse> {
  const response = await fetchWithAuth('/departments/activity');
  return response.json();
}

export async function toggleDepartment(id: string): Promise<{ status: string }> {
  const response = await fetchWithAuth(`/departments/${id}/toggle`, {
    method: 'POST',
  });
  return response.json();
}

export async function triggerDepartmentHeartbeat(): Promise<{ results: unknown[] }> {
  const response = await fetchWithAuth('/departments/tick', {
    method: 'POST',
  });
  return response.json();
}

export async function getDepartmentTriggers(): Promise<ProactiveTrigger[]> {
  const response = await fetchWithAuth('/departments/triggers');
  return response.json();
}

export async function toggleTrigger(id: string): Promise<{ enabled: boolean }> {
  const response = await fetchWithAuth(`/departments/triggers/${id}`, {
    method: 'PUT',
  });
  return response.json();
}

export async function getDepartmentDecisionLog(hours = 24): Promise<DecisionLogEntry[]> {
  const response = await fetchWithAuth(`/departments/decision-log?hours=${hours}`);
  return response.json();
}

export async function getInterDeptRequests(): Promise<InterDeptRequest[]> {
  const response = await fetchWithAuth('/departments/requests');
  return response.json();
}

// ── Department Task Handoffs ─────────────────────────────────────────────────

export interface DepartmentTask {
  id: string;
  title: string;
  description: string | null;
  from_department_id: string;
  to_department_id: string;
  from_department_name?: string;
  to_department_name?: string;
  created_by: string;
  assigned_to: string | null;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DepartmentHealthSummary {
  department_id: string;
  department_name: string;
  department_type: string;
  department_status: string;
  active_tasks: number;
  completed_30d: number;
  total_30d: number;
  health_status: 'green' | 'yellow' | 'red';
}

export interface CreateDepartmentTaskParams {
  title: string;
  from_department_id: string;
  to_department_id: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  due_date?: string;
  assigned_to?: string;
}

export async function getDepartmentTasks(
  deptId: string,
  direction: 'inbound' | 'outbound' = 'inbound',
  status?: string,
  limit = 50,
): Promise<DepartmentTask[]> {
  const params = new URLSearchParams({ direction, limit: String(limit) });
  if (status) params.set('status', status);
  const response = await fetchWithAuth(`/departments/${deptId}/tasks?${params}`);
  return response.json();
}

export async function createDepartmentTask(
  params: CreateDepartmentTaskParams,
): Promise<DepartmentTask> {
  const response = await fetchWithAuth('/departments/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return response.json();
}

export async function updateDepartmentTaskStatus(
  taskId: string,
  status: DepartmentTask['status'],
): Promise<DepartmentTask> {
  const response = await fetchWithAuth(`/departments/tasks/${taskId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return response.json();
}

export async function getDepartmentHealth(): Promise<DepartmentHealthSummary[]> {
  const response = await fetchWithAuth('/departments/health');
  return response.json();
}
