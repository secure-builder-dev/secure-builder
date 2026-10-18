// The shapes the API answers with (plans/design.md). Given by the plan: do not change.
export type User = "her" | "him";
export type Priority = "low" | "normal" | "urgent";
export type Status = "open" | "acknowledged" | "in_progress" | "done" | "closed";

export interface Ticket {
  id: number;
  title: string;
  details: string;
  priority: Priority;
  due: string | null;
  status: Status;
  filed_by: User;
  assigned_to: User;
  created_at: string;
  updated_at: string;
  group?: 0 | 1 | 2; // only on the personal board's todo and in_progress tickets
}

export interface Board {
  todo: Ticket[];
  in_progress: Ticket[];
  completed: Ticket[];
}

export interface Filed {
  tickets: Ticket[];
}

export interface Me {
  user: User;
}

export interface NewTicket {
  title: string;
  details: string;
  priority: Priority;
  due: string | null;
}

// E3: comments and history
export interface CommentOut {
  id: number;
  ticket_id: number;
  author: User;
  body: string;
  created_at: string;
}

export interface Comments {
  comments: CommentOut[];
}

export type EventKind = "filed" | "status" | "edited";

export interface TicketEvent {
  id: number;
  ticket_id: number;
  actor: User;
  kind: EventKind;
  from_status: Status | null;
  to_status: Status | null;
  at: string;
}

export interface History {
  events: TicketEvent[];
}

// E4: edit, filter, summary
export interface TicketEdit {
  title: string;
  details: string;
  priority: Priority;
  due: string | null;
}

export interface BoardFilter {
  q: string;
  priority: Priority | "";
  assigned_to: User | "";
}

export interface Summary {
  overdue: number;
  due_today: number;
  open: number;
}
