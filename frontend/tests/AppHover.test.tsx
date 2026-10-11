import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(() => {
  cleanup();
});

const mockTickets = {
  todo: [
    {
      id: 1,
      title: 'Todo Ticket',
      details: 'Todo Details',
      priority: 'normal',
      due: null,
      status: 'open',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      group: 1
    }
  ],
  in_progress: [
    {
      id: 2,
      title: 'Progress Ticket',
      details: 'Progress Details',
      priority: 'urgent',
      due: '2026-01-10',
      status: 'in_progress',
      filed_by: 'him',
      assigned_to: 'her',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      group: 0
    }
  ],
  completed: [
    {
      id: 3,
      title: 'Completed Ticket',
      details: 'Completed Details',
      priority: 'low',
      due: '2026-01-01',
      status: 'done',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z'
    }
  ]
};

const setupFetchMock = () => {
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/dashboard') {
      return Promise.resolve(new Response(JSON.stringify(mockTickets)));
    } else if (url === '/api/filed') {
      return Promise.resolve(new Response(JSON.stringify({ tickets: [] })));
    } else if (url === '/api/board') {
      return Promise.resolve(new Response(JSON.stringify(mockTickets)));
    } else if (url === '/api/me') {
      return Promise.resolve(new Response(JSON.stringify({ user: 'her' })));
    } else if (url === '/api/tickets') {
      return Promise.resolve(new Response(JSON.stringify({}), { status: 201 }));
    } else if (url.includes('/api/tickets/')) {
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    }
    return Promise.resolve(new Response(null, { status: 404 }));
  });
};

describe('App HoverCard Integration', () => {
  it('shows tooltip details when hovering a ticket title in To Do column', async () => {
    setupFetchMock();
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Todo Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Todo Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Filed by her');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Assigned to him');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Created 2026-01-01');
  });

  it('shows tooltip details when hovering a ticket title in In Progress column', async () => {
    setupFetchMock();
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Progress Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Progress Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Filed by him');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Assigned to her');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Created 2026-01-01');
  });

  it('shows tooltip details when hovering a ticket title in Completed column', async () => {
    setupFetchMock();
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Completed Ticket');
    fireEvent.mouseEnter(title);

    expect(screen.getByRole('tooltip')).toHaveTextContent('Completed Details');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Filed by her');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Assigned to him');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Created 2026-01-01');
  });

  it('hides tooltip when mouse leaves the title', async () => {
    setupFetchMock();
    render(<App />);
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));

    const title = await screen.findByText('Todo Ticket');
    fireEvent.mouseEnter(title);
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    
    fireEvent.mouseLeave(title);
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('does not break existing App functionality (smoke test)', async () => {
    setupFetchMock();
    render(<App />);
    
    expect(screen.getByText('~/honey-do')).toBeInTheDocument();
    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
    expect(screen.getByText('New Ticket')).toBeInTheDocument();
    
    fireEvent.change(screen.getByLabelText(/Token/i), { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByText(/Load/i));
    
    expect(await screen.findByText('Todo Ticket')).toBeInTheDocument();
    expect(screen.getByText('Tickets I Filed')).toBeInTheDocument();
  });
});