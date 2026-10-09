import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App.tsx';

const mockToken = 'test-token';

const mockDashboard = {
  todo: [
    { id: 1, title: 'Todo 1', priority: 'urgent', due: '2026-01-01', status: 'open', group: 0 },
    { id: 2, title: 'Todo 2', priority: 'normal', due: '2026-01-10', status: 'acknowledged', group: 1 },
  ],
  in_progress: [
    { id: 3, title: 'Doing 1', priority: 'low', due: '2026-01-15', status: 'in_progress', group: 2 },
  ],
  completed: [
    { id: 4, title: 'Done 1', priority: 'normal', due: '2026-01-01', status: 'done', updated_at: new Date().toISOString() },
  ],
};

const mockFiled = {
  tickets: [
    { id: 5, title: 'Filed 1', priority: 'normal', due: null, status: 'done', updated_at: new Date().toISOString() },
    { id: 6, title: 'Filed 2', priority: 'normal', due: null, status: 'open', updated_at: new Date().toISOString() },
  ],
};

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.stubGlobal('localStorage', { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn() });
    vi.stubGlobal('sessionStorage', { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn() });
  });

  it('clause 1: sends token as Bearer to all API endpoints', async () => {
    render(<App />);
    const tokenInput = screen.getByLabelText(/Token/i);
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.change(tokenInput, { target: { value: mockToken } });

    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    fireEvent.click(loadButton);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/dashboard', expect.objectContaining({
        headers: { 'Authorization': `Bearer ${mockToken}` }
      }));
    });
  });

  it('clause 2: token input is password type and not stored in local/session storage', async () => {
    render(<App />);
    const tokenInput = screen.getByLabelText(/Token/i);
    expect(tokenInput).toHaveAttribute('type', 'password');

    fireEvent.change(tokenInput, { target: { value: mockToken } });
    expect(localStorage.setItem).not.toHaveBeenCalled();
    expect(sessionStorage.setItem).not.toHaveBeenCalled();
  });

  it('clause 3: new ticket form inputs and submission', async () => {
    render(<App />);
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
    const titleInput = screen.getByLabelText(/Title/i);
    const detailsInput = screen.getByLabelText(/Details/i);
    const prioritySelect = screen.getByLabelText(/Priority/i);
    const dueInput = screen.getByLabelText(/Due/i);
    const submitBtn = screen.getByRole('button', { name: /File ticket/i });

    expect(prioritySelect).toBeWithinHTML('option', 'low');
    expect(prioritySelect).toBeWithinHTML('option', 'normal');
    expect(prioritySelect).toBeWithinHTML('option', 'urgent');
    expect(dueInput).toHaveAttribute('type', 'date');

    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ id: 10 }), { status: 201 }));
    fireEvent.change(titleInput, { target: { value: 'Task X' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/tickets', expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Task X')
      }));
    });
  });

  it('clause 4: board columns display tickets with title, priority, and due date', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify(mockDashboard), { status: 200 }));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/To Do/i)).toBeInTheDocument();
      expect(screen.getByText(/In Progress/i)).toBeInTheDocument();
      expect(screen.getByText(/Completed/i)).toBeInTheDocument();
      
      const ticket = screen.getByText('Todo 1').closest('div');
      expect(ticket).toHaveTextContent('Todo 1');
      expect(ticket).toHaveTextContent('urgent');
      expect(ticket).toHaveTextContent('2026-01-01');
    });
  });

  it('clause 5: group 0 tickets have urgent class', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify(mockDashboard), { status: 200 }));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      const urgentTicket = screen.getByText('Todo 1').closest('div');
      expect(urgentTicket).toHaveClass('urgent');
      const normalTicket = screen.getByText('Todo 2').closest('div');
      expect(normalTicket).not.toHaveClass('urgent');
    });
  });

  it('clause 6: status buttons and their API calls', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify(mockDashboard), { status: 200 }));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      const ackBtn = screen.getByRole('button', { name: /Acknowledge/i });
      const startBtn = screen.getByRole('button', { name: /Start/i });
      const doneBtn = screen.getByRole('button', { name: /Done/i });

      (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
      fireEvent.click(ackBtn);
      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/status'), expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('acknowledged')
      }));
    });
  });

  it('clause 7: filed tickets section and close/reopen buttons', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockDashboard), { status: 200 }));
    (globalThis.fetch as any).mockResolvedValueOnce(new Response(JSON.stringify(mockFiled), { status: 200 }));
    
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
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/Wrong token/i)).toBeInTheDocument();
    });

    (globalThis.fetch as any).mockResolvedValueOnce(new Response('Internal Error', { status: 500 }));
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
      expect(screen.queryByText('Internal Error')).not.toBeInTheDocument();
    });
  });

  it('clause 9: no dangerouslySetInnerHTML or eval', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({
      todo: [{ id: 9, title: '<img src=x onerror=alert(1)>', priority: 'low', due: null, status: 'open', group: 2 }],
      in_progress: [],
      completed: []
    }), { status: 200 }));
    
    render(<App />);
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    await waitFor(() => {
      const element = screen.getByText('<img src=x onerror=alert(1)>');
      expect(element.innerHTML).not.toContain('<img src=x');
    });
  });
});

expect.extend({
  toBeWithinHTML(received, selector, text) {
    const matches = received.querySelectorAll(selector);
    const found = Array.from(matches).some(el => el.textContent === text);
    return { pass: found, message: () => `expected ${received} to contain ${selector} with text ${text}` };
  },
});