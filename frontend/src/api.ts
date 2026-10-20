
export async function fetchMe(token: string) {
  const resp = await fetch('/api/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  const data = await resp.json();
  // Validate that the returned user is one of the known users.
  if (data.user !== 'her' && data.user !== 'him') {
    // Treat an unexpected user as a failed request.
    throw new Error(String(resp.status));
  }
  return data;
}

export async function fetchBoard(token: string) {
  const resp = await fetch('/api/board', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function fetchDashboard(token: string) {
  const resp = await fetch('/api/dashboard', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function fetchFiled(token: string) {
  const resp = await fetch('/api/filed', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function createTicket(token: string, data: {
  title: string;
  details: string;
  priority: 'low' | 'normal' | 'urgent';
  due: string | null;
}) {
  const resp = await fetch('/api/tickets', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function changeStatus(token: string, id: number, status: 'open' | 'acknowledged' | 'in_progress' | 'done' | 'closed') {
  const resp = await fetch(`/api/tickets/${id}/status`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status }),
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function fetchTicket(token: string, id: number) {
  const resp = await fetch(`/api/tickets/${id}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function fetchComments(token: string, id: number) {
  const resp = await fetch(`/api/tickets/${id}/comments`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function fetchHistory(token: string, id: number) {
  const resp = await fetch(`/api/tickets/${id}/history`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

export async function addComment(token: string, id: number, body: string) {
  const resp = await fetch(`/api/tickets/${id}/comments`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ body }),
  });
  if (!resp.ok) {
    throw new Error(String(resp.status));
  }
  return await resp.json();
}

