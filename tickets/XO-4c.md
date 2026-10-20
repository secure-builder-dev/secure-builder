id: XO-4c
unit: XO-4
state: claimed
depends_on: XO-4a
done_when: PATCH /api/tickets/{id} with an object holding any of title, details, priority and due answers 200 with the edited ticket; it answers 404 {'error': 'not found'} for a missing ticket, 400 {'error': 'invalid request'} for an invalid body, field or id, 403 {'error': 'forbidden'} when the caller is not the filer and 409 {'error': 'not editable'} past acknowledged, in the order rules.edit_ticket checks them; it answers 401 without a valid bearer token and follows the error, header and body-limit rules of every other route

# XO-4c
