id: TQ-2f
unit: TQ-2
state: open
depends_on: TQ-2e
done_when: once the dashboard has loaded, main shows, before My board, <section className="panel new-ticket" aria-label="New ticket"> with <h2>New ticket</h2> and a form with the labelled inputs Title, Details (a textarea), Priority (a select of low, normal and urgent, normal by default) and Due (an input of type date), and a File ticket button; File ticket calls createTicket with {title, details, priority, due} (due null when the Due field is empty) — on success it clears the form and reloads, which fetches the dashboard and the filed tickets again and shows them — on failure it shows the error message as Load does and keeps what was typed; on My board, each To Do ticket with status open gets an Acknowledge button, each with status acknowledged a Start button, and each In Progress ticket a Done button, passed as the TicketCard's children — Completed tickets have no buttons; Acknowledge, Start and Done call changeStatus with acknowledged, in_progress and done and then reload — a failure shows the error message as Load does

# TQ-2f
