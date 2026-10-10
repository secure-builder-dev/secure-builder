import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockFetch = (responses: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const path = new URL(url, 'http://localhost').pathname;
    if (responses[path]) {
      return Promise.resolve(new Response(JSON.stringify(responses[path]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    } else {
      return Promise.resolve(new Response(JSON.stringify({ error: 'Not Found' }), {
        status: 404,
      }));
    }
  });
};

describe('App Household Board', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('calls fetchBoard and displays HouseholdBoard content when Load is pressed', async () => {
    const boardData = {
      todo: [{ id: 1, title: 'Household Task 1', assigned_to: 'him' }],
      in_progress: [{ id: 2, title: 'Household Task 2', assigned_to: 'her' }],
      completed: [{ id: 3, title: 'Household Task 3', assigned_to: 'him' }],
    };

    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': boardData,
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(await screen.findByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('Household Task 1')).toBeInTheDocument();
    expect(screen.getAllByText('for him')).toHaveLength(2);
    expect(screen.getByText('Household Task 2')).toBeInTheDocument();
    expect(screen.getByText('for her')).toBeInTheDocument();
    expect(screen.getByText('Household Task 3')).toBeInTheDocument();
  });

  it('leaves household board empty and page intact when /api/board fails', async () => {
    globalThis.fetch = vi.fn((url) => {
      const path = new URL(url, 'http://localhost').pathname;
      if (path === '/api/board') {
        return Promise.resolve(new Response(null, { status: 500 }));
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Household board/i)).not.toBeInTheDocument();
  });

  it('leaves household board empty when /api/board returns malformed data', async () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { wrong_key: 'bad_data' },
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(screen.queryByText(/Household board/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
  });
});