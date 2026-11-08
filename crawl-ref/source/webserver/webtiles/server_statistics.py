"""Read aggregate results from normal-game xlogfiles, without player details."""
from pathlib import Path
import re
import threading
import time


_SEPARATOR = re.compile(r"(?<=[^:]):(?=[^:])")
_lock = threading.Lock()
_cached_key = None
_cached_at = 0
_cached_value = None


def collect_statistics(directory, excluded_players=()):
    if not directory or not Path(directory).is_dir():
        return {"available": False}
    excluded = {name.casefold() for name in excluded_players}
    completed = wins = total_seconds = 0
    best_score = None
    seen = set()
    # Sprint, tutorial and other modes use suffixed logfile names in DCSS.
    for path in sorted(Path(directory).glob("*/logfile")):
        if path.parent.name.casefold() in excluded:
            continue
        try:
            stream = path.open(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        with stream:
            for line in stream:
                # A game may be appending its final record during this read.
                if not line.endswith("\n"):
                    continue
                fields = {}
                for entry in _SEPARATOR.split(line.strip()):
                    key, separator, value = entry.partition("=")
                    if separator:
                        fields[key] = value.replace("::", ":")
                if not all(fields.get(k) for k in ("name", "start", "end", "ktyp")):
                    continue
                if fields["name"].casefold() in excluded:
                    continue
                try:
                    score, duration = int(fields["sc"]), int(fields["dur"])
                    if score < 0 or duration < 0 or int(fields.get("wiz", 0)) or int(fields.get("explore", 0)):
                        continue
                except (KeyError, ValueError):
                    continue
                identity = (fields["name"].casefold(), fields["start"], fields["end"])
                if identity in seen:
                    continue
                seen.add(identity)
                completed += 1
                wins += fields["ktyp"] == "winning"
                total_seconds += duration
                best_score = score if best_score is None else max(best_score, score)
    return dict(available=True, completed=completed, wins=wins,
                best_score=best_score, total_seconds=total_seconds)


def cached_statistics(directory, excluded_players=()):
    global _cached_key, _cached_at, _cached_value
    key = (str(directory), tuple(sorted(name.casefold() for name in excluded_players)))
    with _lock:
        now = time.monotonic()
        if key != _cached_key or now - _cached_at >= 30 or _cached_value is None:
            value = collect_statistics(directory, excluded_players)
            _cached_key, _cached_at, _cached_value = key, now, value
        return dict(_cached_value)
