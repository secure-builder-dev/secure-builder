"""GD-1c: change_status — the moves of the design table, and nothing else."""
import datetime as dt

import pytest

from app.rules import change_status, create_ticket
from tests.conftest import at, set_times

# (from, to, who) where who is "assignee" or "filer"
MOVES = [
    ("open", "acknowledged", "assignee"),
    ("acknowledged", "in_progress", "assignee"),
    ("in_progress", "done", "assignee"),
    ("done", "closed", "filer"),
    ("done", "open", "filer"),
    ("closed", "open", "filer"),
]
STATUSES = ["open", "acknowledged", "in_progress", "done", "closed"]
ALLOWED = {(a, b) for a, b, _ in MOVES}


def _ticket(db, status="open"):
    t = create_ticket(db, "her", {"title": "Task"})      # filer her, assignee him
    old = at("2026-01-01")
    set_times(db, t["id"], updated=old, status=status)
    return t["id"]


def _party(who):
    return "him" if who == "assignee" else "her"


def _other(who):
    return "her" if who == "assignee" else "him"


@pytest.mark.parametrize("src,dst,who", MOVES)
def test_each_allowed_move(db, src, dst, who):
    tid = _ticket(db, src)
    t = change_status(db, tid, _party(who), dst)
    assert t["id"] == tid
    assert t["status"] == dst
    updated = dt.datetime.fromisoformat(t["updated_at"])
    assert updated > at("2026-01-01")
    assert dt.datetime.now(dt.timezone.utc) - updated < dt.timedelta(minutes=1)


@pytest.mark.parametrize("src,dst,who", MOVES)
def test_each_allowed_move_by_the_wrong_party_raises_permission_error(db, src, dst, who):
    tid = _ticket(db, src)
    with pytest.raises(PermissionError):
        change_status(db, tid, _other(who), dst)


@pytest.mark.parametrize("src,dst", [(a, b) for a in STATUSES for b in STATUSES if (a, b) not in ALLOWED])
def test_every_move_not_in_the_table_raises_value_error(db, src, dst):
    tid = _ticket(db, src)
    for user in ("her", "him"):
        with pytest.raises(ValueError):
            change_status(db, tid, user, dst)


@pytest.mark.parametrize("bad", ["ghost", "", "OPEN", None])
def test_unknown_status_raises_value_error(db, bad):
    tid = _ticket(db)
    with pytest.raises(ValueError):
        change_status(db, tid, "him", bad)


def test_missing_ticket_raises_lookup_error(db):
    with pytest.raises(LookupError):
        change_status(db, 999999, "him", "acknowledged")


def test_user_who_is_not_a_party_raises_lookup_error(db):
    tid = _ticket(db)
    with pytest.raises(LookupError):
        change_status(db, tid, "stranger", "acknowledged")


def test_lookup_error_comes_before_value_error(db):
    with pytest.raises(LookupError):
        change_status(db, 999999, "him", "ghost")


def test_value_error_comes_before_permission_error(db):
    tid = _ticket(db, "open")
    # open -> done is not in the table: ValueError even for the filer, who could never make it
    with pytest.raises(ValueError):
        change_status(db, tid, "her", "done")


@pytest.mark.parametrize("user,dst", [("her", "acknowledged"), ("him", "closed"), ("him", "ghost"), ("stranger", "acknowledged")])
def test_a_raising_call_leaves_the_ticket_unchanged(db, user, dst):
    from app.models import Ticket
    tid = _ticket(db, "open")
    with pytest.raises((LookupError, ValueError, PermissionError)):
        change_status(db, tid, user, dst)
    db.expire_all()
    t = db.get(Ticket, tid)
    assert t.status == "open"
    assert t.updated_at == at("2026-01-01")


def test_the_full_life_of_a_ticket(db):
    tid = create_ticket(db, "him", {"title": "Laundry"})["id"]     # filer him, assignee her
    assert change_status(db, tid, "her", "acknowledged")["status"] == "acknowledged"
    assert change_status(db, tid, "her", "in_progress")["status"] == "in_progress"
    assert change_status(db, tid, "her", "done")["status"] == "done"
    assert change_status(db, tid, "him", "open")["status"] == "open"
    change_status(db, tid, "her", "acknowledged")
    change_status(db, tid, "her", "in_progress")
    change_status(db, tid, "her", "done")
    assert change_status(db, tid, "him", "closed")["status"] == "closed"
    assert change_status(db, tid, "him", "open")["status"] == "open"


def test_change_status_is_committed(db):
    from app.db import SessionLocal
    from app.models import Ticket
    tid = _ticket(db, "open")
    change_status(db, tid, "him", "acknowledged")
    other = SessionLocal()
    try:
        assert other.get(Ticket, tid).status == "acknowledged"
    finally:
        other.close()
