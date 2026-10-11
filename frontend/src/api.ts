export interface Ticket {
  id: number;
  title: string;
  details: string;
  priority: "low" | "normal" | "urgent";
  due: string | null;
  status: string;
  filed_by: string;
  assigned_to: string;
  created_at: string;
  updated_at: string;
}

export interface TicketWithGroup extends Ticket {
  group: number;
}

export interface DashboardData {
  todo: TicketWithGroup[];
  in_progress: TicketWithGroup[];
  completed: Ticket[];
}

export interface FiledTicketsData {
  tickets: Ticket[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = new Error(`Request failed with status ${response.status}`);
    (error as any).status = response.status;
    throw error;
  }
  return response.json();
}

export async function getDashboard(token: string): Promise<DashboardData> {
  const response = await fetch("/api/dashboard", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse(response);
}

export async function getFiledTickets(token: string): Promise<FiledTicketsData> {
  const response = await fetch("/api/filed", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return handleResponse(response);
}

export async function createTicket(
  token: string,
  data: { title: string; details?: string; priority?: "low" | "normal" | "urgent"; due?: string | null }
): Promise<Ticket> {
  const response = await fetch("/api/tickets", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  return handleResponse(response);
}

export async function changeStatus(
  token: string,
  ticketId: number,
  newStatus: string
): Promise<Ticket> {
  const response = await fetch(`/api/tickets/${ticketId}/status`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status: newStatus }),
  });
  return handleResponse(response);
}