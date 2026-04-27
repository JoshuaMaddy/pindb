# PinDB Deployment Guide

End-to-end instructions for standing up PinDB on a fresh Linux host, deploying
new versions, and managing the running stack by hand. The application uses a
zero-downtime blue/green Docker setup fronted by Caddy; see
[`CLAUDE.md`](./CLAUDE.md) for architecture detail.

---

## 1. From-Zero Host Setup

Target: a fresh Ubuntu/Debian VPS (Linode, EC2, Hetzner, etc.) with root or
sudo access.

### 1.1 Install Docker

```bash
# Docker Engine + Compose v2
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable --now docker
docker compose version   # confirm Compose v2 is present
```

`systemctl enable docker` is load-bearing — without it, containers will not
restart after a host reboot.

### 1.2 Install git and clone the repo

```bash
sudo apt-get update && sudo apt-get install -y git
git clone <your-fork-or-origin-url> /root/pindb
cd /root/pindb
```

You can clone anywhere; just use that path consistently for the systemd unit
later.

### 1.3 Create `.env`

```bash
cp .env.example .env
$EDITOR .env
```

Required variables (bootstrap will refuse to run without them):

- `POSTGRES_PASSWORD`
- `MEILISEARCH_KEY`

Other variables (OAuth client IDs/secrets, contact email, R2 credentials, etc.)
are optional and feature-gated. See [`src/pindb/config.py`](./src/pindb/config.py)
for the full list.

### 1.4 (Optional) Bootstrap admin users

Set in `.env`:

```
BOOTSTRAP_ADMIN_USERNAMES=alice,bob
```

These users are promoted to admin on app startup (after they sign up).

### 1.5 Run bootstrap

```bash
./scripts/bootstrap.sh
```

This will:

1. Validate `.env` and Docker prerequisites.
2. Build the four service images (`app_blue`, `app_green`, `migrate`,
   `scheduler`).
3. Release host port 8000 from any legacy single-`app` container (no-op on a
   fresh host).
4. Start postgres + meilisearch and wait for them to be healthy.
5. Run Alembic migrations.
6. Start `app_blue` and wait for `/healthz`.
7. Start `scheduler` and `proxy` (Caddy claims host:8000 — brief 502s through
   NPM happen only here, only the first time).
8. Smoke-test `http://localhost:8000/healthz`.

Bootstrap is idempotent. If it fails partway, fix the issue and re-run.

### 1.6 Install the systemd unit (recommended)

Without this, a host reboot will revive whatever containers were running before
shutdown — including the *inactive* color, which causes drift between the
state file and reality.

```bash
sudo cp scripts/pindb.service /etc/systemd/system/pindb.service
sudo sed -i "s|@WORKDIR@|$(pwd)|; s|@USER@|$(whoami)|" /etc/systemd/system/pindb.service
sudo systemctl daemon-reload
sudo systemctl enable --now pindb.service
```

The unit runs `scripts/start.sh`, which reads `.deploy-active-color` and
brings up only the active color, plus stops/removes the inactive one.

### 1.7 Point your reverse proxy at host:8000

Caddy listens on host port `8000`. If you run NPM (Nginx Proxy Manager) or
another upstream reverse proxy for TLS, point its `pindb` proxy entry at
`http://<host>:8000`.

---

## 2. Daily Deploys (Code Updates)

```bash
cd /root/pindb
git pull
./scripts/deploy.sh
```

`deploy.sh` does a blue/green swap:

1. Reads `.deploy-active-color` to determine current color.
2. Builds new images for both colors, `migrate`, and `scheduler`.
3. Runs Alembic migrations once (`migrate` profile).
4. Starts the *idle* color alongside the live one (`--force-recreate`).
5. Polls Docker for the new container to report `healthy` (~90s window).
6. Smoke-tests `http://localhost:8000/healthz` through Caddy.
7. Stops + removes the old color.
8. Restarts `scheduler` on the new image.
9. Updates `.deploy-active-color`.

If the new color never goes healthy, deploy aborts — the live color keeps
serving and the new container's logs are dumped to stderr.

### Migration discipline

During a swap, both colors run against the same DB for ~10–30s. Migrations
must be backward-compatible. See **Migration discipline** in
[`CLAUDE.md`](./CLAUDE.md) for the rules.

---

## 3. Manual Operations

All commands assume `cd /root/pindb` (or wherever you cloned).

### 3.1 Check status

```bash
docker ps --filter name=pindb
cat .deploy-active-color
curl -fsS http://localhost:8000/healthz
```

The active color in `.deploy-active-color` should match the running
`pindb-app_<color>-1` container. If they disagree, see **Recovery** below.

### 3.2 View logs

```bash
docker logs -f pindb-app_blue-1        # or app_green
docker logs -f pindb-scheduler-1
docker logs -f pindb_proxy             # Caddy
docker logs -f pindb-postgres-1
```

App logs also persist to `./logs/pindb.log` (mounted into the containers).

### 3.3 Bring the stack up

After `docker compose down`, manual pruning, or any time containers are gone:

```bash
./scripts/start.sh
```

This brings up postgres, meilisearch, the active color, scheduler, and proxy,
then stops/removes the inactive color.

### 3.4 Bring the stack down

Stop everything but keep volumes (DB + Meili + Caddy data preserved):

```bash
docker compose --profile blue --profile green down
```

If the systemd unit is installed, also stop it so it won't bring the stack
back on the next boot:

```bash
sudo systemctl stop pindb.service
sudo systemctl disable pindb.service   # only if you want it gone permanently
```

### 3.5 Restart a single service

```bash
docker compose restart scheduler
docker compose restart proxy
docker compose --profile blue restart app_blue   # or green
```

### 3.6 Force a blue/green swap (no code change)

```bash
./scripts/deploy.sh
```

Identical-image case is handled by `--force-recreate`; the script will still
spin a fresh container, swap, and update the state file.

### 3.7 Run Alembic by hand

```bash
docker compose --profile migrate run --rm migrate                      # upgrade head
docker compose --profile migrate run --rm migrate uv run alembic current
docker compose --profile migrate run --rm migrate uv run alembic downgrade -1
```

### 3.8 Open a psql shell

```bash
docker compose exec postgres psql -U pindb -d pindb
```

### 3.9 Backups

```bash
# DB
uv run python scripts/dump_db.py --via-docker > pindb-$(date +%F).sql

# Images (filesystem backend only)
tar czf images-$(date +%F).tar.gz images/

# Meilisearch dump
curl -X POST -H "Authorization: Bearer $MEILISEARCH_KEY" \
  http://localhost:7700/dumps
```

---

## 4. Recovery

### 4.1 State file disagrees with running containers

Check what's actually running, then write the truth into the state file:

```bash
docker ps --filter name=pindb-app_
echo blue > .deploy-active-color   # or green — match reality
./scripts/start.sh
```

### 4.2 Both colors running

Should only happen after a host reboot without the systemd unit installed. Stop
the inactive one:

```bash
ACTIVE=$(cat .deploy-active-color)
[ "$ACTIVE" = "blue" ] && OTHER=green || OTHER=blue
docker compose --profile "$OTHER" stop "app_$OTHER"
docker compose --profile "$OTHER" rm -f "app_$OTHER"
```

### 4.3 No app container running

```bash
./scripts/start.sh
```

If that fails, check `.deploy-active-color` is set and the image was built:

```bash
docker images | grep pindb-app_
docker compose --profile blue --profile green build app_blue app_green
./scripts/start.sh
```

### 4.4 Image upload returns `PermissionError`

Host bind-mount `./images` is owned by a different UID than the container's
`pindb` user (UID 10001):

```bash
sudo chown -R 10001:10001 ./images ./logs
docker compose --profile blue --profile green restart
```

### 4.5 Caddy is `unhealthy`

Caddy's healthcheck pings its own `/healthz`. If both upstreams are down it
will report unhealthy. Bring an app color up first (`./scripts/start.sh`), then
restart the proxy:

```bash
docker compose restart proxy
```

---

## 5. Uninstall

```bash
sudo systemctl disable --now pindb.service
sudo rm /etc/systemd/system/pindb.service
sudo systemctl daemon-reload

docker compose --profile blue --profile green --profile migrate down -v   # -v drops volumes
docker image prune -a
```

`-v` is destructive — deletes Postgres data, Meilisearch index, and Caddy
state. Back up first.
