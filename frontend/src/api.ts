export async function fetchBoard(token: string): Promise<any> {
  const response = await fetch('/api/board', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(response.status.toString());
  }

  return response.json();
}

export async function fetchMe(token: string): Promise<any> {
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
