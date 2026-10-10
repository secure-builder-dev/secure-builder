export async function fetchDashboard(token: string): Promise<any> {
  const response = await fetch('/api/dashboard', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Wrong token');
    } else {
      throw new Error('Something went wrong');
    }
  }

  return await response.json();
}

export async function fetchFiled(token: string): Promise<any> {
  const response = await fetch('/api/filed', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Wrong token');
    } else {
      throw new Error('Something went wrong');
    }
  }

  return await response.json();
}

export async function createTicket(token: string, ticketData: any): Promise<any> {
  const response = await fetch('/api/tickets', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(ticketData)
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Wrong token');
    } else {
      throw new Error('Something went wrong');
    }
  }

  return await response.json();
}

export async function updateStatus(token: string, ticketId: number, newStatus: string): Promise<any> {
  const response = await fetch(`/api/tickets/${ticketId}/status`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ status: newStatus })
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Wrong token');
    } else {
      throw new Error('Something went wrong');
    }
  }

  return await response.json();
}