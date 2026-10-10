import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import * as api from '../src/api';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Signed In User', () => {
  const mockFetch = (responses: Record<string, any>) => {
    globalThis.fetch = vi.fn().mockImplementation((url, options) => {
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

  it('fetchMe sends correct request and returns JSON', async () => {
    const token = 'test-token';
    const mockUser = { user: 'her' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockUser),
    });

    const result = await api.fetchMe(token);

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/me', expect.objectContaining({
      headers: { 'Authorization': `Bearer ${token}` },
    }));
    expect(result).toEqual(mockUser);
  });

  it('shows signed in text and correct form heading for her', async () => {
    mockFetch({
      '/api/me': { user: 'her' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
    });

    render(<App />);
    
    expect(screen.getByText('New ticket')).toBeInTheDocument();

    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'token-her' } });
    fireEvent.click(screen.getByText('Load'));

    expect(await screen.findByText('Signed in as her')).toBeInTheDocument();
    expect(screen.getByText('New ticket for him')).toBeInTheDocument();
  });

  it('shows signed in text and correct form heading for him', async () => {
    mockFetch({
      '/api/me': { user: 'him' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'token-him' } });
    fireEvent.click(screen.getByText('Load'));

    expect(await screen.findByText('Signed in as him')).toBeInTheDocument();
    expect(screen.getByText('New ticket for her')).toBeInTheDocument();
  });

  it('handles failed /api/me gracefully', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url === '/api/me') return Promise.resolve({ ok: false, status: 500 });
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'bad-token' } });
    fireEvent.click(screen.getByText('Load'));

    expect(screen.queryByText(/Signed in as/i)).not.toBeInTheDocument();
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
  });
});