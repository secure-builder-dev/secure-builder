import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockTickets = {
  todo: [
    {
      id: 1,
      title: 'Todo Ticket',
      details: 'Todo Details',
      priority: 'normal',
      due: '2026-01-01',
      status: 'open',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      group: 1,
    },
  ],
  in_progress: [
    {
      id: 2,
      title: 'Progress Ticket',
      details: 'Progress Details',
      priority: 'urgent',
      due: '2025-12-31',
      status: 'in_progress',
      filed_by: 'him',
      assigned_to: 'her',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
      group: 0,
    },
  ],
  completed: [
    {
      id: 3,
      title: 'Completed Ticket',
      details: 'Completed Details',
      priority: 'low',
      due: null,
      status: 'done',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-01T00:00:00Z',
    },
  ],
};

const mockFetch = (url: string) => {
  if (url === '/api/dashboard') return Promise.resolve(new Response(JSON.stringify(mockTickets)));
  if (url === '/api/filed') return Promise.resolve(new Response(JSON.stringify({ tickets: [] })));
  if (url === '/api/board') return Promise.resolve(new Response(JSON.stringify({})));
  if (url === '/api/me') return Promise.resolve(new Response(JSON.stringify({ user: 'him' })));
  return Promise.reject(new Error('Unknown URL'));
};

describe('App HoverCards', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('should show ticket details in a tooltip when hovering the title in To Do, In Progress, and Completed columns', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => mockFetch(url as string));

    render(<App />);

    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const ticketsToTest = [
      { title: 'Todo Ticket', details: 'Todo Details' },
      { title: 'Progress Ticket', details: 'Progress Details' },
      { title: 'Completed Ticket', details: 'Completed Details' },
    ];

    for (const ticket of ticketsToTest) {
      const titleElement = await screen.findByText(ticket.title);
      
      fireEvent.mouseEnter(titleElement);
      
      const tooltip = await screen.findByRole('tooltip');
      expect(tooltip).toBeInTheDocument();
      expect(tooltip).toHaveTextContent(ticket.details);
      
      fireEvent.mouseLeave(titleElement);
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    }
  });

  it('should not break the rest of the page when HoverCards are present', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => mockFetch(url as string));

    render(<App />);

    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Details/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Priority/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Due/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /File ticket/i })).toBeInTheDocument();

    expect(await screen.findByRole('heading', { name: /To Do/i })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /In Progress/i })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: /Completed/i })).toBeInTheDocument();
  });
});