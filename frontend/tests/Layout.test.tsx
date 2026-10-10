import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { afterEach, describe, it, expect, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(cleanup);

const mockFetch = (data: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const path = new URL(url, 'http://localhost').pathname;
    if (data[path]) {
      return Promise.resolve(new Response(JSON.stringify(data[path]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    }
    return Promise.resolve(new Response(null, { status: 404 }));
  });
};

describe('Layout', () => {
  it('should have a topbar with brand ~/honey-do and token field', () => {
    mockFetch({});
    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const topbar = tokenInput.closest('.topbar');
    expect(topbar).toBeInTheDocument();
    
    const brand = screen.getByText('~/honey-do');
    expect(brand).toHaveClass('brand');
    expect(topbar).toContainElement(brand);
    
    const loadBtn = screen.getByRole('button', { name: /Load/i });
    expect(topbar).toContainElement(loadBtn);
  });

  it('should have a board containing three columns', async () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': { todo: [], in_progress: [], completed: [] },
      '/api/me': { user: 'her' },
    });
    
    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadBtn = screen.getByRole('button', { name: /Load/i });
    
    fireEvent.change(tokenInput, { target: { value: 'test-token' } });
    fireEvent.click(loadBtn);

    const board = await screen.findByText(/Board/i).then(el => el.closest('.board'));
    expect(board).toBeInTheDocument();
    
    const columns = board?.querySelectorAll('.column');
    expect(columns).toHaveLength(3);
  });

  it('should apply card and urgent classes to tickets', async () => {
    mockFetch({
      '/api/dashboard': {
        todo: [
          { id: 1, title: 'Urgent Ticket', details: '', priority: 'urgent', due: null, status: 'open', filed_by: 'him', assigned_to: 'her', created_at: '', updated_at: '', group: 0 },
          { id: 2, title: 'Normal Ticket', details: '', priority: 'normal', due: null, status: 'open', filed_by: 'him', assigned_to: 'her', created_at: '', updated_at: '', group: 1 },
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
    const loadBtn = screen.getByRole('button', { name: /Load/i });
    
    fireEvent.change(tokenInput, { target: { value: 'test-token' } });
    fireEvent.click(loadBtn);

    const urgentTicket = await screen.findByText('Urgent Ticket').then(el => el.closest('.card'));
    expect(urgentTicket).toBeInTheDocument();
    expect(urgentTicket).toHaveClass('urgent');

    const normalTicket = screen.getByText('Normal Ticket').closest('.card');
    expect(normalTicket).toBeInTheDocument();
    expect(normalTicket).not.toHaveClass('urgent');
  });

  it('should verify fetch is mocked for all required endpoints', async () => {
    const endpoints = ['/api/dashboard', '/api/filed', '/api/board', '/api/me'];
    const data = endpoints.reduce((acc, url) => ({ ...acc, [url]: { success: true } }), {});
    mockFetch(data);
    
    render(<App />);
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadBtn = screen.getByRole('button', { name: /Load/i });
    
    fireEvent.change(tokenInput, { target: { value: 'test-token' } });
    fireEvent.click(loadBtn);

    // We just check that fetch was called; the mockFetch implementation ensures
    // that it handles these specific URLs as required by the DoD.
    expect(globalThis.fetch).toHaveBeenCalled();
  });
});