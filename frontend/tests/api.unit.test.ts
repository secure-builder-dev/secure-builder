// Unit tests for frontend/src/api.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchDashboard, fetchFiled, createTicket, changeStatus } from '../src/api';

describe('frontend API functions', () => {
  const token = 'test-token';
  const baseHeaders = {
    Authorization: `Bearer ${token}`,
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('test_fetch_functions_return_parsed_json', async () => {
    // Mock fetch for dashboard
    const board = { todo: [], in_progress: [], completed: [] };
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => board,
    } as Response);
    const resultBoard = await fetchDashboard(token);
    expect(resultBoard).toEqual(board);
    expect(global.fetch).toHaveBeenCalledWith('/api/dashboard', {
      method: 'GET',
      headers: baseHeaders,
    });

    // Mock fetch for filed
    const filed = { tickets: [] };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => filed,
    } as Response);
    const resultFiled = await fetchFiled(token);
    expect(resultFiled).toEqual(filed);
    expect(global.fetch).toHaveBeenCalledWith('/api/filed', {
      method: 'GET',
      headers: baseHeaders,
    });

    // Mock fetch for createTicket
    const newTicket = { title: 't', details: '', priority: 'normal', due: null } as any;
    const createdTicket = { ...newTicket, id: 1, status: 'open', filed_by: 'her', assigned_to: 'him', created_at: '', updated_at: '' };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => createdTicket,
    } as Response);
    const resultCreated = await createTicket(token, newTicket);
    expect(resultCreated).toEqual(createdTicket);
    expect(global.fetch).toHaveBeenCalledWith('/api/tickets', {
      method: 'POST',
      headers: { ...baseHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify(newTicket),
    });

    // Mock fetch for changeStatus
    const changedTicket = { ...createdTicket, status: 'in_progress' };
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => changedTicket,
    } as Response);
    const resultChanged = await changeStatus(token, 1, 'in_progress');
    expect(resultChanged).toEqual(changedTicket);
    expect(global.fetch).toHaveBeenCalledWith('/api/tickets/1/status', {
      method: 'POST',
      headers: { ...baseHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'in_progress' }),
    });
  });

  it('test_fetch_functions_send_correct_headers', async () => {
    // Dashboard (GET) should not have Content-Type
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) } as Response);
    await fetchDashboard(token);
    expect(global.fetch).toHaveBeenCalledWith('/api/dashboard', {
      method: 'GET',
      headers: baseHeaders,
    });

    // createTicket (POST) should have Content-Type
    const payload = { title: 'x', details: '', priority: 'low', due: null } as any;
    (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({}) } as Response);
    await createTicket(token, payload);
    expect(global.fetch).toHaveBeenCalledWith('/api/tickets', {
      method: 'POST',
      headers: { ...baseHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    // changeStatus (POST) should have Content-Type
    (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({}) } as Response);
    await changeStatus(token, 42, 'done');
    expect(global.fetch).toHaveBeenCalledWith('/api/tickets/42/status', {
      method: 'POST',
      headers: { ...baseHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'done' }),
    });
  });

  it('test_fetch_functions_throw_on_error_status', async () => {
    // Simulate 401 response for each function
    const errorResponse = { ok: false, status: 401 } as Response;
    global.fetch = vi.fn().mockResolvedValue(errorResponse);
    await expect(fetchDashboard(token)).rejects.toThrowError('401');
    await expect(fetchFiled(token)).rejects.toThrowError('401');
    const payload = { title: 'x', details: '', priority: 'low', due: null } as any;
    await expect(createTicket(token, payload)).rejects.toThrowError('401');
    await expect(changeStatus(token, 1, 'open')).rejects.toThrowError('401');
  });
});
