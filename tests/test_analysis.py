import pytest

from igfollowback.analysis import analyze
from igfollowback.parser import Account


def accs(*names, ts=None):
    return [Account(n, timestamp=ts) for n in names]


def test_categories():
    r = analyze(accs("a", "b", "c"), accs("b", "c", "d", "e"))
    assert [a.username for a in r.not_following_back] == ["d", "e"]
    assert [a.username for a in r.fans] == ["a"]
    assert [a.username for a in r.mutuals] == ["b", "c"]
    assert (r.followers_count, r.following_count) == (3, 4)


def test_duplicates_counted_once():
    r = analyze(accs("a", "a"), accs("a", "b", "b"))
    assert (r.followers_count, r.following_count) == (1, 2)
    assert [a.username for a in r.not_following_back] == ["b"]


def test_exclude_list():
    r = analyze(accs("a"), accs("b", "celebrity"), exclude=["@Celebrity"])
    assert [a.username for a in r.not_following_back] == ["b"]


def test_sort_by_date_puts_missing_last():
    following = [Account("z", timestamp=1), Account("y", timestamp=None), Account("x", timestamp=5)]
    r = analyze([], following, sort_by="date")
    assert [a.username for a in r.not_following_back] == ["z", "x", "y"]


def test_bad_sort_key():
    with pytest.raises(ValueError):
        analyze([], accs("a"), sort_by="followers")


def test_as_dict_is_json_ready():
    d = analyze(accs("a"), [Account("b", timestamp=0)]).as_dict()
    assert d["not_following_back"] == [
        {
            "username": "b",
            "url": "https://www.instagram.com/b",
            "since": "1970-01-01T00:00:00+00:00",
        }
    ]
    assert d["fans"][0]["since"] is None
