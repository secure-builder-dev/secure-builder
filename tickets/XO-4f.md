id: XO-4f
unit: XO-4
state: open
depends_on: XO-4e
done_when: EditTicketForm (default export of frontend/src/EditTicketForm.tsx, props ticket, onSave, onCancel and optional error) renders form.edit-ticket named Edit ticket with the labelled fields Title, Details, Priority (a select of low, normal, urgent) and Due (a date input) filled from the ticket, a Save submit button and a Cancel button that calls onCancel; Save calls onSave with all four fields, due null when the field is empty, and with error the form shows p.error with role alert holding that text; TicketDetail shows an Edit button only when me is the ticket's filer and its status is open or acknowledged — Edit shows the form, a successful save PATCHes the four fields, closes the form, shows the answered ticket, fetches the history again and calls onSaved with the ticket, and a failed save keeps the form open with the error Could not save

# XO-4f
