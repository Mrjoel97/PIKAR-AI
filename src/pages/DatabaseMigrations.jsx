import React from 'react';
import MigrationManager from '@/components/migration/MigrationManager';

export default function DatabaseMigrationsPage() {
    return (
        <div className="p-6">
            <MigrationManager />
        </div>
    );
}