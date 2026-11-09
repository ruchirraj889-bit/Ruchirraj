"""Government vacancy watcher (History / PG-level, India).
Scans sources -> keeps posts whose title matches a POST keyword and whose subject is History
-> sends only NEW items to Telegram."""
import hashlib, json, os, re, sys
from urllib.parse import urljoin

import feedparser, requests, yaml
from bs4 import BeautifulSoup

SEEN_FILE = "seen.json"
MAX_PER_RUN = 30
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; vacancy-bot/1.1)"}


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f)), True
    except FileNotFoundError:
        return set(), False


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f)


def items_from_source(src):
    if src["type"] == "rss":
        for e in feedparser.parse(src["url"]).entries:
            yield e.get("title", ""), e.get("link", "")
        return
    r = requests.get(src["url"], headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if len(text) >= 10:
            yield text, urljoin(src["url"], a["href"])


def any_match(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def page_text(url):
    """Return lowercase text of a linked HTML page, or None if it can't be read."""
    if url.lower().endswith(".pdf"):
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if "html" not in r.headers.get("content-type", ""):
            return None
        return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:200000]
    except Exception:
        return None


def send_telegram(text):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return
    # Telegram's limit is 4096 chars per message, so send in chunks
    chunk = ""
    for block in text.split("\n\n"):
        if len(chunk) + len(block) + 2 > 3800:
            _post(token, chat, chunk)
            chunk = ""
        chunk += block + "\n\n"
    if chunk.strip():
        _post(token, chat, chunk)


def _post(token, chat, text):
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text.strip(), "disable_web_page_preview": True},
        timeout=30,
    ).raise_for_status()


def main():
    cfg = yaml.safe_load(open("sources.yaml"))
    posts, subjects, excl = cfg["post_keywords"], cfg["subject_keywords"], cfg["exclude_keywords"]
    detail_budget = cfg.get("max_detail_fetches", 40)
    seen, existed = load_seen()
    new = []

    for src in cfg["sources"]:
        try:
            for title, link in items_from_source(src):
                if not link or any_match(excl, title) or not any_match(posts, title):
                    continue
                key = hashlib.sha1(link.encode()).hexdigest()
                if key in seen:
                    continue

                if src.get("trusted") or any_match(subjects, title):
                    ok = True
                elif detail_budget > 0:
                    detail_budget -= 1
                    body = page_text(link)
                    if body is None:
                        continue  # couldn't read it; try again next run
                    ok = any_match(subjects, body)
                else:
                    continue  # out of budget; retry next run

                seen.add(key)
                if ok:
                    new.append((src["name"], title, link))
        except Exception as e:
            print(f"[warn] {src['name']} failed: {e}", file=sys.stderr)

    if new:
        head = "Vacancy bot is live. Current matches:" if not existed else f"{len(new)} new vacancy update(s):"
        lines = [f"• [{s}] {t}\n{l}" for s, t, l in new[:MAX_PER_RUN]]
        if len(new) > MAX_PER_RUN:
            lines.append(f"...and {len(new) - MAX_PER_RUN} more.")
        send_telegram(head + "\n\n" + "\n\n".join(lines))
    save_seen(seen)
    print(f"Done. {len(new)} new item(s).")


if __name__ == "__main__":
    main()
