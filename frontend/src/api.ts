import type { Board, Filed, Ticket, NewTicket, Status, Me, Comments, History, CommentOut, TicketEdit, BoardFilter, Summary } from "./types";

export async function fetchDashboard(token: string): Promise<Board> {
  const res = await fetch("/api/dashboard", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchFiled(token: string): Promise<Filed> {
  const res = await fetch("/api/filed", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
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
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function changeStatus(token: string, id: number, status: Status): Promise<Ticket> {
  const res = await fetch(`/api/tickets/${id}/status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchBoard(token: string, filter?: BoardFilter): Promise<Board> {
  const params = new URLSearchParams();
  if (filter) {
    if (filter.q !== "") params.append("q", filter.q);
    if (filter.priority !== "") params.append("priority", filter.priority);
    if (filter.assigned_to !== "") params.append("assigned_to", filter.assigned_to);
  }
  const url = params.toString() ? `/api/board?${params.toString()}` : "/api/board";
  const res = await fetch(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchMe(token: string): Promise<Me> {
  const res = await fetch("/api/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchTicket(token: string, id: number): Promise<Ticket> {
  const res = await fetch(`/api/tickets/${id}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchComments(token: string, id: number): Promise<Comments> {
  const res = await fetch(`/api/tickets/${id}/comments`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchHistory(token: string, id: number): Promise<History> {
  const res = await fetch(`/api/tickets/${id}/history`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function addComment(token: string, id: number, body: string): Promise<CommentOut> {
  const res = await fetch(`/api/tickets/${id}/comments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ body }),
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function editTicket(token: string, id: number, changes: TicketEdit): Promise<Ticket> {
  const res = await fetch(`/api/tickets/${id}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(changes),
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

export async function fetchSummary(token: string): Promise<Summary> {
  const res = await fetch("/api/summary", {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}
