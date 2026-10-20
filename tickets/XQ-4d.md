id: XQ-4d
unit: XQ-4
state: claimed
depends_on: XQ-4b
done_when: GET /api/board takes the optional query parameters q, priority and assigned_to and answers the filtered household board, ignoring other parameters; a q over 120 characters, a priority that is not low, normal or urgent, or an assigned_to that is not her or him answers 400 {'error': 'invalid request'}; GET /api/summary answers 200 with the caller's summary for the current UTC date, and 401 without a valid bearer token

# XQ-4d
