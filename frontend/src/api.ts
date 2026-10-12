// GD-1g: frontend/src/api.ts — every fetch call of the personal board.
import type { Board, Filed, Me, NewTicket, Ticket } from "./types";

const BASE = "/api";

function checkStatus(status: number): void {
  if (status < 200 || status >= 300) {
    throw new Error(String(status));
  }
}

export async function fetchDashboard(token: string): Promise<Board> {
  const res = await fetch(`${BASE}/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  checkStatus(res.status);
  return res.json();
}

export async function fetchFiled(token: string): Promise<Filed> {
  const res = await fetch(`${BASE}/filed`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  checkStatus(res.status);
  return res.json();
}

export async function createTicket(token: string, data: NewTicket): Promise<Ticket> {
  const res = await fetch(`${BASE}/tickets`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  checkStatus(res.status);
  return res.json();
}

export async function changeStatus(token: string, id: number, status: string): Promise<Ticket> {
  const res = await fetch(`${BASE}/tickets/${id}/status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  checkStatus(res.status);
  return res.json();
}
