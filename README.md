# Iffert Media Operations Bot — MVP

This is Phase 1: bot online 24/7, one-time scheduled messages, recurring
scheduled messages, and a basic slash command. It's built so Phase 2/3
features (roles, certifications, AI commands) can be added as new files
in `cogs/` without touching this core.

## What's included

- `/ping` — confirms the bot is alive
- `/schedule` — one-time message: pick a channel + date + time, then a
  popup form for the message text
- `/every` — recurring message: `monday 9am`, `day 8am`, `friday 5pm`,
  `first sunday 9am`, etc.
- `/scheduled` — lists everything currently queued
- `/unschedule <job_id>` — cancels a scheduled or recurring message

Scheduled jobs are stored in `data/schedule.db` (SQLite), so they survive
a bot restart or redeploy — this was called out earlier as the part most
first-attempt bots get wrong (in-memory schedulers silently lose all
recurring jobs on every restart).

## 1. Create the Discord application

1. Go to https://discord.com/developers/applications → **New Application**.
2. Name it (e.g. "Iffert Media Ops") → **Create**.
3. Go to the **Bot** tab → **Reset Token** → copy it. This goes in `.env`
   as `DISCORD_TOKEN`. Treat it like a password — never share it or commit it.
4. On the same page, under **Privileged Gateway Intents**, enable
   **Server Members Intent** (needed later for welcome messages / role
   assignment; harmless to enable now).

## 2. Invite the bot to your server

1. Go to **OAuth2 → URL Generator**.
2. Scopes: check `bot` and `applications.commands`.
3. Bot Permissions: check `Send Messages`, `Read Messages/View Channels`,
   `Manage Roles` (for Phase 2), `Embed Links`.
4. Copy the generated URL, open it in a browser, and add the bot to your
   server.

## 3. Local setup

```bash
git clone <this-repo>  # or just use the files as-is
cd iffert-bot
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `DISCORD_TOKEN` — from step 1
- `GUILD_ID` — your server's ID (enable Developer Mode in Discord settings
  → right-click your server icon → Copy Server ID). Strongly recommended
  during development since it makes slash commands appear instantly
  instead of waiting up to an hour for the global sync.

## 4. Run it

```bash
python3 bot.py
```

You should see `Logged in as <bot name>`. In Discord, try `/ping`.

## 5. Try scheduling

- `/schedule channel:#launchpad date:August 5 time:8:00 AM` → opens a form
  for the message → submit → it posts automatically at that time.
- `/every channel:#general recurrence:monday 9am` → opens a form for the
  message → posts every Monday at 9am indefinitely.
- `/scheduled` → see everything queued, with job IDs.
- `/unschedule job_id:every-XXXXXXXX` → cancel one.

## Deploying for 24/7 uptime (Railway)

1. Push this folder to a GitHub repo (`.env` and `data/` are already
   gitignored — set the same environment variables in Railway's dashboard
   instead).
2. Create a new Railway project from that repo.
3. Set `DISCORD_TOKEN` (and optionally `GUILD_ID`, `BOT_TIMEZONE`) in
   Railway's **Variables** tab.
4. **Important:** attach a **Volume** mounted at `/app/data` (or wherever
   your working directory ends up). Railway's default filesystem is wiped
   on every redeploy — without a volume, `schedule.db` gets deleted and
   every recurring message silently stops firing the next time you push
   a change. This is worth doing before you rely on it, not after you
   notice Monday's post didn't go out.
5. Set the start command to `python3 bot.py`.

## Known limitations of this MVP (by design, not oversight)

- `/schedule` and `/every` currently require a Discord staff member to
  type the recurrence in one of a few fixed formats (`monday 9am`, `day
  8am`, `first sunday 9am`). It's not a full natural-language parser —
  intentionally, to keep Phase 1 shippable. Easy to extend in
  `cogs/time_parsing.py`.
- No creator database yet (`/creator`, `/certify`, level tracking) — that's
  Phase 2, and will need a proper SQLite schema (or Google Sheets sync)
  rather than reusing the scheduler's job store.
- No AI-generated content (`/voiceover`, `/cover`, `/graphic`) — Phase 3,
  and will need an Anthropic or OpenAI API key wired in separately.

## Project structure

```
iffert-bot/
  bot.py              # entry point, loads cogs, starts scheduler
  jobs.py             # functions the scheduler actually calls to post messages
  cogs/
    general.py        # /ping
    scheduler.py       # /schedule, /every, /unschedule, /scheduled
    time_parsing.py    # date/time/recurrence string parsing
  requirements.txt
  .env.example
  data/                # created automatically; holds schedule.db (gitignored)
```
