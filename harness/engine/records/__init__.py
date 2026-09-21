# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The record set (spec 02). Plain text, append-only, under version control."""
import datetime
import pathlib
import zoneinfo


class TimezoneUnavailable(Exception):
    pass


def zone(cfg):
    """The single stated timezone. If it cannot be resolved on this system the
    record is refused: writing a different timezone silently would make every
    timestamp in the series mean something other than it says."""
    tz_name = cfg.timezone if cfg else "UTC"
    if tz_name in ("UTC", "Etc/UTC", "Z"):
        return datetime.timezone.utc
    try:
        return zoneinfo.ZoneInfo(tz_name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError) as e:
        raise TimezoneUnavailable(f"timezone {tz_name!r} is not available on this system ({e}); "
                                  "install tzdata or set the configured timezone to UTC") from None


def now(cfg):
    """A timestamp in the single stated timezone (spec 02 REQ-2.5.1), from the
    source the configuration names (the workstation clock unless told otherwise)."""
    return datetime.datetime.now(zone(cfg)).replace(microsecond=0).isoformat()


def today(cfg):
    return now(cfg)[:10]


def records_dir(root):
    return pathlib.Path(root) / ".engine" / "records"
