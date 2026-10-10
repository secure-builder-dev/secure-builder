import { describe, it, expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import fs from 'node:fs';
import path from 'node:path';

afterEach(() => {
  cleanup();
});

const cssPath = path.resolve(__dirname, '../src/styles.css');

const getCss = () => {
  if (!fs.existsSync(cssPath)) return '';
  return fs.readFileSync(cssPath, 'utf8');
};

describe('styles.css', () => {
  it('should have .board with grid layout and 3 columns', () => {
    const css = getCss();
    expect(css).toContain('.board');
    expect(css).toContain('display: grid');
    expect(css).toContain('grid-template-columns: repeat(3, 1fr)');
    expect(css).toContain('gap');
  });

  it('should have .card with border-radius, box-shadow, and padding', () => {
    const css = getCss();
    expect(css).toContain('.card');
    expect(css).toContain('border-radius');
    expect(css).toContain('box-shadow');
    expect(css).toContain('padding');
  });

  it('should have .card:hover that changes box-shadow', () => {
    const css = getCss();
    expect(css).toContain('.card:hover');
    expect(css).toContain('box-shadow');
  });

  it('should have .urgent with border-left color #c0392b', () => {
    const css = getCss();
    expect(css).toContain('.urgent');
    expect(css).toContain('border-left');
    expect(css).toContain('#c0392b');
  });

  it('should have .topbar with display: flex', () => {
    const css = getCss();
    expect(css).toContain('.topbar');
    expect(css).toContain('display: flex');
  });
});