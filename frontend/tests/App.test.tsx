import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockToken = 'test-token';

const mockDashboard = {
  todo: [
    { id: 1, title: 'Todo 1', priority: 'urgent', due: '2026-01-01', status: 'open', group: 0 },
    { id: 2, title: 'Todo 2', priority: 'normal', due: '2026-01-10', status: 'acknowledged', group: 2 },
  ],
  in_progress: [
    { id: 3, title: 'Progress 1', priority: 'low', due: '2026-01-05', status: 'in_progress', group: 1 },
  ],
  completed: [
    { id: 4, title: 'Done 1', priority: 'normal', due: '2026-01-01', status: 'done' },
  ],
};

const mockFiled = {
  tickets: [
    { id: 5, title: 'Filed 1', priority: 'normal', due: '2026-01-01', status: 'done' },
    { id: 6, title: 'Filed 2', priority: 'normal', due: '2026-01-01', status: 'open' },
  ],
};

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it('clause 1: sends Authorization header to correct endpoints', async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({})));
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/dashboard', expect.objectContaining({
        headers: { 'Authorization': `Bearer ${mockToken}` }
      }));
    });
  });

  it('clause 2: token input is password type and not persisted', async () => {
    render(<App />);
    const tokenInput = screen.getByLabelText(/Token/i);
    expect(tokenInput).toHaveAttribute('type', 'password');

    fireEvent.change(tokenInput, { target: { value: mockToken } });
    expect(window.localStorage.getItem('token')).toBeNull();
    expect(window.sessionStorage.getItem('token')).toBeNull();

    expect(globalThis.fetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));
  });

  it('clause 3: new ticket form inputs and submission', async () => {
    render(<App />);
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Details/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Due/i)).toBeInTheDocument();

    const prioritySelect = screen.getByLabelText(/Priority/i);
    expect(prioritySelect).toHaveValue('normal');

    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 201 }));
    fireEvent.click(screen.getByRole('button', { name: /File ticket/i }));
    
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/tickets', expect.objectContaining({ method: 'POST' }));
    });
  });

  it('clause 4: board displays columns and ticket details', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockDashboard)));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockFiled)));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/To Do/i)).toBeInTheDocument();
      expect(screen.getByText(/In Progress/i)).toBeInTheDocument();
      expect(screen.getByText(/Completed/i)).toBeInTheDocument();
      expect(screen.getByText('Todo 1')).toBeInTheDocument();
      expect(screen.getByText('urgent')).toBeInTheDocument();
      expect(screen.getByText(/2026-01-01/)).toBeInTheDocument();
    });
  });

  it('clause 5: urgent class applied to group 0', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockDashboard)));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockFiled)));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      const ticket = screen.getByText('Todo 1').closest('div');
      expect(ticket).toHaveClass('urgent');
    });
  });

  it('clause 6: board action buttons and status updates', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockDashboard)));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockFiled)));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Acknowledge/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Start/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Done/i })).toBeInTheDocument();
    });

    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify({})));
    fireEvent.click(screen.getByRole('button', { name: /Acknowledge/i }));
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/status'), expect.objectContaining({ method: 'POST' }));
    });
  });

  it('clause 7: filed tickets and close/reopen buttons', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockDashboard)));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockFiled)));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/Tickets I filed/i)).toBeInTheDocument();
      expect(screen.getByText('Filed 1')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Close/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reopen/i })).toBeInTheDocument();
    });
  });

  it('clause 8: error messages for 401 and others', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(null, { status: 401 }));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));
    await waitFor(() => expect(screen.getByText(/Wrong token/i)).toBeInTheDocument());

    (globalThis.fetch as any).mockResolvedValueOnce(new Response('Secret Error', { status: 500 }));
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));
    await waitFor(() => {
      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
      expect(screen.queryByText('Secret Error')).not.toBeInTheDocument();
    });
  });

  it('clause 9: no XSS via React text', async () => {
    const xssDashboard = {
      todo: [{ id: 1, title: '<img src=x onerror=alert(1)>', priority: 'normal', due: null, status: 'open', group: 2 }],
      in_progress: [],
      completed: [],
    };
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(xssDashboard)));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify({ tickets: [] })));

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      const element = screen.getByText('<img src=x onerror=alert(1)>');
      expect(element).toBeInTheDocument();
      expect(element.textContent).toBe('<img src=x onerror=alert(1)>');
    });
  });
});