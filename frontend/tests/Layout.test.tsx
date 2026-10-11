import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockFetch = (data: Record<string, any>) => {
  return vi.fn().mockImplementation((url: string) => {
    const responseBody = data[url] || { error: 'Not Found' };
    return Promise.resolve(new Response(JSON.stringify(responseBody), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
  });
};

describe('Layout', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('should have a topbar containing the brand and token controls', async () => {
    globalThis.fetch = mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const topbar = tokenInput.closest('.topbar');
    expect(topbar).toBeInTheDocument();
    expect(topbar).toContainElement(screen.getByText('~/honey-do'));
    expect(screen.getByText('~/honey-do')).toHaveClass('brand');
    expect(screen.getByRole('button', { name: /Load/i })).toBeInTheDocument();
  });

  it('should organize board columns within a board container', async () => {
    globalThis.fetch = mockFetch({
      '/api/dashboard': { 
        todo: [{ id: 1, title: 'T1', group: 1, status: 'open', priority: 'normal', due: null }],
        in_progress: [{ id: 2, title: 'T2', group: 1, status: 'in_progress', priority: 'normal', due: null }],
        completed: [{ id: 3, title: 'T3', status: 'done', priority: 'normal', due: null }],
      },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const board = document.querySelector('.board');
    expect(board).toBeInTheDocument();
    
    const columns = document.querySelectorAll('.column');
    expect(columns).toHaveLength(3);
  });

  it('should apply card and urgent classes to tickets', async () => {
    globalThis.fetch = mockFetch({
      '/api/dashboard': {
        todo: [
          { id: 1, title: 'Urgent Ticket', group: 0, status: 'open', priority: 'urgent', due: null },
          { id: 2, title: 'Normal Ticket', group: 1, status: 'open', priority: 'normal', due: null },
        ],
        in_progress: [],
        completed: [],
      },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const urgentTicket = screen.getByText('Urgent Ticket').closest('.card');
    expect(urgentTicket).toBeInTheDocument();
    expect(urgentTicket).toHaveClass('urgent');

    const normalTicket = screen.getByText('Normal Ticket').closest('.card');
    expect(normalTicket).toBeInTheDocument();
    expect(normalTicket).not.toHaveClass('urgent');
  });
});