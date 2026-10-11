import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockBoardData = {
  todo: [
    { id: 1, title: 'Household Todo 1', details: '', priority: 'normal', due: null, status: 'open', filed_by: 'her', assigned_to: 'him', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' },
  ],
  in_progress: [
    { id: 2, title: 'Household In Progress 1', details: '', priority: 'urgent', due: null, status: 'in_progress', filed_by: 'him', assigned_to: 'her', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' },
  ],
  completed: [
    { id: 3, title: 'Household Completed 1', details: '', priority: 'low', due: null, status: 'done', filed_by: 'her', assigned_to: 'him', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' },
  ],
};

const mockDashboardData = {
  todo: [{ id: 10, title: 'Personal Todo', details: '', priority: 'normal', due: null, status: 'open', filed_by: 'him', assigned_to: 'her', created_at: '2023-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z', group: 1 }],
  in_progress: [],
  completed: [],
};

const mockFiledData = { tickets: [] };

const createFetchMock = (boardResponse: Response) => {
  return vi.fn().mockImplementation((url) => {
    if (url === '/api/board') return Promise.resolve(boardResponse);
    if (url === '/api/dashboard') return Promise.resolve(new Response(JSON.stringify(mockDashboardData)));
    if (url === '/api/filed') return Promise.resolve(new Response(JSON.stringify(mockFiledData)));
    if (url === '/api/me') return Promise.resolve(new Response(JSON.stringify({ user: 'her' })));
    return Promise.resolve(new Response(null, { status: 404 }));
  });
};

describe('App Household Board Integration', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('calls fetchBoard and shows HouseholdBoard when Load is pressed', async () => {
    globalThis.fetch = createFetchMock(
      new Response(JSON.stringify(mockBoardData), { status: 200 })
    );

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    expect(await screen.findByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('Household Todo 1')).toBeInTheDocument();
    expect(screen.getByText('Household In Progress 1')).toBeInTheDocument();
    expect(screen.getByText('Household Completed 1')).toBeInTheDocument();
  });

  it('leaves household board empty and page intact when /api/board fails', async () => {
    globalThis.fetch = createFetchMock(
      new Response(null, { status: 500 })
    );

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    // Wait for other requests to finish
    await screen.findByText('Personal Todo');

    expect(screen.queryByText('Household board')).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Wrong token/i)).not.toBeInTheDocument();
  });

  it('leaves household board empty and page intact when /api/board returns malformed JSON', async () => {
    globalThis.fetch = createFetchMock(
      new Response('not json', { status: 200 })
    );

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    await screen.findByText('Personal Todo');

    expect(screen.queryByText('Household board')).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
  });
});