id: XO-3d
unit: XO-3
state: open
depends_on: XO-3c
done_when: GET /api/tickets/{id} answers 200 with the ticket as rules.ticket_to_dict gives it, and 404 {'error': 'not found'} for a missing ticket; GET /api/tickets/{id}/comments answers 200 {'comments': [...]} oldest first, and GET /api/tickets/{id}/history answers 200 {'events': [...]} oldest first, both 404 for a missing ticket; POST /api/tickets/{id}/comments with the body {'body': text} answers 201 with the new comment (author is the caller), 404 for a missing ticket, and 400 {'error': 'invalid request'} for malformed JSON, a body that is not an object, any other key, or an invalid text; the four routes answer 401 {'error': 'unauthorized'} without a valid bearer token, 400 for a non-integer id, 413 for a body over 65536 bytes, and send the four security headers on every answer

# XO-3d
