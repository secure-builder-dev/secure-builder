import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(() => {
  cleanup();
});

const mockFetch = (dataMap: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const data = dataMap[url];
    if (data) {
      return Promise.resolve(new Response(JSON.stringify(data), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    }
    return Promise.resolve(new Response(JSON.stringify({ error: 'Not Found' }), { status: 404 }));
  });
};

describe('Layout', () => {
  it('should wrap token field and load button in an element with class topbar', () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });
    render(<App />);
    const tokenInput = screen.getByLabelText(/token/i);
    const loadButton = screen.getByRole('button', { name: /load/i });
    expect(tokenInput.parentElement).toHaveClass('topbar');
    expect(loadButton.parentElement).toHaveClass('topbar');
  });

  it('should have board columns inside an element with class board and each column with class column', () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });
    render(<App />);
    const board = screen.getByText(/to do/i).closest('.board');
    expect(board).toBeInTheDocument();
    
    const columns = board?.querySelectorAll('.column');
    expect(columns).toHaveLength(3);
  });

  it('should give every ticket on the board class card and group 0 tickets class urgent', async () => {
    mockFetch({
      '/api/dashboard': {
        todo: [
          { id: 1, title: 'Urgent Ticket', group: 0, priority: 'urgent', due: '2025-01-01', status: 'open' },
          { id: 2, title: 'Normal Ticket', group: 1, priority: 'normal', due: '2025-01-10', status: 'open' },
        ],
        in_progress: [],
        completed: [],
      },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });
    
    render(<App />);
    
    const tokenInput = screen.getByLabelText(/token/i);
    const loadButton = screen.getByRole('button', { name: /load/i });
    
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(loadButton);

    await vi.waitFor(() => {
      expect(screen.getByText('Urgent Ticket')).toBeInTheDocument();
    });
    
    const urgentTicket = screen.getByText('Urgent Ticket').closest('.card');
    const normalTicket = screen.getByText('Normal Ticket').closest('.card');
    
    expect(urgentTicket).toHaveClass('card', 'urgent');
    expect(normalTicket).toHaveClass('card');
    expect(normalTicket).not.toHaveClass('urgent');
  });

  it('should use a mock fetch that handles all required API endpoints', () => {
    const endpoints = ['/api/dashboard', '/api/filed', '/api/board', '/api/me'];
    const dataMap: Record<string, any> = {};
    endpoints.forEach(url => dataMap[url] = {});
    
    mockFetch(dataMap);
    
    return Promise.all(endpoints.map(url => 
      fetch(url).then(res => {
        expect(res).toBeInstanceOf(Response);
        return res.json();
      })
    ));
  });
});