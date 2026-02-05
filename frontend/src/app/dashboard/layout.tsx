import { NotificationProvider } from '@/contexts/NotificationContext';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      {children}
    </NotificationProvider>
  );
}
