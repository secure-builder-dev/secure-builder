import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(() => {
  cleanup();
});

const mockFetch = (data: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const path = url.toString();
    if (path.includes('/api/dashboard')) return Promise.resolve(new Response(JSON.stringify(data.dashboard || {})));
    if (path.includes('/api/filed')) return Promise.resolve(new Response(JSON.stringify(data.filed || {})));
    if (path.includes('/api/board')) return Promise.resolve(new Response(JSON.stringify(data.board || {})));
    if (path.includes('/api/me')) return Promise.resolve(new Response(JSON.stringify(data.me || {})));
    return Promise.resolve(new Response(JSON.stringify({}), { status: 404 }));
  });
};

describe('App HoverCard Integration', () => {
  const mockTickets = {
    dashboard: {
      todo: [
        { id: 1, title: 'Todo Ticket', details: 'Todo Details', priority: 'normal', due: '2026-01-01', status: 'open', group: 1, filed_by: 'her', assigned_to: 'him', created_at: '2026-01-01T00:00:00Z' }
      ],
      in_progress: [
        { id: 2, title: 'Progress Ticket', details: 'Progress Details', priority: 'urgent', due: '2026-01-01', status: 'in_progress', group: 0, filed_by: 'him', assigned_to: 'her', created_at: '2026-01-01T00:00:00Z' }
      ],
      completed: [
        { id: 3, title: 'Done Ticket', details: 'Done Details', priority: 'low', due: '2026-01-01', status: 'done', filed_by: 'her', assigned_to: 'him', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }
      ]
    },
    filed: {
      tickets: [
        { id: 4, title: 'Filed Ticket', details: 'Filed Details', priority: 'normal', due: '2026-01-01', status: 'done', filed_by: 'him', assigned_to: 'her', created_at: '2026-01-01T00:00:00Z' }
      ]
    }
  };

  it('shows ticket details in a tooltip when hovering the title in To Do column', async () => {
    mockFetch(mockTickets);
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Todo Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Todo Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Filed by her');
  });

  it('shows ticket details in a tooltip when hovering the title in In Progress column', async () => {
    mockFetch(mockTickets);
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Progress Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Progress Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Assigned to her');
  });

  it('shows ticket details in a tooltip when hovering the title in Completed column', async () => {
    mockFetch(mockTickets);
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Done Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Done Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Created 2026-01-01');
  });

  it('verifies that other page elements are still present and functional', async () => {
    mockFetch(mockTickets);
    render(<App />);
    
    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
    expect(screen.getByText(/New ticket/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByText(/File ticket/i)).toBeInTheDocument();
    expect(screen.getByText(/Tickets I filed/i)).toBeInTheDocument();
  });

  it('verifies that the fetch mock handles all required API endpoints', async () => {
    const data = { dashboard: {}, filed: {}, board: {}, me: {} };
    mockFetch(data);
    
    const endpoints = ['/api/dashboard', '/api/filed', '/api/board', '/api/me'];
    for (const url of endpoints) {
      const res = await fetch(url);
      expect(res.status).toBe(200);
    }
  });
});