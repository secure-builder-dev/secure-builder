id: XO-2c
unit: XO-2
state: open
depends_on: -
done_when: frontend/src/HoverCard.tsx default-exports the React component HoverCard({ticket, children}) that renders its children inside <span className="hover-target" tabIndex={0}>; from mouseenter until mouseleave, and from focus until blur, the span also holds <div role="tooltip" className="hover-card"> — it is absent otherwise; the tooltip holds four paragraphs: the ticket's details (or No details when details is empty), Filed by {filed_by}, Assigned to {assigned_to}, and Created {the first 10 characters of created_at}, all as React text

# XO-2c
