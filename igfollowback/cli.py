"""Command-line interface: ``python -m igfollowback``."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .analysis import Report, analyze
from .parser import Account, ExportFormatError, load_export, load_many

CATEGORIES = {
    "nonfollowers": ("not_following_back", "Not following you back"),
    "fans": ("fans", "Fans (follow you, you don't follow them)"),
    "mutuals": ("mutuals", "Mutuals"),
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="igfollowback",
        description=(
            "Find who doesn't follow you back using Instagram's official JSON data "
            "export. Works fully offline: no login, no scraping, no API."
        ),
    )
    src = p.add_argument_group("input (use --export OR --followers + --following)")
    src.add_argument("--export", type=Path, help="export folder or .zip downloaded from Instagram")
    src.add_argument(
        "--followers",
        type=Path,
        action="append",
        default=[],
        help="followers_N.json file (repeat for followers_2.json, ...)",
    )
    src.add_argument("--following", type=Path, action="append", default=[], help="following.json")
    p.add_argument(
        "--show",
        default="nonfollowers",
        help="comma-separated: nonfollowers,fans,mutuals or 'all' (default: nonfollowers)",
    )
    p.add_argument("--sort", choices=["username", "date"], default="username")
    p.add_argument(
        "--exclude",
        type=Path,
        help="text file with usernames to ignore (one per line, e.g. celebrities)",
    )
    p.add_argument("--csv", type=Path, help="write all categories to this CSV file")
    p.add_argument("--json", type=Path, help="write the full report to this JSON file")
    p.add_argument("-q", "--quiet", action="store_true", help="only print the summary")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _parse_show(value: str) -> list[str]:
    if value.strip() == "all":
        return list(CATEGORIES)
    chosen = [v.strip() for v in value.split(",") if v.strip()]
    unknown = [c for c in chosen if c not in CATEGORIES]
    if unknown or not chosen:
        raise ValueError(f"--show: unknown category {unknown or value!r}")
    return chosen


def write_csv(report: Report, path: Path) -> int:
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["category", "username", "url", "since"])
        for key, (attr, _) in CATEGORIES.items():
            for a in getattr(report, attr):
                since = a.followed_at.isoformat() if a.followed_at else ""
                writer.writerow([key, a.username, a.url, since])
                rows += 1
    return rows


def write_json(report: Report, path: Path) -> None:
    path.write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False) + "\n", "utf-8")


def _format_account(a: Account) -> str:
    since = f"  (since {a.followed_at:%Y-%m-%d})" if a.followed_at else ""
    return f"  @{a.username}{since}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        show = _parse_show(args.show)
        if args.export:
            if args.followers or args.following:
                parser.error("use either --export or --followers/--following, not both")
            followers, following = load_export(args.export)
        elif args.followers and args.following:
            followers, following = load_many(args.followers), load_many(args.following)
        else:
            parser.error("provide --export, or both --followers and --following")
        exclude: list[str] = []
        if args.exclude:
            exclude = [
                ln.strip()
                for ln in args.exclude.read_text("utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")
            ]
        report = analyze(followers, following, sort_by=args.sort, exclude=exclude)
    except (ExportFormatError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Followers: {report.followers_count} | Following: {report.following_count} | "
        f"Not following back: {len(report.not_following_back)} | "
        f"Fans: {len(report.fans)} | Mutuals: {len(report.mutuals)}"
    )
    if not args.quiet:
        for key in show:
            attr, title = CATEGORIES[key]
            accounts = getattr(report, attr)
            print(f"\n{title} ({len(accounts)}):")
            for a in accounts:
                print(_format_account(a))
            if not accounts:
                print("  (none)")
    if args.csv:
        n = write_csv(report, args.csv)
        print(f"\nWrote {n} rows to {args.csv}")
    if args.json:
        write_json(report, args.json)
        print(f"Wrote JSON report to {args.json}")
    return 0
