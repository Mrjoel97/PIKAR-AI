import { fetchWithAuth } from './api';

export interface Department {
  id: string;
  name: string;
  type: string;
  status: 'RUNNING' | 'PAUSED' | 'ERROR';
  state: Record<string, unknown>;
  last_heartbeat: string;
}

export async function listDepartments(): Promise<Department[]> {
  const response = await fetchWithAuth('/departments');
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
