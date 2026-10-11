export async function fetchWithAuth(url: string, token: string, options?: RequestInit) {
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string> || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
}

export async function getDashboard(token: string) {
  const res = await fetchWithAuth('/api/dashboard', token);
  if (!res.ok) {
    if (res.status === 401) throw new Error('WRONG_TOKEN');
    throw new Error('ERROR');
  }
  return res.json();
}

export async function getDashboardAndFiled(token: string) {
  const [dashRes, filedRes] = await Promise.all([
    fetchWithAuth('/api/dashboard', token),
    fetchWithAuth('/api/filed', token)
  ]);
  
  if (!dashRes.ok || !filedRes.ok) {
    if (dashRes.status === 401 || filedRes.status === 401) {
      throw new Error('WRONG_TOKEN');
    }
    throw new Error('ERROR');
  }
  
  const [dashData, filedData] = await Promise.all([dashRes.json(), filedRes.json()]);
  return { dashboard: dashData, filed: filedData };
}

export async function getMyFiled(token: string) {
  const res = await fetchWithAuth('/api/filed', token);
  if (!res.ok) {
    if (res.status === 401) throw new Error('WRONG_TOKEN');
    throw new Error('ERROR');
  }
  return res.json();
}

export async function createTicket(token: string, data: { title: string; details: string; priority: string; due: string | null }) {
  const res = await fetchWithAuth('/api/tickets', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    if (res.status === 401) throw new Error('WRONG_TOKEN');
    throw new Error('ERROR');
  }
  return res.json();
}

export async function changeStatus(token: string, ticketId: number, status: string) {
  const res = await fetchWithAuth(`/api/tickets/${ticketId}/status`, token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    if (res.status === 401) throw new Error('WRONG_TOKEN');
    throw new Error('ERROR');
  }
  return res.json();
}

export async function fetchBoard(token: string) {
  const res = await fetchWithAuth('/api/board', token);
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function fetchMe(token: string) {
  const res = await fetchWithAuth('/api/me', token);
  if (!res.ok) {
    return null;
  }
  return res.json();
}