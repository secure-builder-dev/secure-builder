import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import HouseholdBoard from '../src/HouseholdBoard';
import { fetchBoard } from '../src/api';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('fetchBoard', () => {
  it('sends GET /api/board with Authorization header and returns JSON', async () => {
    const mockData = { todo: [], in_progress: [], completed: [] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });

    const token = 'test-token';
    const result = await fetchBoard(token);

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/board', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    expect(result).toEqual(mockData);
  });

  it('throws Error with status code when response is not ok', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
    });

    await expect(fetchBoard('bad-token')).rejects.toThrow('401');
  });
});

describe('HouseholdBoard Component', () => {
  const mockBoard = {
    todo: [
      { id: 1, title: 'Fix sink', assigned_to: 'him' },
      { id: 2, title: 'Buy milk', assigned_to: 'her' },
    ],
    in_progress: [
      { id: 3, title: 'Paint wall', assigned_to: 'him' },
    ],
    completed: [
      { id: 4, title: 'Mow lawn', assigned_to: 'her' },
    ],
  };

  it('renders the household board structure with correct headings', () => {
    render(<HouseholdBoard board={mockBoard} />);
    
    expect(screen.getByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders tickets with titles and correct assigned_to text', () => {
    render(<HouseholdBoard board={mockBoard} />);

    // To Do
    const todoSection = screen.getByText('To Do').closest('[role="gridcell"]');
    expect(todoSection).toHaveTextContent('Fix sink');
    expect(todoSection).toHaveTextContent('for him');
    expect(todoSection).toHaveTextContent('Buy milk');
    expect(todoSection).toHaveTextContent('for her');

    // In Progress
    const progressSection = screen.getByText('In Progress').closest('[role="gridcell"]');
    expect(progressSection).toHaveTextContent('Paint wall');
    expect(progressSection).toHaveTextContent('for him');

    // Completed
    const completedSection = screen.getByText('Completed').closest('[role="gridcell"]');
    expect(completedSection).toHaveTextContent('Mow lawn');
    expect(completedSection).toHaveTextContent('for her');
  });
});