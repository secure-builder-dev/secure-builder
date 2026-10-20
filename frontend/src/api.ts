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
