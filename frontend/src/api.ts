// Frontend API helper functions

// Frontend API helper functions
// These functions wrap fetch calls to the backend API, handling authentication headers,

// JSON bodies, and error handling as specified in the design plan.

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
 * Fetch the household board.
 */
export async function fetchMe(token: string) {
  return get<any>("/api/me", token);
}

/**
 * Fetch the household board.
 */
export async function fetchBoard(token: string) {
  return get<any>("/api/board", token);
}

