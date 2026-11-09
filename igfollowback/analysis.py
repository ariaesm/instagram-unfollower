"""Set logic: who doesn't follow back, fans and mutuals."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .parser import Account


def _dedupe(accounts: Iterable[Account]) -> dict[str, Account]:
    out: dict[str, Account] = {}
    for a in accounts:
        out.setdefault(a.username, a)
    return out


@dataclass(frozen=True)
class Report:
    followers_count: int
    following_count: int
    not_following_back: list[Account]  # you follow them, they don't follow you
    fans: list[Account]  # they follow you, you don't follow them
    mutuals: list[Account]

    def as_dict(self) -> dict[str, object]:
        def rows(accounts: list[Account]) -> list[dict[str, object]]:
            return [
                {
                    "username": a.username,
                    "url": a.url,
                    "since": a.followed_at.isoformat() if a.followed_at else None,
                }
                for a in accounts
            ]

        return {
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "not_following_back": rows(self.not_following_back),
            "fans": rows(self.fans),
            "mutuals": rows(self.mutuals),
        }


def _sort(accounts: Iterable[Account], by: str) -> list[Account]:
    if by == "username":
        return sorted(accounts, key=lambda a: a.username)
    if by == "date":
        # Oldest first; entries without a timestamp go last.
        return sorted(accounts, key=lambda a: (a.timestamp is None, a.timestamp or 0, a.username))
    raise ValueError(f"unknown sort key {by!r} (use 'username' or 'date')")


def analyze(
    followers: Iterable[Account],
    following: Iterable[Account],
    sort_by: str = "username",
    exclude: Iterable[str] = (),
) -> Report:
    fol = _dedupe(followers)
    ing = _dedupe(following)
    skip = {u.strip().lstrip("@").lower() for u in exclude}
    nfb = [ing[u] for u in ing.keys() - fol.keys() if u not in skip]
    fans = [fol[u] for u in fol.keys() - ing.keys() if u not in skip]
    # For mutuals keep the "following" record (its timestamp = when you followed them).
    mutuals = [ing[u] for u in ing.keys() & fol.keys()]
    return Report(
        followers_count=len(fol),
        following_count=len(ing),
        not_following_back=_sort(nfb, sort_by),
        fans=_sort(fans, sort_by),
        mutuals=_sort(mutuals, sort_by),
    )
