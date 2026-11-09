# Government Vacancy Bot

Scans job pages/RSS feeds, filters for Assistant Professor / PG-level posts, and sends new ones to Telegram.

## Setup (≈10 min, free)
1. In Telegram, message @BotFather → /newbot → copy the **token**.
2. Message your new bot once, then open
   https://api.telegram.org/bot<TOKEN>/getUpdates and copy your **chat id**.
3. Create a GitHub repo, upload these files (keep the .github folder).
4. Repo → Settings → Secrets and variables → Actions → add
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
5. Actions tab → "vacancy-bot" → Run workflow. It then runs every 6 hours.

## Run locally
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=...
    python bot.py      # without the env vars it just prints results

## Customise
Edit `sources.yaml`: add state PSC, university, IIT/NIT, central university and
institute career pages; tweak include/exclude keywords.
