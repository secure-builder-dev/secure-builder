import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import HouseholdBoard from '../src/HouseholdBoard';
import * as api from '../src/api';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('fetchBoard', () => {
  it('sends GET /api/board with Authorization header and returns JSON', async () => {
    const mockData = { todo: [], in_progress: [], completed: [] };
    const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockData,
    } as Response);

    const token = 'test-token';
    const result = await api.fetchBoard(token);

    expect(fetchSpy).toHaveBeenCalledWith('/api/board', {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(result).toEqual(mockData);
  });

  it('throws an Error with the status code message when response is not ok', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: false,
      status: 401,
    } as Response);

    await expect(api.fetchBoard('bad-token')).rejects.toThrow('401');
  });
});

describe('HouseholdBoard Component', () => {
  const mockBoard = {
    todo: [
      { id: 1, title: 'Fix sink', assigned_to: 'him', filed_by: 'her', status: 'open', priority: 'normal', due: null, details: '', created_at: '', updated_at: '' },
      { id: 2, title: 'Buy milk', assigned_to: 'her', filed_by: 'him', status: 'acknowledged', priority: 'low', due: null, details: '', created_at: '', updated_at: '' },
    ],
    in_progress: [
      { id: 3, title: 'Paint wall', assigned_to: 'him', filed_by: 'her', status: 'in_progress', priority: 'urgent', due: null, details: '', created_at: '', updated_at: '' },
    ],
    completed: [
      { id: 4, title: 'Mow lawn', assigned_to: 'her', filed_by: 'him', status: 'done', priority: 'normal', due: null, details: '', created_at: '', updated_at: '' },
    ],
  };

  it('renders the Household board section and three columns', () => {
    render(<HouseholdBoard board={mockBoard} />);

    expect(screen.getByText('Household board')).toBeInTheDocument();
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders tickets with titles and correct assigned_to text', () => {
    render(<HouseholdBoard board={mockBoard} />);

    // To Do
    expect(screen.getByText('Fix sink')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();
    expect(screen.getByText('Buy milk')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();

    // In Progress
    expect(screen.getByText('Paint wall')).toBeInTheDocument();
    expect(screen.getByText('him')).toBeInTheDocument();

    // Completed
    expect(screen.getByText('Mow lawn')).toBeInTheDocument();
    expect(screen.getByText('her')).toBeInTheDocument();
  });
});