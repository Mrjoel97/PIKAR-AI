// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createInitiativeFromBraindump } from '@/services/initiatives';
import { fetchWithAuth } from '@/services/api';

jest.mock('@/services/api');

describe('Initiatives Service', () => {
    it('should call fetchWithAuth with the correct parameters when creating an initiative from a braindump', async () => {
        // Arrange
        const braindumpId = 'test-braindump-id';
        const mockFetchWithAuth = fetchWithAuth as jest.Mock;
        mockFetchWithAuth.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ success: true }),
        });

        // Act
        await createInitiativeFromBraindump(braindumpId);

        // Assert
        expect(mockFetchWithAuth).toHaveBeenCalledWith('/initiatives/from-braindump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ braindump_id: braindumpId }),
        });
    });
});
