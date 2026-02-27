import { redirect } from 'next/navigation';

export default function WorkflowsIndexPage() {
  redirect('/dashboard/workflows/templates');
}

