import json
import zipfile
from pathlib import Path

import pytest

from igfollowback.parser import ExportFormatError, load_export, load_file, parse_relationships

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "instagram-export"


def rel(value=None, title="", href=None, ts=1700000000):
    item = {"timestamp": ts}
    if value is not None:
        item["value"] = value
    if href is not None:
        item["href"] = href
    return {"title": title, "media_list_data": [], "string_list_data": [item]}


def test_list_shape():
    accounts = parse_relationships([rel("Alice_Fake", href="https://www.instagram.com/alice_fake")])
    assert accounts[0].username == "alice_fake"  # normalised to lower-case
    assert accounts[0].timestamp == 1700000000
    assert accounts[0].followed_at.year == 2023


def test_relationships_following_shape():
    data = {"relationships_following": [rel("a_fake"), rel("b_fake")]}
    assert [a.username for a in parse_relationships(data)] == ["a_fake", "b_fake"]


def test_username_from_title_when_value_missing():
    assert parse_relationships([rel(title="t_fake")])[0].username == "t_fake"


@pytest.mark.parametrize(
    "href",
    [
        "https://www.instagram.com/h_fake",
        "https://www.instagram.com/h_fake/",
        "https://www.instagram.com/_u/h_fake",
        "https://www.instagram.com/h_fake?igsh=abc",
    ],
)
def test_username_from_href(href):
    assert parse_relationships([rel(href=href)])[0].username == "h_fake"


def test_default_url():
    assert parse_relationships([rel("x_fake")])[0].url == "https://www.instagram.com/x_fake"


@pytest.mark.parametrize(
    "bad",
    [{"something_else": []}, "text", [1, 2], [{"title": "", "string_list_data": [{}]}]],
)
def test_bad_shapes(bad):
    with pytest.raises(ExportFormatError):
        parse_relationships(bad)


def test_load_file_invalid_json(tmp_path):
    f = tmp_path / "followers_1.json"
    f.write_text("{not json")
    with pytest.raises(ExportFormatError, match="invalid JSON"):
        load_file(f)


def test_load_example_export_dir():
    followers, following = load_export(EXAMPLE)
    assert len(followers) == 7
    assert len(following) == 8


def test_load_export_zip_and_split_followers(tmp_path):
    z = tmp_path / "export.zip"
    base = "connections/followers_and_following/"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(base + "followers_1.json", json.dumps([rel("a_fake")]))
        zf.writestr(base + "followers_2.json", json.dumps([rel("b_fake")]))
        zf.writestr(
            base + "following.json", json.dumps({"relationships_following": [rel("a_fake")]})
        )
        zf.writestr(base + "close_friends.json", json.dumps({"relationships_close_friends": []}))
    followers, following = load_export(z)
    assert sorted(a.username for a in followers) == ["a_fake", "b_fake"]
    assert [a.username for a in following] == ["a_fake"]


def test_load_export_missing_files(tmp_path):
    (tmp_path / "following.json").write_text('{"relationships_following": []}')
    with pytest.raises(ExportFormatError, match="could not find"):
        load_export(tmp_path)
