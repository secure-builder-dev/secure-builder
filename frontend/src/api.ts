// Frontend API helper functions
// These functions wrap fetch calls to the backend API, handling authentication headers,
// JSON bodies, and error handling as specified in the design plan.

/**
 * Perform a GET request to the given endpoint with the Authorization header.
 * Returns the parsed JSON if the response is ok, otherwise throws an Error with the status code.
 */
async function get<T>(url: string, token: string): Promise<T> {
  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    throw new Error(String(response.status));
  }
  return (await response.json()) as T;
}

/**
 * Perform a POST request with a JSON body to the given endpoint with the Authorization header.
 * Returns the parsed JSON if the response is ok, otherwise throws an Error with the status code.
 */
async function post<T, B>(url: string, token: string, body: B): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(String(response.status));
  }
  return (await response.json()) as T;
}

/**
 * Perform a PATCH request with a JSON body to the given endpoint with the Authorization header.
 * Returns the parsed JSON if the response is ok, otherwise throws an Error with the status code.
 */
async function patch<T, B>(url: string, token: string, body: B): Promise<T> {
  const response = await fetch(url, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(String(response.status));
  }
  return (await response.json()) as T;
}

/**
 * Fetch the personal dashboard board.
 */
export async function fetchDashboard(token: string) {
  return get<any>("/api/dashboard", token);
}

/**
 * Fetch the tickets filed by the current user.
 */
export async function fetchFiled(token: string) {
  return get<any>("/api/filed", token);
}

/**
 * Create a new ticket.
 * @param token authentication token
 * @param data NewTicket payload
 */
export async function createTicket(token: string, data: any) {
  return post<any, any>("/api/tickets", token, data);
}

/**
 * Change the status of a ticket.
 * @param token authentication token
 * @param id ticket id
 * @param status new status string
 */
export async function changeStatus(token: string, id: number, status: string) {
  return post<any, any>(`/api/tickets/${id}/status`, token, { status });
}

/**
 * Fetch the current user's identity.
 */
export async function fetchMe(token: string) {
  return get<any>("/api/me", token);
}

/**
 * Fetch the household board, optionally filtered.
 * If a filter is provided, only non‑empty fields are sent as query parameters.
 */
export async function fetchBoard(token: string, filter?: { q: string; priority: string; assigned_to: string }) {
  if (!filter) {
    return get<any>("/api/board", token);
  }
  const params = new URLSearchParams();
  if (filter.q) params.append("q", filter.q);
  if (filter.priority) params.append("priority", filter.priority);
  if (filter.assigned_to) params.append("assigned_to", filter.assigned_to);
  const query = params.toString();
  const url = query ? `/api/board?${query}` : "/api/board";
  return get<any>(url, token);
}

/**
 * Fetch a single ticket by ID.
 */
export async function fetchTicket(token: string, id: number) {
  return get<any>(`/api/tickets/${id}`, token);
}

/**
 * Fetch comments for a ticket.
 */
export async function fetchComments(token: string, id: number) {
  return get<any>(`/api/tickets/${id}/comments`, token);
}

/**
 * Fetch history (events) for a ticket.
 */
export async function fetchHistory(token: string, id: number) {
  return get<any>(`/api/tickets/${id}/history`, token);
}

/**
 * Add a comment to a ticket.
 */
export async function addComment(token: string, id: number, body: string) {
  return post<any, { body: string }>(`/api/tickets/${id}/comments`, token, { body });
}

/**
 * Edit a ticket (E4).
 * Sends a PATCH request with the provided changes and returns the parsed ticket.
 */
export async function editTicket(token: string, id: number, changes: any) {
  return patch<any, any>(`/api/tickets/${id}`, token, changes);
}

/**
 * Fetch the summary for the current user (E4).
 */
export async function fetchSummary(token: string) {
  return get<any>("/api/summary", token);
}
