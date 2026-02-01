import { ChatInterface } from '@/components/chat/ChatInterface';

interface DashboardPageProps {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  // In Next.js 15+, searchParams is a Promise
  const params = await searchParams;
  const sessionId = typeof params.sessionId === 'string' ? params.sessionId : undefined;

  return (
    <div className="h-[calc(100vh-theme(spacing.16))] p-4 max-w-6xl mx-auto">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-slate-800 dark:text-slate-100">
          {sessionId ? 'Resume Session' : 'New Chat'}
        </h1>
        <p className="text-sm text-slate-500">
          {sessionId ? `Continuing session ${sessionId.slice(0, 8)}...` : 'Start a new conversation with Pikar AI'}
        </p>
      </div>

      <ChatInterface initialSessionId={sessionId} />
    </div>
  );
}