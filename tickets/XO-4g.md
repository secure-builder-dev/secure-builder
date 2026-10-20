id: XO-4g
unit: XO-4
state: in review
depends_on: -
done_when: FilterBar (default export of frontend/src/FilterBar.tsx, prop onApply) renders form.filter-bar with role search named Filter household board, holding the labelled fields Search (text), Priority (a select of Any with the empty value, low, normal, urgent) and Assigned to (a select of Anyone with the empty value, her, him) and an Apply submit button; Apply calls onApply with {q, priority, assigned_to}, q stripped and empty strings for no filter; SummaryBadge (default export of frontend/src/SummaryBadge.tsx, prop summary) renders span.summary named Summary reading '2 overdue · 1 due today · 5 open' for those numbers, with the class alert only when overdue is more than 0

# XO-4g
