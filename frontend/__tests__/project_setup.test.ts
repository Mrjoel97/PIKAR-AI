import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Project Setup & Dependencies', () => {
  const rootDir = path.resolve(__dirname, '..');

  it('should have a package.json file', () => {
    const packageJsonPath = path.join(rootDir, 'package.json');
    expect(fs.existsSync(packageJsonPath)).toBe(true);
  });

  it('should have next.config.ts', () => {
    const nextConfigPath = path.join(rootDir, 'next.config.ts');
    expect(fs.existsSync(nextConfigPath)).toBe(true);
  });

  it('should have tsconfig.json', () => {
    const tsconfigPath = path.join(rootDir, 'tsconfig.json');
    expect(fs.existsSync(tsconfigPath)).toBe(true);
  });

  it('should list critical dependencies in package.json', () => {
    const packageJsonPath = path.join(rootDir, 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));
    const dependencies = packageJson.dependencies || {};
    const devDependencies = packageJson.devDependencies || {};

    expect(dependencies['next']).toBeDefined();
    expect(dependencies['react']).toBeDefined();
    expect(dependencies['react-dom']).toBeDefined();
    expect(devDependencies['tailwindcss']).toBeDefined();
    expect(devDependencies['typescript']).toBeDefined();
  });
});
