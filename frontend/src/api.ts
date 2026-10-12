import { Board, Filed, Me, NewTicket, Ticket } from "./types";

export async function fetchDashboard(token: string): Promise<Board> {
  const res = await fetch("/api/dashboard", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function fetchFiled(token: string): Promise<Filed> {
  const res = await fetch("/api/filed", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function createTicket(token: string, data: NewTicket): Promise<Ticket> {
  const res = await fetch("/api/tickets", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function changeStatus(token: string, id: number, status: string): Promise<Ticket> {
  const res = await fetch(`/api/tickets/${id}/status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function fetchBoard(token: string): Promise<Board> {
  const res = await fetch("/api/board", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function fetchMe(token: string): Promise<Me> {
  const res = await fetch("/api/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}