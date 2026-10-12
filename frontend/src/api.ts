// GD-1g: frontend/src/api.ts — every fetch call of the personal board.
import type { Board, Filed, Me, NewTicket, Ticket } from "./types";

const BASE = "/api";

function checkOk(response: Response): never | void {
  if (!response.ok) {
    throw new Error(String(response.status));
  }
}

export async function fetchDashboard(token: string): Promise<Board> {
  const response = await fetch(`${BASE}/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  checkOk(response);
  return response.json();
}

export async function fetchFiled(token: string): Promise<Filed> {
  const response = await fetch(`${BASE}/filed`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  checkOk(response);
  return response.json();
}

export async function createTicket(token: string, data: NewTicket): Promise<Ticket> {
  const response = await fetch(`${BASE}/tickets`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  checkOk(response);
  return response.json();
}

export async function changeStatus(token: string, id: number, status: string): Promise<Ticket> {
  const response = await fetch(`${BASE}/tickets/${id}/status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  checkOk(response);
  return response.json();
}
