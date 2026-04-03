// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NotificationProvider } from '@/contexts/NotificationContext';
import { SubscriptionProvider } from '@/contexts/SubscriptionContext';
import { WorkspaceProvider } from '@/contexts/WorkspaceContext';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <NotificationProvider>
      <SubscriptionProvider>
        <WorkspaceProvider>
          {children}
        </WorkspaceProvider>
      </SubscriptionProvider>
    </NotificationProvider>
  );
}
