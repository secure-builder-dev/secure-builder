import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

afterEach(() => {
  cleanup();
});

const mockFetch = (data: Record<string, any>) => {
  globalThis.fetch = vi.fn((url) => {
    const responseData = data[url] || { error: 'Not found' };
    return Promise.resolve(new Response(JSON.stringify(responseData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
  });
};

describe('App HoverCard Integration', () => {
  const mockTickets = [
    {
      id: 1,
      title: 'Fix the sink',
      details: 'Leaking in the kitchen',
      priority: 'urgent',
      due: '2026-01-01',
      status: 'open',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2025-12-01T10:00:00Z',
      updated_at: '2025-12-01T10:00:00Z',
      group: 0,
    },
    {
      id: 2,
      title: 'Buy milk',
      details: 'Organic please',
      priority: 'low',
      due: '2026-01-05',
      status: 'in_progress',
      filed_by: 'him',
      assigned_to: 'her',
      created_at: '2025-12-02T10:00:00Z',
      updated_at: '2025-12-02T10:00:00Z',
      group: 1,
    },
    {
      id: 3,
      title: 'Clean attic',
      details: 'Dusty',
      priority: 'normal',
      due: null,
      status: 'done',
      filed_by: 'her',
      assigned_to: 'him',
      created_at: '2025-11-01T10:00:00Z',
      updated_at: '2025-12-20T10:00:00Z',
      group: 2,
    },
  ];

  it('shows ticket details in a tooltip when hovering the title in To Do, In Progress, and Completed columns', async () => {
    mockFetch({
      '/api/dashboard': { todo: [mockTickets[0]], in_progress: [mockTickets[1]], completed: [mockTickets[2]] },
      '/api/filed': { tickets: [] },
      '/api/board': {},
      '/api/me': { user: 'him' },
    });

    render(<App />);

    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const titles = ['Fix the sink', 'Buy milk', 'Clean attic'];
    const details = ['Leaking in the kitchen', 'Organic please', 'Dusty'];

    for (let i = 0; i < titles.length; i++) {
      const titleEl = await screen.findByText(titles[i]);
      
      fireEvent.mouseEnter(titleEl);
      
      const tooltip = await screen.findByRole('tooltip');
      expect(tooltip).toHaveTextContent(details[i]);
      expect(tooltip).toHaveTextContent(/Filed by/i);
      expect(tooltip).toHaveTextContent(/Assigned to/i);
      
      fireEvent.mouseLeave(titleEl);
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    }
  });

  it('does not wrap titles in the "Tickets I filed" section with HoverCard', async () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [mockTickets[0]] },
      '/api/board': {},
      '/api/me': { user: 'him' },
    });

    render(<App />);

    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    fireEvent.click(screen.getByRole('button', { name: /Load/i }));

    const titleEl = await screen.findByText('Fix the sink');
    fireEvent.mouseEnter(titleEl);
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('verifies that other page elements remain functional and present', async () => {
    mockFetch({
      '/api/dashboard': { todo: [], in_progress: [], completed: [] },
      '/api/filed': { tickets: [] },
      '/api/board': {},
      '/api/me': { user: 'him' },
    });

    render(<App />);

    expect(screen.getByText('~/honey-do')).toBeInTheDocument();
    expect(screen.getByLabelText(/Token/i)).toBeInTheDocument();
    expect(screen.getByText('New ticket')).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /File ticket/i })).toBeInTheDocument();
    expect(screen.getByText('Tickets I filed')).toBeInTheDocument();
  });
});