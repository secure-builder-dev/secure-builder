import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { fetchBoard } from '../src/api';
import HouseholdBoard from '../src/HouseholdBoard';

afterEach(() => {
  cleanup();
});

describe('fetchBoard', () => {
  it('sends GET /api/board with Authorization header and returns JSON', async () => {
    const mockBoard = { todo: [], in_progress: [], completed: [] };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockBoard,
    } as Response);

    const token = 'test-token';
    const result = await fetchBoard(token);

    expect(fetchSpy).toHaveBeenCalledWith('/api/board', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    expect(result).toEqual(mockBoard);
    fetchSpy.mockRestore();
  });

  it('throws Error with status code when response is not ok', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
    } as Response);

    await expect(fetchBoard('bad-token')).rejects.toThrow('401');
    fetchSpy.mockRestore();
  });
});

describe('HouseholdBoard Component', () => {
  const mockBoard = {
    todo: [
      { id: 1, title: 'Fix Sink', assigned_to: 'him' },
      { id: 2, title: 'Buy Milk', assigned_to: 'her' },
    ],
    in_progress: [
      { id: 3, title: 'Paint Wall', assigned_to: 'him' },
    ],
    completed: [
      { id: 4, title: 'Mow Lawn', assigned_to: 'her' },
    ],
  };

  it('renders the Household board section and column headers', () => {
    render(<HouseholdBoard board={mockBoard} />);
    
    expect(screen.getByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders tickets with titles and correct assignee text', () => {
    render(<HouseholdBoard board={mockBoard} />);

    // To Do
    expect(screen.getByText('Fix Sink')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();
    expect(screen.getByText('Buy Milk')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();

    // In Progress
    expect(screen.getByText('Paint Wall')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();

    // Completed
    expect(screen.getByText('Mow Lawn')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();
  });
});