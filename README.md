# igfollowback - who doesn't follow you back on Instagram (offline)

A small Python CLI that tells you **who you follow that doesn't follow you back**, plus your
**fans** (they follow you, you don't follow them) and **mutuals**, using the data export
Instagram itself gives you.

## Why offline? (no login, no scraping, no API)

This tool **deliberately** does not log in to Instagram, scrape pages or call any
unofficial/third-party API. Automated access is against
[Instagram's Terms of Use](https://help.instagram.com/581066165581870), and "unfollower"
apps that ask for your password are a common way to get accounts rate-limited, locked or
stolen. Instead it reads the JSON files from Instagram's official
**"Download your information"** feature. Your password never leaves Instagram, nothing is
sent over the network, and the analysis runs entirely on your computer.

## Features

- Reads both shapes found in real exports:
  - `followers_1.json` (also `followers_2.json`, ... for big accounts) - a top-level list of
    `{"string_list_data": [{"href", "value", "timestamp"}]}` objects;
  - `following.json` - an object `{"relationships_following": [...]}` with the same entries.
  - Newer exports that put the username in `title` (or only in the `href`) are handled too.
- Point it at the **unzipped export folder or the `.zip` itself**; files are found automatically.
- Three lists: not following back, fans, mutuals - with the date the follow happened.
- Sort by username or by date (`--sort date`: oldest follows first).
- Ignore list (`--exclude file.txt`) for brands/celebrities you never expect a follow-back from.
- Export to **CSV** and **JSON**.
- Standard library only - no runtime dependencies.

## Getting your data from Instagram

1. In the Instagram app or website go to **Accounts Center → Your information and
   permissions → Download your information**.
2. Choose your account, select **Followers and following** (that's all this tool needs).
3. Pick **Format: JSON** (not HTML) and request the download.
4. When Instagram emails you, download the `.zip`. Inside it the relevant files live in
   `connections/followers_and_following/`.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/ariaesm/instagram-unfollwer-using-python.git
cd instagram-unfollwer-using-python
pip install -r requirements.txt   # only needed to run the tests
```

## Usage

`examples/` contains a tiny **fake** export (usernames like `fake_alice_01`) so you can try
it right away. All output below is real output from running the commands on that sample.

```console
$ python -m igfollowback --export examples/instagram-export --sort date --exclude examples/exclude.txt
Followers: 7 | Following: 8 | Not following back: 3 | Fans: 3 | Mutuals: 4

Not following you back (3):
  @fake_heidi_08  (since 2024-04-02)
  @fake_ivan_09  (since 2024-04-25)
  @fake_judy_10  (since 2024-05-18)
```

Show everything (`--show all`, or a comma-separated subset of `nonfollowers,fans,mutuals`):

```console
$ python -m igfollowback --export examples/instagram-export --show all
Followers: 7 | Following: 8 | Not following back: 4 | Fans: 3 | Mutuals: 4

Not following you back (4):
  @fake_brand_11  (since 2024-06-10)
  @fake_heidi_08  (since 2024-04-02)
  @fake_ivan_09  (since 2024-04-25)
  @fake_judy_10  (since 2024-05-18)

Fans (follow you, you don't follow them) (3):
  @fake_erin_05  (since 2024-03-09)
  @fake_frank_06  (since 2024-03-26)
  @fake_grace_07  (since 2024-04-12)

Mutuals (4):
  @fake_alice_01  (since 2024-01-01)
  @fake_bob_02  (since 2024-01-24)
  @fake_carol_03  (since 2024-02-16)
  @fake_dave_04  (since 2024-03-10)
```

"since" is the date you followed them (non-followers, mutuals) or they followed you (fans).

Export to CSV / JSON (exports always contain all three categories):

```console
$ python -m igfollowback --export examples/instagram-export -q --csv report.csv --json report.json
Followers: 7 | Following: 8 | Not following back: 4 | Fans: 3 | Mutuals: 4

Wrote 11 rows to report.csv
Wrote JSON report to report.json
$ head -3 report.csv
category,username,url,since
nonfollowers,fake_brand_11,https://www.instagram.com/_u/fake_brand_11,2024-06-10T00:00:00+00:00
nonfollowers,fake_heidi_08,https://www.instagram.com/fake_heidi_08,2024-04-02T00:00:00+00:00
```

You can also pass files explicitly (repeat `--followers` for split files):

```bash
python -m igfollowback \
  --followers followers_1.json --followers followers_2.json \
  --following following.json --show nonfollowers,fans
```

Run `python -m igfollowback --help` for all options.

## Limitations

- The result is a snapshot of the moment you requested the export; request a new one to refresh.
- Deactivated or deleted accounts may still appear in one of the files.
- Instagram occasionally changes the export layout; if parsing fails you'll get a clear
  error - please open an issue with the (anonymised) structure.

## Tests

```bash
python -m pytest -q
```

CI (GitHub Actions) runs `ruff` and `pytest` on Python 3.12.

## License

MIT - see [LICENSE](LICENSE).
