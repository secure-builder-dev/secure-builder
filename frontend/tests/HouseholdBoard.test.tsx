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
    const mockToken = 'test-token';
    const mockData = { todo: [], in_progress: [], completed: [] };
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const result = await fetchBoard(mockToken);

    expect(fetchSpy).toHaveBeenCalledWith('/api/board', {
      headers: { Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toEqual(mockData);
    fetchSpy.mockRestore();
  });

  it('throws an Error with the status code when response is not ok', async () => {
    const mockToken = 'test-token';
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 403,
    } as Response);

    await expect(fetchBoard(mockToken)).rejects.toThrow('403');
    vi.restoreAllMocks();
  });
});

describe('HouseholdBoard', () => {
  const mockBoard = {
    todo: [
      { id: 1, title: 'Task 1', assigned_to: 'her' },
      { id: 2, title: 'Task 2', assigned_to: 'him' },
    ],
    in_progress: [
      { id: 3, title: 'Task 3', assigned_to: 'her' },
    ],
    completed: [
      { id: 4, title: 'Task 4', assigned_to: 'him' },
    ],
  };

  it('renders the section heading and column headers', () => {
    render(<HouseholdBoard board={mockBoard} />);
    expect(screen.getByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders tickets with titles and correct assigned_to text', () => {
    render(<HouseholdBoard board={mockBoard} />);
    
    // To Do
    expect(screen.getByText('Task 1')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();
    expect(screen.getByText('Task 2')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();

    // In Progress
    expect(screen.getByText('Task 3')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();

    // Completed
    expect(screen.getByText('Task 4')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();
  });
});