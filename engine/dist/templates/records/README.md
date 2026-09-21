# Records

© 2026 Casey Houle. All rights reserved.

Plain text, under version control, append-only. These files are the assessment
evidence. Rows are never deleted; a wrong verdict is superseded by a later row
that says so.

**Single-writer assumption.** These records assume one unit of work in flight at
a time. Two concurrent branches will conflict on append; resolve by keeping both
rows. A team that outgrows this moves to one file per gate run, assembled into
the series on read (spec 02 §2.4).

**Timestamps** are recorded in the timezone named in `.engine/rules/config.json`
(`timezone`) and come from the source named there (`clock`).
