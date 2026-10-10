import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(() => {
  cleanup();
});

const mockFetch = (responses: Record<string, any>) => {
  globalThis.fetch = vi.fn().mockImplementation((url) => {
    const path = url.toString();
    for (const key in responses) {
      if (path.includes(key)) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(responses[key]),
        });
      }
    }
    return Promise.resolve({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: 'Not Found' }),
    });
  });
};

describe('App Menu and Directions', () => {
  it('shows the Menu component in the topbar and hides Directions by default', () => {
    mockFetch({
      '/api/me': { user: 'her' },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    const topbar = screen.getByLabelText('Menu').parentElement;
    expect(topbar).toHaveClass('topbar');
    expect(screen.getByLabelText('Menu')).toBeInTheDocument();
    expect(screen.queryByText('Directions')).not.toBeInTheDocument();
    expect(screen.queryByText('Paste your token into the Token field')).not.toBeInTheDocument();
  });

  it('shows Directions when chosen in menu and hides it when Close is clicked', () => {
    mockFetch({
      '/api/me': { user: 'her' },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    // Open menu
    fireEvent.click(screen.getByLabelText('Menu'));
    
    // Click Directions
    fireEvent.click(screen.getByText('Directions'));
    
    // Verify Directions component is visible
    expect(screen.getByText('Directions')).toBeInTheDocument();
    expect(screen.getByText('Paste your token into the Token field')).toBeInTheDocument();
    
    // Click Close
    fireEvent.click(screen.getByText('Close'));
    
    // Verify Directions component is hidden
    expect(screen.queryByText('Directions')).not.toBeInTheDocument();
    expect(screen.queryByText('Paste your token into the Token field')).not.toBeInTheDocument();
  });
});