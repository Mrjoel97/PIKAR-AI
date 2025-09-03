import React from 'react';
import MigrationManager from '@/components/migration/MigrationManager';
import SupabaseDataMigrator from '@/components/migration/SupabaseDataMigrator';

export default function DatabaseMigrationsPage() {
    return (
        <div className="p-6 space-y-4">
            <MigrationManager />
            <SupabaseDataMigrator />
        </div>
    );
}