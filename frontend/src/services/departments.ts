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
