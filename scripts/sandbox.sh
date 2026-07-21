#!/usr/bin/env bash
# Dalgo dev sandbox: worktree + branch off main + dedicated Postgres DB + own
# redis + backend/frontend on unique ports. Spec: features/dev-sandbox/spec.md
#
#   sandbox.sh create <name> [--with-chat]
#   sandbox.sh list
#   sandbox.sh destroy <name> [--delete-branch]
#
# Naming is the registry: dir .dalgo-worktrees/<name>/, branch feature/<name>,
# DB dalgo_sbx_<name>, pm2 apps *-sbx-<name>. sandbox.json records the ports.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DALGO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_MAIN="$DALGO_ROOT/DDP_backend"
FRONTEND_MAIN="$DALGO_ROOT/webapp_v2"
WT_ROOT="$DALGO_ROOT/.dalgo-worktrees"

BACKEND_PORT_BASE=8003
FRONTEND_PORT_BASE=3002
REDIS_PORT_BASE=6380

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

# ── helpers ──────────────────────────────────────────────────────────────────

require_tools() {
  local t
  for t in git uv npm psql redis-server pm2 lsof curl openssl python3; do
    command -v "$t" >/dev/null || die "required tool not found: $t"
  done
}

# replace KEY=... in an env file, or append if absent (never prints values)
set_env() {
  local file=$1 key=$2 value=$3
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" >>"$file"
  fi
}

get_env() { # file key -> value (strips quotes); empty if absent
  grep -E "^$2=" "$1" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true
}

port_free() {
  ! lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1 || return 1
  # also skip ports claimed by other sandboxes whose stack is currently stopped
  ! grep -rhs "\"$1\"" "$WT_ROOT"/*/sandbox.json >/dev/null 2>&1
}

next_free_port() {
  local p=$1
  while ! port_free "$p"; do p=$((p + 1)); done
  echo "$p"
}

# psql against the admin 'postgres' DB using creds from an env file
admin_psql() {
  local envfile=$1; shift
  local host port user pass
  host=$(get_env "$envfile" DBHOST); port=$(get_env "$envfile" DBPORT)
  user=$(get_env "$envfile" DBUSER); pass=$(get_env "$envfile" DBPASSWORD)
  PGPASSWORD="$pass" psql -h "${host:-localhost}" -p "${port:-5432}" \
    -U "${user:-postgres}" -d postgres -v ON_ERROR_STOP=1 "$@"
}

sandbox_paths() { # sets globals from name
  NAME=$1
  SBX_DIR="$WT_ROOT/$NAME"
  BACKEND_WT="$SBX_DIR/DDP_backend"
  FRONTEND_WT="$SBX_DIR/webapp_v2"
  BRANCH="feature/$NAME"
  DB="dalgo_sbx_$(echo "$NAME" | tr '-' '_')"
  APPS=("redis-sbx-$NAME" "django-asgi-sbx-$NAME" "celery-sbx-$NAME" "webapp-sbx-$NAME")
}

# ── create ───────────────────────────────────────────────────────────────────

cmd_create() {
  local with_chat=0
  local name="${1:-}"; shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --with-chat) with_chat=1 ;;
      *) die "unknown flag: $1" ;;
    esac
    shift
  done
  [ -n "$name" ] || die "usage: sandbox.sh create <name> [--with-chat]"
  echo "$name" | grep -Eq '^[a-z][a-z0-9-]{1,30}$' ||
    die "name must be kebab-case: lowercase letters, digits, hyphens (e.g. chart-filters)"
  sandbox_paths "$name"

  require_tools
  [ -f "$BACKEND_MAIN/.env" ] || die "main backend .env not found at $BACKEND_MAIN/.env"
  [ -d "$SBX_DIR" ] && die "sandbox dir already exists: $SBX_DIR (destroy it or pick another name)"
  local repo
  for repo in "$BACKEND_MAIN" "$FRONTEND_MAIN"; do
    git -C "$repo" show-ref --verify --quiet "refs/heads/$BRANCH" &&
      die "branch $BRANCH already exists in $(basename "$repo")"
  done
  local db_exists
  db_exists=$(admin_psql "$BACKEND_MAIN/.env" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$DB'")
  [ "$db_exists" = "1" ] && die "database $DB already exists (destroy the old sandbox first)"

  info "assigning ports"
  BP=$(next_free_port "$BACKEND_PORT_BASE")
  FP=$(next_free_port "$FRONTEND_PORT_BASE")
  RP=$(next_free_port "$REDIS_PORT_BASE")
  info "backend :$BP  frontend :$FP  redis :$RP"

  info "creating worktrees on $BRANCH (off origin/main)"
  mkdir -p "$SBX_DIR"
  if ! git -C "$BACKEND_MAIN" fetch --quiet origin main ||
     ! git -C "$FRONTEND_MAIN" fetch --quiet origin main; then
    echo "    (fetch failed — offline? branching from the last-fetched origin/main)"
  fi
  git -C "$BACKEND_MAIN" worktree add --quiet -b "$BRANCH" "$BACKEND_WT" origin/main
  git -C "$FRONTEND_MAIN" worktree add --quiet -b "$BRANCH" "$FRONTEND_WT" origin/main

  info "generating env files (copied from main checkouts, sandbox values patched)"
  cp "$BACKEND_MAIN/.env" "$BACKEND_WT/.env"
  [ -f "$BACKEND_MAIN/.env.test" ] && cp "$BACKEND_MAIN/.env.test" "$BACKEND_WT/.env.test"
  set_env "$BACKEND_WT/.env" DBNAME "$DB"
  set_env "$BACKEND_WT/.env" REDIS_PORT "$RP"
  set_env "$BACKEND_WT/.env" FRONTEND_URL "http://localhost:$FP"
  set_env "$BACKEND_WT/.env" FRONTEND_URL_V2 "http://localhost:$FP"
  local cors
  cors=$(get_env "$BACKEND_WT/.env" CORS_ALLOWED_ORIGINS)
  [ -z "$cors" ] && cors="http://localhost:3000,http://localhost:3001"
  case "$cors" in
    *"localhost:$FP"*) ;;
    *) cors="$cors,http://localhost:$FP" ;;
  esac
  set_env "$BACKEND_WT/.env" CORS_ALLOWED_ORIGINS "$cors"
  if [ -f "$BACKEND_WT/.env.test" ]; then
    set_env "$BACKEND_WT/.env.test" DBNAME "$DB"
    set_env "$BACKEND_WT/.env.test" REDIS_PORT "$RP"
  fi
  [ -f "$FRONTEND_MAIN/.env" ] && cp "$FRONTEND_MAIN/.env" "$FRONTEND_WT/.env"
  [ -f "$FRONTEND_MAIN/.env.local" ] && cp "$FRONTEND_MAIN/.env.local" "$FRONTEND_WT/.env.local"
  touch "$FRONTEND_WT/.env.local"
  set_env "$FRONTEND_WT/.env.local" NEXT_PUBLIC_BACKEND_URL "http://localhost:$BP"

  info "installing backend deps (uv sync --frozen, own .venv)"
  (cd "$BACKEND_WT" && uv sync --frozen --quiet)

  info "installing frontend deps (npm ci — the slow part)"
  (cd "$FRONTEND_WT" && npm ci --no-audit --no-fund --loglevel=error)

  info "creating database $DB + migrations + seed fixtures"
  admin_psql "$BACKEND_WT/.env" -qc "CREATE DATABASE $DB"
  (cd "$BACKEND_WT" &&
    .venv/bin/python manage.py migrate --no-input &&
    .venv/bin/python manage.py loaddata 001_roles.json 002_permissions.json \
      003_role_permissions.json tasks.json)

  local email="admin@sbx-$NAME.local" password
  password=$(openssl rand -hex 8)
  info "creating org sbx-$NAME and admin user $email"
  # NOT createorganduser: that calls create_organization, which requires a live
  # Airbyte connection to create a workspace (and deletes the org when it can't).
  # A sandbox has no Airbyte — create the org/plan/user/orguser rows directly.
  (cd "$BACKEND_WT" && SBX_ORG="sbx-$NAME" SBX_EMAIL="$email" SBX_PASSWORD="$password" \
    .venv/bin/python manage.py shell -c '
import os
from django.contrib.auth.models import User
from django.utils.text import slugify
from ddpui.models.org import Org
from ddpui.models.org_plans import OrgPlans, OrgPlanType
from ddpui.models.org_user import OrgUser, UserAttributes
from ddpui.models.role_based_access import Role

name, email = os.environ["SBX_ORG"], os.environ["SBX_EMAIL"]
org = Org.objects.filter(name__iexact=name).first()
if org is None:
    org = Org(name=name)
    org.slug = slugify(name)[:20]
    org.save()
    print(f"Org {name} created (slug {org.slug}; no airbyte workspace — sandbox)")
if not OrgPlans.objects.filter(org=org).exists():
    OrgPlans.objects.create(
        org=org, base_plan=OrgPlanType.INTERNAL.value, can_upgrade_plan=True,
        superset_included=False, subscription_duration="Monthly", features={},
    )
user = User.objects.filter(email=email).first()
if user is None:
    user = User.objects.create_user(
        email=email, username=email, password=os.environ["SBX_PASSWORD"]
    )
    print(f"User {email} created")
role = Role.objects.get(slug="admin")
OrgUser.objects.get_or_create(
    org=org, user=user, defaults={"new_role": role, "email_verified": True}
)
ua, _ = UserAttributes.objects.get_or_create(user=user)
ua.email_verified = True
ua.can_create_orgs = True
ua.save()
print("sandbox org/user ready")
')

  if [ "$with_chat" = 1 ]; then
    info "chat-with-data: creating checkpointer tables"
    (cd "$BACKEND_WT" && .venv/bin/python manage.py chat_with_data_setup)
  fi

  info "writing pm2 config + sandbox.json"
  local redis_bin next_bin
  redis_bin=$(command -v redis-server)
  next_bin="$FRONTEND_WT/node_modules/.bin/next"
  cat >"$SBX_DIR/ecosystem.config.js" <<EOF
// Generated by sandbox.sh for sandbox '$NAME' — do not hand-edit ports here;
// they must match the worktree .env files and sandbox.json.
module.exports = {
  apps: [
    {
      name: 'redis-sbx-$NAME',
      script: '$redis_bin --port $RP --save "" --appendonly no',
      max_restarts: 5,
      watch: false,
    },
    {
      name: 'django-asgi-sbx-$NAME',
      cwd: '$BACKEND_WT',
      script: '$BACKEND_WT/.venv/bin/uvicorn ddpui.asgi:application --workers 1 --host 0.0.0.0 --port $BP --timeout-keep-alive 60',
      max_restarts: 5,
      watch: false,
    },
    {
      name: 'celery-sbx-$NAME',
      cwd: '$BACKEND_WT',
      script: '$BACKEND_WT/.venv/bin/celery -A ddpui worker -Q default -n sbx-$NAME -P solo --concurrency=1 --without-mingle --without-gossip',
      max_restarts: 5,
      watch: false,
    },
    {
      name: 'webapp-sbx-$NAME',
      cwd: '$FRONTEND_WT',
      script: '$next_bin dev --turbopack -p $FP',
      max_restarts: 5,
      watch: false, // next dev has its own HMR; pm2 watch would double-restart
    },
  ],
};
EOF
  cat >"$SBX_DIR/sandbox.json" <<EOF
{
  "name": "$NAME",
  "branch": "$BRANCH",
  "db": "$DB",
  "ports": { "backend": "$BP", "frontend": "$FP", "redis": "$RP" },
  "org": "sbx-$NAME",
  "email": "$email",
  "password": "$password",
  "created": "$(date +%Y-%m-%dT%H:%M:%S)"
}
EOF

  info "starting pm2 apps"
  pm2 start "$SBX_DIR/ecosystem.config.js"

  info "waiting for backend on :$BP"
  local i code=000
  for i in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$BP/api/currentuserv2" || true)
    [ "$code" != "000" ] && break
    sleep 1
  done
  [ "$code" = "000" ] && die "backend did not come up on :$BP — check: pm2 logs django-asgi-sbx-$NAME"

  echo
  echo "───────────────────────────────────────────────────────────────"
  echo " Sandbox '$NAME' is ready"
  echo "   frontend   http://localhost:$FP"
  echo "   backend    http://localhost:$BP"
  echo "   branch     $BRANCH   (both repos, off origin/main)"
  echo "   worktrees  $SBX_DIR/{DDP_backend,webapp_v2}"
  echo "   database   $DB    redis :$RP"
  echo "   login      $email  /  $password"
  if [ "$with_chat" = 1 ]; then
    echo
    echo " chat-with-data manual steps remaining:"
    echo "   1. connect a warehouse via the UI (org sbx-$NAME)"
    echo "   2. load seed/warehouse/test_ngo_seed.sql into that warehouse DB"
    echo "   3. enable the CHAT_WITH_DATA feature flag + llm_optin for the org"
  fi
  echo
  echo " tear down:  scripts/sandbox.sh destroy $NAME"
  echo "───────────────────────────────────────────────────────────────"
}

# ── destroy ──────────────────────────────────────────────────────────────────

cmd_destroy() {
  local delete_branch=0
  local name="${1:-}"; shift || true
  while [ $# -gt 0 ]; do
    case "$1" in
      --delete-branch) delete_branch=1 ;;
      *) die "unknown flag: $1" ;;
    esac
    shift
  done
  [ -n "$name" ] || die "usage: sandbox.sh destroy <name> [--delete-branch]"
  sandbox_paths "$name"

  info "stopping pm2 apps"
  local app
  for app in "${APPS[@]}"; do
    pm2 delete "$app" >/dev/null 2>&1 && echo "    stopped $app" || true
  done

  info "dropping databases $DB (+ test twin)"
  admin_psql "$BACKEND_MAIN/.env" -qc "DROP DATABASE IF EXISTS $DB WITH (FORCE)" || true
  admin_psql "$BACKEND_MAIN/.env" -qc "DROP DATABASE IF EXISTS test_$DB WITH (FORCE)" || true

  info "removing worktrees"
  git -C "$BACKEND_MAIN" worktree remove --force "$BACKEND_WT" 2>/dev/null || true
  git -C "$FRONTEND_MAIN" worktree remove --force "$FRONTEND_WT" 2>/dev/null || true
  git -C "$BACKEND_MAIN" worktree prune
  git -C "$FRONTEND_MAIN" worktree prune
  rm -rf "$SBX_DIR"

  if [ "$delete_branch" = 1 ]; then
    info "deleting branch $BRANCH in both repos"
    git -C "$BACKEND_MAIN" branch -D "$BRANCH" 2>/dev/null || true
    git -C "$FRONTEND_MAIN" branch -D "$BRANCH" 2>/dev/null || true
  else
    echo "    branch $BRANCH kept in both repos (pass --delete-branch to remove)"
  fi
  info "sandbox '$name' destroyed"
}

# ── list ─────────────────────────────────────────────────────────────────────

cmd_list() {
  local found=0 manifest
  printf '%-18s %-9s %-10s %-8s %s\n' NAME BACKEND FRONTEND STATUS DB
  for manifest in "$WT_ROOT"/*/sandbox.json; do
    [ -f "$manifest" ] || continue
    found=1
    python3 - "$manifest" <<'PYEOF'
import json, socket, sys
m = json.load(open(sys.argv[1]))
bp = int(m["ports"]["backend"])
s = socket.socket(); s.settimeout(0.3)
try:
    s.connect(("localhost", bp)); status = "running"
except OSError:
    status = "stopped"
finally:
    s.close()
print(f'{m["name"]:<18} :{bp:<8} :{m["ports"]["frontend"]:<9} {status:<8} {m["db"]}')
PYEOF
  done
  [ "$found" = 1 ] || echo "(no sandboxes — create one with: sandbox.sh create <name>)"
}

# ── main ─────────────────────────────────────────────────────────────────────

case "${1:-}" in
  create) shift; cmd_create "$@" ;;
  destroy) shift; cmd_destroy "$@" ;;
  list) shift; cmd_list ;;
  *)
    echo "usage: sandbox.sh create <name> [--with-chat] | destroy <name> [--delete-branch] | list"
    exit 1
    ;;
esac
