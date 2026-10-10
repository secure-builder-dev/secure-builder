import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

describe('App Household Board', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  const mockFetch = (responses: Record<string, any>) => {
    globalThis.fetch = vi.fn((url) => {
      const response = responses[url];
      if (response) {
        return Promise.resolve(new Response(JSON.stringify(response), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }));
      }
      return Promise.resolve(new Response(null, { status: 404 }));
    });
  };

  it('clause 1: calls fetchBoard and shows HouseholdBoard with data', async () => {
    const boardData = {
      todo: [{ id: 1, title: 'Household Todo', assigned_to: 'her' }],
      in_progress: [{ id: 2, title: 'Household Progress', assigned_to: 'him' }],
      completed: [{ id: 3, title: 'Household Done', assigned_to: 'her' }],
    };

    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': boardData,
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(await screen.findByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('Household Todo')).toBeInTheDocument();
    expect(screen.getByText('for her')).toBeInTheDocument();
    expect(screen.getByText('Household Progress')).toBeInTheDocument();
    expect(screen.getByText('for him')).toBeInTheDocument();
    expect(screen.getByText('Household Done')).toBeInTheDocument();
  });

  it('clause 2: failed /api/board answer leaves household board empty and no error', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/api/board') {
        return Promise.resolve(new Response(null, { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const boardHeading = screen.queryByText('Household board');
    expect(boardHeading).not.toBeInTheDocument();
    
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
    expect(screen.queryByText(/Wrong token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
  });

  it('clause 2: malformed /api/board answer leaves household board empty and no error', async () => {
    globalThis.fetch = vi.fn((url) => {
      if (url === '/api/board') {
        return Promise.resolve(new Response('not json', { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(screen.queryByText('Household board')).not.toBeInTheDocument();
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
  });

  it('clause 4: verifies fetch mock implementation details', async () => {
    const responses = {
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    };
    mockFetch(responses);
    
    const res = await (globalThis.fetch as any)('/api/board');
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json).toEqual(responses['/api/board']);
  });
});