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
    expect(css).toContain(':root');
    expect(css).toContain('--bg: #0d1117');
    expect(css).toContain('--panel: #161b22');
    expect(css).toContain('--border: #30363d');
    expect(css).toContain('--fg: #e6edf3');
    expect(css).toContain('--accent: #3fb950');
    expect(css).toContain('--danger: #f85149');
    
    expect(css).toMatch(/body\s*\{[^}]*background:\s*var\(--bg\)[^}]*color:\s*var\(--fg\)[^}]*font-family:[^}]*"JetBrains Mono"[^}]*monospace[^}]*\}/s);
  });

  it('defines .board rule with grid layout', () => {
    expect(css).toMatch(/\.board\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*repeat\(3,\s*1fr\)[^}]*gap:[^}]*\}/s);
  });

  it('defines .card and .card:hover rules', () => {
    expect(css).toMatch(/\.card\s*\{[^}]*background:\s*var\(--panel\)[^}]*border:[^}]*var\(--border\)[^}]*border-radius:[^}]*padding:[^}]*\}/s);
    expect(css).toMatch(/\.card:hover\s*\{[^}]*border-color:\s*var\(--accent\)[^}]*box-shadow:[^}]*\}/s);
  });

  it('defines .urgent, .topbar, and .brand rules', () => {
    expect(css).toMatch(/\.urgent\s*\{[^}]*border-left:[^}]*var\(--danger\)[^}]*\}/s);
    expect(css).toMatch(/\.topbar\s*\{[^}]*display:\s*flex[^}]*border-bottom:[^}]*var\(--border\)[^}]*\}/s);
    expect(css).toMatch(/\.brand\s*\{[^}]*color:\s*var\(--accent\)[^}]*\}/s);
  });
});