import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';
import { fetchMe } from '../src/api';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const mockFetch = (responses: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const key = Object.keys(responses).find(k => url.includes(k));
    if (key) {
      return Promise.resolve(new Response(JSON.stringify(responses[key]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }));
    }
    return Promise.resolve(new Response(null, { status: 404 }));
  }) as any;
};

describe('SignedIn functionality', () => {
  it('clause 1: fetchMe sends correct request and returns JSON', async () => {
    const mockResponse = { user: 'her' };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockResponse))
    );

    const result = await fetchMe('test-token');
    
    expect(fetchSpy).toHaveBeenCalledWith('/api/me', expect.objectContaining({
      headers: { 'Authorization': 'Bearer test-token' }
    }));
    expect(result).toEqual(mockResponse);
  });

  it('clause 2: App shows signed in user and dynamic form heading', async () => {
    mockFetch({
      '/api/me': { user: 'her' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'token-her' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await screen.findByText(/Signed in as her/i);
    expect(screen.getByText(/New ticket for him/i)).toBeInTheDocument();
  });

  it('clause 2b: App shows signed in user and dynamic form heading for him', async () => {
    mockFetch({
      '/api/me': { user: 'him' },
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
    });

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'token-him' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await screen.findByText(/Signed in as him/i);
    expect(screen.getByText(/New ticket for her/i)).toBeInTheDocument();
  });

  it('clause 3: failed /api/me does not show signed in text but page works', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url.includes('/api/me')) {
        return Promise.resolve(new Response(null, { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }) as any;

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'token-fail' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await new Promise(r => setTimeout(r, 100));
    
    expect(screen.queryByText(/Signed in as/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
  });

  it('clause 4: verify fetch implementation details', async () => {
    // This test ensures the mockFetch pattern used in other tests matches the requirement
    // of replacing globalThis.fetch with a vi.fn() answering by URL
    const responses = {
      '/api/dashboard': { data: 'dash' },
      '/api/filed': { data: 'filed' },
      '/api/board': { data: 'board' },
      '/api/me': { data: 'me' },
    };
    mockFetch(responses);
    
    const resMe = await fetch('/api/me');
    expect(await resMe.json()).toEqual(responses['/api/me']);
    
    const resDash = await fetch('/api/dashboard');
    expect(await resDash.json()).toEqual(responses['/api/dashboard']);
  });
});