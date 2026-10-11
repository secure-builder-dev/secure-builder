import { describe, it, expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import fs from 'node:fs';
import path from 'node:path';

afterEach(cleanup);

const cssPath = path.resolve(__dirname, '../src/styles.css');
const css = fs.existsSync(cssPath) ? fs.readFileSync(cssPath, 'utf8') : '';

describe('styles.css', () => {
  it('defines :root custom properties and body styles', () => {
    expect(css).toContain('--bg: #0d1117');
    expect(css).toContain('--panel: #161b22');
    expect(css).toContain('--border: #30363d');
    expect(css).toContain('--fg: #e6edf3');
    expect(css).toContain('--accent: #3fb950');
    expect(css).toContain('--danger: #f85149');
    
    expect(css).toMatch(/body\s*\{[^}]*background:\s*var\(--bg\)[^}]*\}/);
    expect(css).toMatch(/body\s*\{[^}]*color:\s*var\(--fg\)[^}]*\}/);
    expect(css).toMatch(/body\s*\{[^}]*font-family:\s*[^}]*"JetBrains Mono"[^}]*monospace[^}]*\}/);
  });

  it('defines .board rule with grid layout', () => {
    expect(css).toMatch(/\.board\s*\{[^}]*display:\s*grid[^}]*\}/);
    expect(css).toMatch(/\.board\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*1fr\)[^}]*\}/);
    expect(css).toMatch(/\.board\s*\{[^}]*gap:\s*[^}]*\}/);
  });

  it('defines .card and .card:hover rules', () => {
    expect(css).toMatch(/\.card\s*\{[^}]*background:\s*var\(--panel\)[^}]*\}/);
    expect(css).toMatch(/\.card\s*\{[^}]*border:[^}]*var\(--border\)[^}]*\}/);
    expect(css).toMatch(/\.card\s*\{[^}]*border-radius:\s*[^}]*\}/);
    expect(css).toMatch(/\.card\s*\{[^}]*padding:\s*[^}]*\}/);
    
    expect(css).toMatch(/\.card:hover\s*\{[^}]*border-color:\s*var\(--accent\)[^}]*\}/);
    expect(css).toMatch(/\.card:hover\s*\{[^}]*box-shadow:\s*[^}]*\}/);
  });

  it('defines .urgent, .topbar, and .brand rules', () => {
    expect(css).toMatch(/\.urgent\s*\{[^}]*border-left:[^}]*var\(--danger\)[^}]*\}/);
    expect(css).toMatch(/\.topbar\s*\{[^}]*display:\s*flex[^}]*\}/);
    expect(css).toMatch(/\.topbar\s*\{[^}]*border-bottom:[^}]*var\(--border\)[^}]*\}/);
    expect(css).toMatch(/\.brand\s*\{[^}]*color:\s*var\(--accent\)[^}]*\}/);
  });
});