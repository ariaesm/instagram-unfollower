"""Parsers for Instagram's official "Download your information" JSON export.

Two shapes are found in real exports:

* ``followers_1.json`` (and ``followers_2.json`` ... for large accounts) is a
  top-level **list** of relationship objects.
* ``following.json`` is an **object** wrapping the same list under
  ``"relationships_following"``.

Each relationship object looks like::

    {"title": "", "media_list_data": [],
     "string_list_data": [{"href": "https://www.instagram.com/someone",
                           "value": "someone", "timestamp": 1700000000}]}

Newer exports sometimes put the username in ``title`` and omit ``value``; as a
last resort the username is taken from the ``href`` URL.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FOLLOWERS_RE = re.compile(r"(^|/)followers(_\d+)?\.json$")
_FOLLOWING_RE = re.compile(r"(^|/)following\.json$")


class ExportFormatError(ValueError):
    """Raised when a file does not look like an Instagram followers/following export."""


@dataclass(frozen=True)
class Account:
    username: str
    href: str | None = None
    timestamp: int | None = None

    @property
    def url(self) -> str:
        return self.href or f"https://www.instagram.com/{self.username}"

    @property
    def followed_at(self) -> dt.datetime | None:
        if self.timestamp is None:
            return None
        return dt.datetime.fromtimestamp(self.timestamp, tz=dt.UTC)


def _username_from_href(href: str) -> str:
    path = href.split("?", 1)[0].rstrip("/")
    name = path.rsplit("/", 1)[-1]
    return "" if name in ("", "_u") else name


def _entries(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        lists = [
            v for k, v in data.items() if k.startswith("relationships_") and isinstance(v, list)
        ]
        if len(lists) == 1:
            return lists[0]
    raise ExportFormatError(
        "expected a list of relationships or an object with a 'relationships_*' list"
    )


def parse_relationships(data: Any) -> list[Account]:
    """Parse already-loaded JSON (either shape) into a list of :class:`Account`."""
    accounts: list[Account] = []
    for entry in _entries(data):
        if not isinstance(entry, dict):
            raise ExportFormatError(f"relationship entry is not an object: {entry!r}")
        items = entry.get("string_list_data") or [{}]
        for item in items:
            href = item.get("href")
            username = (
                item.get("value")
                or entry.get("title")
                or (_username_from_href(href) if href else "")
            )
            if not username:
                raise ExportFormatError(f"could not find a username in entry: {entry!r}")
            accounts.append(Account(username.strip().lower(), href, item.get("timestamp")))
    return accounts


def load_file(path: str | Path) -> list[Account]:
    with open(path, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ExportFormatError(f"{path}: invalid JSON ({exc})") from exc
    try:
        return parse_relationships(data)
    except ExportFormatError as exc:
        raise ExportFormatError(f"{path}: {exc}") from exc


def load_many(paths: Iterable[str | Path]) -> list[Account]:
    out: list[Account] = []
    for p in paths:
        out.extend(load_file(p))
    return out


def _iter_export(root: Path) -> Iterator[tuple[str, Any]]:
    """Yield ``(relative_name, parsed_json)`` for every .json file in a dir or zip."""
    if root.is_dir():
        for p in sorted(root.rglob("*.json")):
            yield p.relative_to(root).as_posix(), p
    elif zipfile.is_zipfile(root):
        with zipfile.ZipFile(root) as zf:
            for name in sorted(zf.namelist()):
                if name.endswith(".json"):
                    yield name, json.loads(zf.read(name).decode("utf-8"))
    else:
        raise ExportFormatError(f"{root} is neither a directory nor a zip file")


def load_export(root: str | Path) -> tuple[list[Account], list[Account]]:
    """Find and load followers/following files inside an export directory or zip."""
    followers: list[Account] = []
    following: list[Account] = []
    found_followers = found_following = False
    for name, payload in _iter_export(Path(root)):
        target = None
        if _FOLLOWERS_RE.search(name):
            target, found_followers = followers, True
        elif _FOLLOWING_RE.search(name):
            target, found_following = following, True
        if target is None:
            continue
        if isinstance(payload, Path):
            target.extend(load_file(payload))
        else:
            target.extend(parse_relationships(payload))
    if not (found_followers and found_following):
        raise ExportFormatError(
            f"could not find followers_*.json and following.json under {root} "
            "(make sure you requested the export in JSON format)"
        )
    return followers, following
