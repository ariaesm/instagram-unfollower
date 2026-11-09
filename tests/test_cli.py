import csv
import json
from pathlib import Path

from igfollowback.cli import main

ROOT = Path(__file__).resolve().parent.parent / "examples"
EXPORT = ROOT / "instagram-export"
FF = EXPORT / "connections" / "followers_and_following"


def test_export_dir_summary(capsys):
    assert main(["--export", str(EXPORT), "--quiet"]) == 0
    out = capsys.readouterr().out
    assert "Followers: 7 | Following: 8 | Not following back: 4 | Fans: 3 | Mutuals: 4" in out


def test_explicit_files_and_exclude(capsys):
    code = main(
        [
            "--followers",
            str(FF / "followers_1.json"),
            "--following",
            str(FF / "following.json"),
            "--exclude",
            str(ROOT / "exclude.txt"),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "@fake_heidi_08" in out
    assert "@fake_brand_11" not in out


def test_csv_and_json_export(tmp_path, capsys):
    c, j = tmp_path / "r.csv", tmp_path / "r.json"
    assert main(["--export", str(EXPORT), "--csv", str(c), "--json", str(j), "-q"]) == 0
    rows = list(csv.DictReader(c.open(encoding="utf-8")))
    assert len(rows) == 4 + 3 + 4
    assert {r["category"] for r in rows} == {"nonfollowers", "fans", "mutuals"}
    report = json.loads(j.read_text())
    assert report["followers_count"] == 7
    assert len(report["fans"]) == 3


def test_missing_input_is_an_error(capsys):
    try:
        main([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected SystemExit")


def test_bad_show_value(capsys):
    assert main(["--export", str(EXPORT), "--show", "enemies"]) == 2
    assert "unknown category" in capsys.readouterr().err


def test_bad_file_reports_error(tmp_path, capsys):
    bad = tmp_path / "f.json"
    bad.write_text('{"nope": 1}')
    assert main(["--followers", str(bad), "--following", str(bad)]) == 2
    assert "error:" in capsys.readouterr().err
