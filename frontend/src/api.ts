import type {
  Board,
  CommentOut,
  Comments,
  Filed,
  History,
  Me,
  NewTicket,
  Ticket,
} from "./types";

async function call(
  token: string,
  path: string,
  init?: RequestInit,
): Promise<unknown> {
  const headers: Record<string, string> = {
    authorization: `Bearer ${token}`,
  };
  if (init?.body !== undefined) {
    headers["content-type"] = "application/json";
  }
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    throw new Error(String(res.status));
  }
  return res.json();
}

export async function fetchDashboard(token: string): Promise<Board> {
  return (await call(token, "/api/dashboard")) as Board;
}

export async function fetchBoard(token: string): Promise<Board> {
  return (await call(token, "/api/board")) as Board;
}

export async function fetchFiled(token: string): Promise<Filed> {
  return (await call(token, "/api/filed")) as Filed;
}

export async function fetchMe(token: string): Promise<Me> {
  return (await call(token, "/api/me")) as Me;
}

export async function createTicket(
  token: string,
  data: NewTicket,
): Promise<Ticket> {
  return (await call(token, "/api/tickets", {
    method: "POST",
    body: JSON.stringify(data),
  })) as Ticket;
}

export async function changeStatus(
  token: string,
  id: number,
  status: string,
): Promise<Ticket> {
  return (await call(token, `/api/tickets/${id}/status`, {
    method: "POST",
    body: JSON.stringify({ status }),
  })) as Ticket;
}

export async function fetchTicket(token: string, id: number): Promise<Ticket> {
  return (await call(token, `/api/tickets/${id}`)) as Ticket;
}

export async function fetchComments(
  token: string,
  id: number,
): Promise<Comments> {
  return (await call(token, `/api/tickets/${id}/comments`)) as Comments;
}

export async function addComment(
  token: string,
  id: number,
  body: string,
): Promise<CommentOut> {
  return (await call(token, `/api/tickets/${id}/comments`, {
    method: "POST",
    body: JSON.stringify({ body }),
  })) as CommentOut;
}

export async function fetchHistory(
  token: string,
  id: number,
): Promise<History> {
  return (await call(token, `/api/tickets/${id}/history`)) as History;
}
