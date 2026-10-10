import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockFetch = (url: string) => {
  const responses: Record<string, string> = {
    '/api/dashboard': JSON.stringify({ todo: [], in_progress: [], completed: [] }),
    '/api/filed': JSON.stringify({ tickets: [] }),
    '/api/board': JSON.stringify({ todo: [], in_progress: [], completed: [] }),
    '/api/me': JSON.stringify({ user: 'her' }),
  };
  return new Response(responses[url] || '{}', { status: 200 });
};

describe('App Menu and Directions', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('shows Menu in topbar and hides Directions by default', () => {
    globalThis.fetch = vi.fn().mockImplementation((req) => mockFetch(new URL(req as string, 'http://localhost').pathname));
    render(<App />);
    
    const topbar = screen.getByText('~/honey-do').closest('.topbar');
    expect(topbar).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Menu/i })).toBeInTheDocument();
    expect(screen.queryByText(/Directions/i)).not.toBeInTheDocument();
  });

  it('shows Directions when chosen in menu and hides it when Close is clicked', async () => {
    globalThis.fetch = vi.fn().mockImplementation((req) => mockFetch(new URL(req as string, 'http://localhost').pathname));
    render(<App />);

    // Open menu
    fireEvent.click(screen.getByRole('button', { name: /Menu/i }));
    
    // Click Directions
    fireEvent.click(screen.getByRole('button', { name: /Directions/i }));
    
    // Verify Directions component is visible
    expect(screen.getByRole('heading', { name: /Directions/i })).toBeInTheDocument();
    expect(screen.getByText(/Paste your token into the Token field/i)).toBeInTheDocument();

    // Click Close
    fireEvent.click(screen.getByRole('button', { name: /Close/i }));
    
    // Verify Directions is hidden
    expect(screen.queryByRole('heading', { name: /Directions/i })).not.toBeInTheDocument();
  });
});