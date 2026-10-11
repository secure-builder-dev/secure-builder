import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import App from '../src/App';

const mockFetchResponse = (url: string, data: any, ok = true, status = 200) => {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  });
};

const setupFetchMock = (boardData: any = { todo: [], in_progress: [], completed: [] }, boardOk = true, boardStatus = 200) => {
  globalThis.fetch = vi.fn((url: string) => {
    if (url === '/api/dashboard') return mockFetchResponse(url, { todo: [], in_progress: [], completed: [] });
    if (url === '/api/filed') return mockFetchResponse(url, { tickets: [] });
    if (url === '/api/me') return mockFetchResponse(url, { user: 'her' });
    if (url === '/api/board') return mockFetchResponse(url, boardData, boardOk, boardStatus);
    return Promise.reject(new Error('Unknown URL'));
  });
};

describe('App Household Board Integration', () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('calls fetchBoard and shows HouseholdBoard when Load is pressed', async () => {
    const boardData = {
      todo: [{ id: 1, title: 'Household Task 1', assigned_to: 'him' }],
      in_progress: [{ id: 2, title: 'Household Task 2', assigned_to: 'her' }],
      completed: [{ id: 3, title: 'Household Task 3', assigned_to: 'him' }],
    };
    setupFetchMock(boardData);

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    expect(await screen.findByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('Household Task 1')).toBeInTheDocument();
    expect(screen.getByText('Household Task 2')).toBeInTheDocument();
    expect(screen.getByText('Household Task 3')).toBeInTheDocument();
    expect(screen.getAllByText('for him')).toHaveLength(2);
    expect(screen.getByText('for her')).toBeInTheDocument();
  });

  it('leaves household board empty and page intact on failed /api/board answer', async () => {
    setupFetchMock({}, false, 500);

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    expect(screen.queryByText('Household board')).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Wrong token/i)).not.toBeInTheDocument();
    
    expect(screen.getByText('~/honey-do')).toBeInTheDocument();
    expect(screen.getByText('New Ticket')).toBeInTheDocument();
  });

  it('leaves household board empty and page intact on malformed /api/board answer', async () => {
    setupFetchMock({ invalid: 'data' });

    render(<App />);
    
    const tokenInput = screen.getByLabelText(/Token/i);
    fireEvent.change(tokenInput, { target: { value: 'valid-token' } });
    
    const loadButton = screen.getByRole('button', { name: /Load/i });
    fireEvent.click(loadButton);

    expect(screen.queryByText('Household board')).not.toBeInTheDocument();
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
    expect(screen.getByText('~/honey-do')).toBeInTheDocument();
  });
});