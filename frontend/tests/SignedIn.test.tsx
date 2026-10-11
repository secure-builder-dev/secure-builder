import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import { fetchMe } from '../src/api';

const mockFetch = vi.fn();

const setupFetch = (responses: Record<string, any>) => {
  globalThis.fetch = mockFetch;
  mockFetch.mockImplementation((url, options) => {
    const path = typeof url === 'string' ? url : '';
    if (responses[path]) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(responses[path]),
      });
    }
    return Promise.resolve({
      ok: false,
      status: 404,
    });
  });
};

describe('fetchMe', () => {
  it('sends GET /api/me with Authorization header and returns JSON', async () => {
    globalThis.fetch = mockFetch;
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ user: 'her' }),
    });

    const token = 'test-token';
    const result = await fetchMe(token);

    expect(mockFetch).toHaveBeenCalledWith('/api/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual({ user: 'her' });
  });
});

describe('SignedIn UI', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('shows Signed in as her and New ticket for him when user is her', async () => {
    setupFetch({
      '/api/me': { user: 'her' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadButton = screen.getByRole('button', { name: /Load/i });

    fireEvent.change(tokenInput, { target: { value: 'token-her' } });
    fireEvent.click(loadButton);

    expect(await screen.findByText(/Signed in as her/i)).toBeInTheDocument();
    expect(screen.getByText(/New ticket for him/i)).toBeInTheDocument();
  });

  it('shows Signed in as him and New ticket for her when user is him', async () => {
    setupFetch({
      '/api/me': { user: 'him' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadButton = screen.getByRole('button', { name: /Load/i });

    fireEvent.change(tokenInput, { target: { value: 'token-him' } });
    fireEvent.click(loadButton);

    expect(await screen.findByText(/Signed in as him/i)).toBeInTheDocument();
    expect(screen.getByText(/New ticket for her/i)).toBeInTheDocument();
  });

  it('handles failed /api/me gracefully', async () => {
    globalThis.fetch = mockFetch;
    mockFetch.mockImplementation((url) => {
      if (url === '/api/me') return Promise.resolve({ ok: false, status: 500 });
      return Promise.resolve({
        ok: true,
        json: async () => ({ todo: [], in_progress: [], completed: [] }),
      });
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadButton = screen.getByRole('button', { name: /Load/i });

    fireEvent.change(tokenInput, { target: { value: 'token-fail' } });
    fireEvent.click(loadButton);

    await new Promise(r => setTimeout(r, 50));
    expect(screen.queryByText(/Signed in as/i)).not.toBeInTheDocument();
    expect(screen.getByText(/New Ticket/i)).toBeInTheDocument();
  });
});