# Ingest records

© 2026 Casey Houle. All rights reserved.

Chain of custody for every bundle ingested across a boundary: identifier, dates,
hash result, and whether the content was modified in transit.

Schema: ingest-records/1.

| date | bundle | production_date | arrival_date | hash_result | modified_in_transit | operator | side |
|---|---|---|---|---|---|---|---|
