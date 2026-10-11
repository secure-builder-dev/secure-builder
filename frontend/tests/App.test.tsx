import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockTickets = [
  {
    id: 1,
    title: 'Urgent Task',
    priority: 'urgent',
    due: '2026-01-01',
    status: 'open',
    group: 0,
  },
  {
    id: 2,
    title: 'Normal Task',
    priority: 'normal',
    due: '2026-01-10',
    status: 'acknowledged',
    group: 2,
  },
  {
    id: 3,
    title: 'In Progress Task',
    priority: 'low',
    due: null,
    status: 'in_progress',
    group: 2,
  },
  {
    id: 4,
    title: 'Completed Task',
    priority: 'normal',
    due: '2026-01-01',
    status: 'done',
    group: 2,
  },
];

const mockFiledTickets = [
  {
    id: 5,
    title: 'My Filed Ticket',
    priority: 'normal',
    due: null,
    status: 'done',
  },
];

describe('App', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  afterEach(cleanup);

  it('clause 1 & 2: requires token and Load button to fetch', async () => {
    render(<App />);
    
    const tokenInput = screen.getByLabelText(/token/i);
    fireEvent.change(tokenInput, { target: { value: 'test-token' } });
    
    expect(globalThis.fetch).not.toHaveBeenCalled();
    
    const loadButton = screen.getByRole('button', { name: /load/i });
    fireEvent.click(loadButton);
    
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/dashboard', expect.objectContaining({
        headers: { 'Authorization': 'Bearer test-token' }
      }));
    });
  });

  it('clause 2: does not use localStorage or sessionStorage', async () => {
    const spyLocal = vi.spyOn(Storage.prototype, 'setItem');
    const spySession = vi.spyOn(Storage.prototype, 'setItem');
    
    render(<App />);
    const tokenInput = screen.getByLabelText(/token/i);
    fireEvent.change(tokenInput, { target: { value: 'secret' } });
    
    expect(spyLocal).not.toHaveBeenCalled();
    expect(spySession).not.toHaveBeenCalled();
  });

  it('clause 3: shows new ticket form and posts data', async () => {
    render(<App />);
    
    expect(screen.getByText(/new ticket/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/details/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/due/i)).toBeInTheDocument();
    
    const titleInput = screen.getByLabelText(/title/i);
    fireEvent.change(titleInput, { target: { value: 'New Task' } });

    const fileButton = screen.getByRole('button', { name: /file ticket/i });
    fireEvent.click(fileButton);
    
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/tickets', expect.objectContaining({
        method: 'POST'
      }));
    });
  });

  it('clause 4 & 5: renders board columns and urgent class', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ todo: mockTickets.slice(0, 2), in_progress: [mockTickets[2]], completed: [mockTickets[3]] }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /to do/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /in progress/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /completed/i })).toBeInTheDocument();
    });

    const urgentTicket = screen.getByText('Urgent Task').closest('div');
    expect(urgentTicket).toHaveClass('urgent');
  });

  it('clause 6: shows correct action buttons in board', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ todo: mockTickets.slice(0, 2), in_progress: [mockTickets[2]], completed: [] }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /acknowledge/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });
  });

  it('clause 7: shows filed tickets and close/reopen buttons', async () => {
    (globalThis.fetch as any).mockImplementation((url) => {
      if (url === '/api/filed') return Promise.resolve({ ok: true, json: async () => ({ tickets: mockFiledTickets }) });
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/tickets i filed/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reopen/i })).toBeInTheDocument();
    });
  });

  it('clause 8: handles 401 and other errors', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ ok: false, status: 401 });
    
    render(<App />);
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/wrong token/i)).toBeInTheDocument();
    });

    (globalThis.fetch as any).mockResolvedValueOnce({ ok: false, status: 500 });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  it('clause 9: does not use dangerouslySetInnerHTML', async () => {
    const payload = { 
      todo: [{ id: 9, title: '<b>Bold</b>', priority: 'low', due: null, status: 'open', group: 2 }],
      in_progress: [],
      completed: []
    };
    (globalThis.fetch as any).mockResolvedValue({ ok: true, json: async () => payload });

    render(<App />);
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: 'tok' } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      const element = screen.getByText('<b>Bold</b>');
      expect(element.innerHTML).not.toBe('Bold');
      expect(element.textContent).toBe('<b>Bold</b>');
    });
  });
});