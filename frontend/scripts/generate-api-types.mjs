// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// Generates TypeScript types from the FastAPI OpenAPI schema without running the server.
// Usage: node scripts/generate-api-types.mjs

import { execFileSync, spawnSync } from 'node:child_process';
import { writeFileSync, existsSync, unlinkSync, mkdtempSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const __dirname = dirname(fileURLToPath(import.meta.url));
const frontendDir = resolve(__dirname, '..');
const projectRoot = resolve(frontendDir, '..');
const schemaPath = resolve(frontendDir, '.openapi-schema.json');
const outputPath = resolve(frontendDir, 'src', 'types', 'api.generated.ts');

// On Windows, uv and npx are .cmd wrappers. We write the Python code to a
// temp script file to avoid quoting issues when passing multi-word strings
// through the Windows shell.
const isWindows = process.platform === 'win32';

console.log('Generating API types from OpenAPI schema...');

// Step 1: Export OpenAPI schema from FastAPI app without running the server.
// Write Python code to a temp file to avoid shell quoting issues on Windows.
const OPENAPI_PYTHON_CODE =
    'from app.fast_api_app import app; import json; print(json.dumps(app.openapi()))';

const uvEnv = {
    ...process.env,
    // Provide minimal env vars to satisfy app startup without real secrets
    GOOGLE_API_KEY: process.env.GOOGLE_API_KEY || 'placeholder',
    SUPABASE_URL: process.env.SUPABASE_URL || 'https://placeholder.supabase.co',
    SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || 'placeholder',
    SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || 'placeholder',
    REDIS_HOST: process.env.REDIS_HOST || 'localhost',
    REDIS_PORT: process.env.REDIS_PORT || '6379',
};

// Write Python code to temp file so it survives shell quoting on all platforms
const tmpDir = mkdtempSync(join(tmpdir(), 'pikar-openapi-'));
const pyScriptPath = join(tmpDir, 'export_openapi.py');
writeFileSync(pyScriptPath, OPENAPI_PYTHON_CODE, 'utf-8');

let schemaJson;
try {
    const uvArgs = ['run', 'python', pyScriptPath];
    const spawnOpts = {
        cwd: projectRoot,
        env: uvEnv,
        stdio: ['ignore', 'pipe', 'pipe'],
        encoding: 'buffer',
        ...(isWindows ? { shell: true } : {}),
    };

    const result = spawnSync('uv', uvArgs, spawnOpts);

    if (result.status !== 0) {
        const stderr = result.stderr?.toString() ?? '';
        const stdout = result.stdout?.toString() ?? '';
        console.error('Failed to export OpenAPI schema from FastAPI app.');
        console.error('stderr:', stderr);
        console.error('stdout:', stdout);
        process.exit(1);
    }
    schemaJson = result.stdout;
} catch (err) {
    console.error('Failed to export OpenAPI schema from FastAPI app.');
    console.error(err.message);
    process.exit(1);
} finally {
    // Clean up temp Python script
    if (existsSync(pyScriptPath)) {
        unlinkSync(pyScriptPath);
    }
}

writeFileSync(schemaPath, schemaJson);
console.log(`OpenAPI schema written to ${schemaPath}`);

// Step 2: Run openapi-typescript to generate TypeScript types
try {
    const npxArgs = ['openapi-typescript', schemaPath, '-o', outputPath];
    const spawnOpts = {
        cwd: frontendDir,
        stdio: 'inherit',
        ...(isWindows ? { shell: true } : {}),
    };

    const result = spawnSync('npx', npxArgs, spawnOpts);
    if (result.status !== 0) {
        throw new Error(`openapi-typescript exited with status ${result.status}`);
    }
    console.log(`TypeScript types written to ${outputPath}`);
} catch (err) {
    console.error('Failed to generate TypeScript types from schema.');
    console.error(err.message);
    process.exit(1);
} finally {
    // Step 3: Clean up intermediate schema file
    if (existsSync(schemaPath)) {
        unlinkSync(schemaPath);
        console.log('Cleaned up temporary schema file.');
    }
}

console.log('Done. Commit frontend/src/types/api.generated.ts to keep types in sync.');
