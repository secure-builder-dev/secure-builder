export const fetchMe = async (token: string) => {
  const response = await fetch('/api/me', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
}

export const fetchDashboard = async (token: string) => {
  const response = await fetch('/api/dashboard', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
};

export const fetchFiled = async (token: string) => {
  const response = await fetch('/api/filed', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
};

export const createTicket = async (token: string, title: string, details: string, priority: string, due: string) => {
  const response = await fetch('/api/tickets', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title, details, priority, due }),
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
};

export const updateTicketStatus = async (token: string, ticketId: number, status: string) => {
  const response = await fetch(`/api/tickets/${ticketId}/status`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
};

export const fetchBoard = async (token: string) => {
  const response = await fetch('/api/board', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(response.status.toString());
  }
  return response.json();
};
