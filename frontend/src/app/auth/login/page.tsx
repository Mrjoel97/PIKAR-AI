// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { Suspense } from 'react';
import LoginPage from './LoginPage';

export default function Page() {
  return (
    <Suspense>
      <LoginPage />
    </Suspense>
  );
}
