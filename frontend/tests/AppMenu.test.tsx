import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockFetch = (url: string) => {
  const responses: Record<string, any> = {
    '/api/dashboard': { todo: [], in_progress: [], completed: [] },
    '/api/filed': { tickets: [] },
    '/api/board': { todo: [], in_progress: [], completed: [] },
    '/api/me': { user: 'her' },
  };

  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(responses[url] || {}),
  });
};

describe('App Menu and Directions', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('shows the Menu component in the topbar and no Directions section initially', () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => mockFetch(url as string));
    render(<App />);
    
    const topbar = document.querySelector('.topbar');
    expect(topbar).toBeInTheDocument();
    
    const menuButton = screen.getByRole('button', { name: /menu/i });
    expect(menuButton).toBeInTheDocument();
    expect(topbar).toContainElement(menuButton);
    
    expect(screen.queryByText('Directions')).not.toBeInTheDocument();
  });

  it('shows Directions when chosen in menu and hides it when Close is clicked', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => mockFetch(url as string));
    render(<App />);

    // Open menu
    fireEvent.click(screen.getByRole('button', { name: /menu/i }));
    
    // Choose Directions
    fireEvent.click(screen.getByRole('button', { name: 'Directions' }));
    
    // Verify Directions section is visible
    expect(screen.getByText('Directions')).toBeInTheDocument();
    expect(screen.getByText('Paste your token into the Token field and press Load.')).toBeInTheDocument();

    // Click Close
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    // Verify Directions section is hidden
    expect(screen.queryByText('Directions')).not.toBeInTheDocument();
  });
});