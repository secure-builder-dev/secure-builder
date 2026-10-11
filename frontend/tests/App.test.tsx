import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../src/App';

const mockToken = 'test-token';

const mockDashboard = {
  todo: [
    { id: 1, title: 'Todo 1', priority: 'urgent', due: '2026-01-01', status: 'open', group: 0 },
    { id: 2, title: 'Todo 2', priority: 'normal', due: '2026-01-05', status: 'acknowledged', group: 1 },
  ],
  in_progress: [
    { id: 3, title: 'Progress 1', priority: 'low', due: '2026-01-10', status: 'in_progress', group: 2 },
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

describe('App', () => {n  beforeEach(() => {
    globalThis.fetch = vi.fn();
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('clause 1 & 2: does not fetch until token entered and Load pressed', async () => {
    render(<App />);
    const tokenInput = screen.getByLabelText(/token/i);
    const loadButton = screen.getByRole('button', { name: /load/i });

    expect(globalThis.fetch).not.toHaveBeenCalled();

    fireEvent.change(tokenInput, { target: { value: mockToken } });
    expect(globalThis.fetch).not.toHaveBeenCalled();

    fireEvent.click(loadButton);
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/dashboard'), expect.objectContaining({
      headers: { Authorization: `Bearer ${mockToken}` }
    }));
  });

  it('clause 2: token is not stored in localStorage or sessionStorage', async () => {
    render(<App />);
    const tokenInput = screen.getByLabelText(/token/i);
    fireEvent.change(tokenInput, { target: { value: mockToken } });
    
    expect(localStorage.getItem('token')).toBeNull();
    expect(sessionStorage.getItem('token')).toBeNull();
  });

  it('clause 3: shows new ticket form and posts ticket', async () => {
    (globalThis.fetch as any).mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<App />);
    
    expect(screen.getByText(/new ticket/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/details/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/due/i)).toBeInTheDocument();

    const fileButton = screen.getByRole('button', { name: /file ticket/i });
    fireEvent.click(fileButton);
    
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/tickets', expect.objectContaining({ method: 'POST' }));
  });

  it('clause 4 & 5: renders board columns and urgent class', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockDashboard,
    });
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/to do/i)).toBeInTheDocument();
      expect(screen.getByText(/in progress/i)).toBeInTheDocument();
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });

    const urgentTicket = screen.getByText('Todo 1').closest('div');
    expect(urgentTicket).toHaveClass('urgent');
  });

  it('clause 6: shows correct action buttons in board', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockDashboard,
    });
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /acknowledge/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument();
    });
  });

  it('clause 7: shows filed tickets and close/reopen buttons', async () => {
    (globalThis.fetch as any).mockImplementation((url) => {
      if (url.includes('/api/filed')) return Promise.resolve({ ok: true, json: async () => mockFiled });
      return Promise.resolve({ ok: true, json: async () => mockDashboard });
    });
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/tickets i filed/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reopen/i })).toBeInTheDocument();
    });
  });

  it('clause 8: shows error messages on failure', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({ status: 401 });
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/wrong token/i)).toBeInTheDocument();
    });

    (globalThis.fetch as any).mockResolvedValueOnce({ status: 500 });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });
  });

  it('clause 9: does not use dangerouslySetInnerHTML', async () => {
    // This is a static analysis check usually, but we can verify no HTML is rendered
    // by providing HTML strings in the mock data and ensuring they are rendered as text
    const maliciousData = {
      todo: [{ id: 9, title: '<img src=x onerror=alert(1)>', priority: 'low', due: null, status: 'open', group: 2 }],
      in_progress: [],
      completed: [],
    };
    (globalThis.fetch as any).mockResolvedValue({ ok: true, json: async () => maliciousData });
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: mockToken } });
    fireEvent.click(screen.getByRole('button', { name: /load/i }));

    await waitFor(() => {
      const element = screen.getByText('<img src=x onerror=alert(1)>');
      expect(element).toBeInTheDocument();
      // If it were rendered as HTML, the text content would be empty or different
      expect(element.innerHTML).not.toContain('<img src=x');
    });
  });
});