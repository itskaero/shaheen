# Deploying BRAWLISTAN on the NAS (ZimaOS + Cloudflare)

docs/DECISIONS.md ADR-127. One Docker stack on the NAS runs:
- Postgres;
- the API;
- the Discord bot;
- nightly backups;
- a Cloudflare Tunnel.

The website stays on GitHub Pages under `brawlistan.rekorex.online`.

```
Discord ⇄ bot ─┐
               ├─ db (Postgres, internal only) ── backup (nightly pg_dump)
         api ──┘
          ▲  http://api:8000
cloudflared ── Cloudflare Tunnel ──▶ https://api.brawlistan.rekorex.online
GitHub Pages ─────────────────────▶ https://brawlistan.rekorex.online
```

No router ports are opened, and Postgres is never reachable from outside the stack. The tunnel connects
outwards, so it works behind CGNAT.

## Before you start

You need:
- The NAS (ZimaOS) with Docker and an SSH or terminal login (Settings → Developer mode → SSH, or the web
  terminal).
- A UPS or inverter for the NAS and the router.
- `rekorex.online` added to your Cloudflare account, with its nameservers pointed at Cloudflare.
- The bot token, guild ID and Brawlhalla API key, as in the README's prerequisites.

## 1. Cloudflare Tunnel (the API's public address)

1. Cloudflare dashboard → **Zero Trust → Networks → Tunnels → Create a tunnel** → **Cloudflared** → name it
   `brawlistan`.
2. On the install screen, choose **Docker** and copy only the token, the long string after `--token`. That's
   `TUNNEL_TOKEN`.
3. **Public hostnames → Add:**
   - Subdomain `api.brawlistan`, domain `rekorex.online`.
   - Service type `HTTP`, URL `api:8000`.

   Cloudflare creates the DNS record itself.

## 2. The stack on the NAS

Over SSH on the NAS:

```bash
mkdir -p /DATA/AppData/brawlistan && cd /DATA/AppData/brawlistan
# Get the two files from the repo (or copy them over from your computer):
curl -fsSLO https://raw.githubusercontent.com/itskaero/shaheen/main/deploy/nas/docker-compose.yml
curl -fsSL  https://raw.githubusercontent.com/itskaero/shaheen/main/deploy/nas/.env.example -o .env
openssl rand -hex 24          # use the output as POSTGRES_PASSWORD
nano .env                     # fill POSTGRES_PASSWORD, TUNNEL_TOKEN, DISCORD_TOKEN, DISCORD_GUILD_ID,
                              # BOT_OWNER_ID, BRAWLHALLA_API_KEY
chmod 600 .env
docker compose pull
docker compose up -d
docker compose ps             # db/api healthy, migrate "exited (0)", bot/cloudflared/backup running
```

**First start:**
1. `migrate` creates every table on the empty database, then exits.
2. `api` and `bot` start after it.
3. On the bot's first snapshot tick, it creates the starting teams (SHAHEEN and the four clan teams) and
   fills their rosters from the in-game clans.

**ZimaOS app store instead of SSH:**
- **App Store → Custom Install → Import** accepts the same `docker-compose.yml`.
- You enter the variables in its UI, and the data folders still default to `/DATA/AppData/brawlistan`.
- SSH is the dependable route: the app UI can't run `migrate` one-shot containers the same way on every
  ZimaOS version.

**Data on the NAS:**
- Postgres: `/DATA/AppData/brawlistan/postgres`
- Backups: `/DATA/AppData/brawlistan/backups/{daily,weekly,monthly}`, kept 7 days, 4 weeks and 3 months, made
  at midnight PKT.

## 3. The website at brawlistan.rekorex.online

1. **Cloudflare → DNS → Add record:**
   - type `CNAME`, name `brawlistan`, target `itskaero.github.io`;
   - **Proxy status: DNS only (grey cloud)** for now.
2. **GitHub → itskaero/shaheen → Settings → Pages → Custom domain:**
   - enter `brawlistan.rekorex.online` and save. The repo's `web/CNAME` already says the same;
   - wait for the DNS check and the certificate (minutes, sometimes up to an hour);
   - then tick **Enforce HTTPS**.
3. **Optional:** switch the record to **Proxied (orange cloud)** with SSL/TLS mode **Full**. Leave it grey
   if you see redirect loops.

The old `itskaero.github.io/shaheen` links redirect to the new domain automatically.

**The site talks to the API at `https://api.brawlistan.rekorex.online`** (`web/assets/js/config.js`). Every
6 hours, `snapshot.yml` fetches it and commits fresh `web/data/*.json`, so the site loads instantly and still
works when the NAS is off.

## 4. The image (one-time)

`.github/workflows/image.yml` builds `ghcr.io/itskaero/shaheen` on every push to `main` that changes the app.
After its first run:
1. Go to GitHub → your profile → **Packages → shaheen → Package settings**.
2. **Change visibility → Public**, so the NAS pulls without logging in. The image contains no secrets.

## 5. Switch off the old hosting

Only one bot may run on the token.
1. **Fly.io:** `flyctl scale count 0 -a shaheen-bot`. Delete the app once the NAS bot is answering.
2. **Render:** suspend or delete the `shaheen-api` service and the `shaheen-db` database.

## 6. In Discord after the move

The database is new, so set things up again:
1. `/setup status`, then `/setup run` if roles or channels need adopting.
2. `/access roles` and `/access status`, then `/access sync` for anyone missing Guest.
3. `/coach setup`.
4. Members run `/link` again, which puts them back on the Pakistan rankings.

## Everyday operations

| Task | Command (in `/DATA/AppData/brawlistan`) |
|---|---|
| Update after a merge | `docker compose pull && docker compose up -d` |
| Bot logs | `docker compose logs -f --tail=200 bot` |
| API health | `curl https://api.brawlistan.rekorex.online/health` |
| Restart one service | `docker compose restart bot` |
| Backup now | `docker compose exec backup /backup.sh` |
| Pin a version | set `BRAWLISTAN_IMAGE=ghcr.io/itskaero/shaheen:sha-<commit>` in `.env`, then `up -d` |

**Restore a backup** (this replaces the current data):

```bash
docker compose stop api bot
docker compose exec -T db dropdb -U brawlistan brawlistan
docker compose exec -T db createdb -U brawlistan brawlistan
gunzip -c backups/daily/brawlistan-latest.sql.gz | docker compose exec -T db psql -U brawlistan -d brawlistan
docker compose up -d
```

**Offsite copy (recommended).** Copy `backups/` to another disk or to cloud storage now and then, for
example with a ZimaOS sync or `rclone` to Cloudflare R2. A NAS-only backup doesn't survive the NAS.

## When something's down

- **The site still works.** It shows the last snapshots with a "Live data is unavailable" banner.
- **The bot is offline:**
  - check `docker compose ps` and `docker compose logs bot`;
  - members who joined meanwhile get their role from the access catch-up within 10 minutes of the bot
    returning (ADR-126).
- **The API is unreachable but `docker compose ps` is healthy:**
  - check the tunnel with `docker compose logs cloudflared`;
  - check its status in Cloudflare Zero Trust.
