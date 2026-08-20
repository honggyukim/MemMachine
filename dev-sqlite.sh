#!/usr/bin/env bash

# MemMachine SQLite Development Server
# Runs MemMachine with no containers at all, using the SQLite sample config.
# Everything lives under a single work directory that can be deleted at will.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLE="$REPO_DIR/sample_configs/episodic_memory_config.sqlite.sample"

WORK_DIR="${MEMMACHINE_DEV_DIR:-$REPO_DIR/.dev-sqlite}"
CONFIG="$WORK_DIR/configuration.yml"
PIDFILE="$WORK_DIR/server.pid"
LOGFILE="$WORK_DIR/server.log"
NLTK_STAMP="$WORK_DIR/.nltk-done"

HOST="${MEMMACHINE_DEV_HOST:-127.0.0.1}"
PORT="${MEMMACHINE_DEV_PORT:-8080}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
BASE_URL="http://$HOST:$PORT/api/v2"

# env -u VIRTUAL_ENV keeps uv from warning when an unrelated virtualenv is
# active in the caller's shell; uv would ignore it anyway.
RUN=(env -u VIRTUAL_ENV uv run --project "$REPO_DIR" --frozen --all-extras)

show_help() {
    cat <<EOF
MemMachine SQLite Development Server

Runs MemMachine against SQLite files only. No Docker, no Neo4j, no Postgres.
A language model and an embedder still have to be reachable; the sample config
points at a local Ollama.

Usage: ./dev-sqlite.sh [COMMAND]

Commands:
  start     Start the server in the background (default)
  run       Start the server in the foreground
  stop      Stop the server
  restart   Restart the server. Clears short-term memory, see 'smoke'
  status    Show whether the server is running
  logs      Follow the server log
  smoke     Run an end-to-end store-and-search check (tools/dev_smoke.py).
            Takes an optional mode: 'rest' calls the v2 API over plain HTTP
            (default), 'client' does the same through the memmachine-client
            library, and 'embedded' drives MemMachine in-process with no
            server at all. Set SHOW_CURL=1 to print the equivalent curl
            commands
  reset     Delete the work directory and start over
  help      Show this message

Environment:
  MEMMACHINE_DEV_DIR    Work directory (default: <repo>/.dev-sqlite)
  MEMMACHINE_DEV_HOST   Bind address (default: 127.0.0.1)
  MEMMACHINE_DEV_PORT   Port (default: 8080)
  OLLAMA_BASE_URL       Ollama endpoint to check (default: http://localhost:11434)

Examples:
  ./dev-sqlite.sh start
  ./dev-sqlite.sh smoke
  ./dev-sqlite.sh smoke client
  ./dev-sqlite.sh smoke embedded
  SHOW_CURL=1 ./dev-sqlite.sh smoke
  ./dev-sqlite.sh reset
EOF
}

check_prerequisites() {
    if ! command -v uv >/dev/null 2>&1; then
        print_error "uv is not installed. See https://docs.astral.sh/uv/"
        exit 1
    fi
    if [ ! -f "$SAMPLE" ]; then
        print_error "Sample config not found at $SAMPLE"
        exit 1
    fi
    if ! curl -sf -m 3 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
        print_warning "Ollama is not responding at $OLLAMA_URL"
        print_warning "Start it with 'ollama serve', or edit $CONFIG to use another provider."
    fi
}

prepare_work_dir() {
    mkdir -p "$WORK_DIR"
    if [ ! -f "$CONFIG" ]; then
        cp "$SAMPLE" "$CONFIG"
        print_success "Created $CONFIG from the SQLite sample"
    fi
    # The bm25 reranker needs NLTK stopwords, which the Docker image bakes in
    # but a local environment does not have.
    if [ ! -f "$NLTK_STAMP" ]; then
        print_info "Downloading NLTK data (first run only)..."
        "${RUN[@]}" memmachine-nltk-setup >/dev/null 2>&1
        touch "$NLTK_STAMP"
        print_success "NLTK data ready"
    fi
}

server_pid() {
    [ -f "$PIDFILE" ] || return 1
    local pid
    pid=$(cat "$PIDFILE")
    kill -0 "$pid" 2>/dev/null || return 1
    echo "$pid"
}

# Whether anything is answering on the port. This is the authority on "is the
# server up": the recorded pid can be gone while the server it started is not.
port_in_use() {
    curl -sf -m 2 "$BASE_URL/health" >/dev/null 2>&1
}

wait_until_healthy() {
    local count=0
    until curl -sf -m 2 "$BASE_URL/health" >/dev/null 2>&1; do
        count=$((count + 1))
        if [ $count -ge 60 ]; then
            print_error "Server did not become healthy within 60 seconds"
            print_error "Last 20 log lines:"
            tail -20 "$LOGFILE" >&2
            return 1
        fi
        sleep 1
    done
    print_success "Server is healthy after ${count}s: $BASE_URL/health"
}

start_server() {
    if server_pid >/dev/null; then
        print_warning "Server is already running (pid $(server_pid)) on port $PORT"
        return 0
    fi
    if port_in_use; then
        print_error "Something already answers $BASE_URL/health but is not in $PIDFILE."
        print_error "Stop it by hand, or pick a free port with MEMMACHINE_DEV_PORT."
        exit 1
    fi
    check_prerequisites
    prepare_work_dir
    print_info "Starting MemMachine on $HOST:$PORT ..."
    (
        cd "$WORK_DIR"
        MEMORY_CONFIG="$CONFIG" HOST="$HOST" PORT="$PORT" \
            "${RUN[@]}" memmachine-server >"$LOGFILE" 2>&1 &
        echo $! >"$PIDFILE"
    )
    wait_until_healthy
    echo
    echo "  API docs:  http://$HOST:$PORT/docs"
    echo "  Work dir:  $WORK_DIR"
    echo "  Log:       $LOGFILE"
    echo
    echo "  Try it:    ./dev-sqlite.sh smoke"
}

run_server() {
    check_prerequisites
    prepare_work_dir
    print_info "Starting MemMachine on $HOST:$PORT (Ctrl-C to stop) ..."
    cd "$WORK_DIR"
    MEMORY_CONFIG="$CONFIG" HOST="$HOST" PORT="$PORT" \
        exec "${RUN[@]}" memmachine-server
}

stop_server() {
    local pid
    if ! pid=$(server_pid); then
        if port_in_use; then
            print_error "Nothing tracked in $PIDFILE, but $BASE_URL/health still answers."
            print_error "An untracked server is holding port $PORT; stop it by hand."
            rm -f "$PIDFILE"
            return 1
        fi
        print_warning "Server is not running"
        rm -f "$PIDFILE"
        return 0
    fi

    # `uv run` runs the server as a child, so the recorded pid is the wrapper.
    # Collect the children before signalling anything: once the wrapper exits
    # they are reparented and can no longer be found from it, and an orphan
    # keeps holding the port and the SQLite files.
    local children
    children=$(pgrep -P "$pid" 2>/dev/null || true)

    # shellcheck disable=SC2086 # children is a list of pids
    kill -TERM $children "$pid" 2>/dev/null || true

    local count=0
    while port_in_use && [ $count -lt 15 ]; do
        sleep 1
        count=$((count + 1))
    done

    # shellcheck disable=SC2086 # children is a list of pids
    kill -KILL $children "$pid" 2>/dev/null || true
    rm -f "$PIDFILE"

    if port_in_use; then
        print_error "Port $PORT is still being served after stopping pid $pid"
        return 1
    fi
    print_success "Server stopped"
}

show_status() {
    local pid
    if pid=$(server_pid); then
        print_success "Running (pid $pid) on http://$HOST:$PORT"
    else
        print_info "Not running"
    fi
    if [ -d "$WORK_DIR" ]; then
        echo "  Work dir: $WORK_DIR"
        for f in "$WORK_DIR"/*.db; do
            [ -e "$f" ] && echo "    $(basename "$f")  $(du -h "$f" | cut -f1)"
        done
    fi
}

reset_all() {
    stop_server
    if [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
        print_success "Removed $WORK_DIR"
    fi
}

SMOKE_SCRIPT="$REPO_DIR/tools/dev_smoke.py"

# End-to-end check: create a project, store episodes, then search.
#
# The search is run twice because episodes that are still in short-term memory
# are removed from the long-term results as duplicates. Restarting the server
# clears short-term memory (it is in-process only) and leaves the SQLite files
# untouched, which is what makes the long-term vector search observable.
#
# The steps themselves live in tools/dev_smoke.py; this only sequences them
# around the restart, which is the part that needs the server lifecycle.
smoke_test() {
    local mode="${1:-rest}"
    case "$mode" in
        rest|client|embedded) ;;
        *) print_error "Unknown smoke mode: $mode (expected 'rest', 'client' or 'embedded')"; exit 1 ;;
    esac

    local smoke=("$SMOKE_SCRIPT" --mode "$mode"
                 --org smoke --project "smoke_$$" --user smoke_user)

    if [ "$mode" = embedded ]; then
        # No server involved, but the databases are the same files, so a
        # running server would be writing to them at the same time.
        if server_pid >/dev/null || port_in_use; then
            print_error "Stop the server first: embedded mode opens the same SQLite files."
            exit 1
        fi
        check_prerequisites
        prepare_work_dir
        smoke+=(--config "$CONFIG")
        print_info "Running the embedded smoke test against $CONFIG"
    else
        server_pid >/dev/null || {
            print_error "Server is not running. Run './dev-sqlite.sh start' first."
            exit 1
        }
        smoke+=(--base-url "http://$HOST:$PORT")
        [ -n "${SHOW_CURL:-}" ] && smoke+=(--show-curl)
        print_info "Running the $mode smoke test against http://$HOST:$PORT"
    fi

    print_info "Storing episodes and searching short-term memory ..."
    "${RUN[@]}" python "${smoke[@]}" ingest

    if [ "$mode" = embedded ]; then
        # Short-term memory lives in the process, so the next invocation
        # starts with an empty one. Nothing to restart.
        print_info "Searching long-term memory in a fresh process ..."
    else
        print_info "Restarting to clear short-term memory ..."
        stop_server >/dev/null
        start_server >/dev/null
        print_info "Searching long-term memory ..."
    fi

    "${RUN[@]}" python "${smoke[@]}" search

    print_success "Smoke test passed ($mode mode)"
}

case "${1:-start}" in
    start)   start_server ;;
    run)     run_server ;;
    stop)    stop_server ;;
    restart) stop_server; start_server ;;
    status)  show_status ;;
    logs)    tail -f "$LOGFILE" ;;
    smoke)   smoke_test "${2:-rest}" ;;
    reset)   reset_all ;;
    help|-h|--help) show_help ;;
    *)       print_error "Unknown command: $1"; echo; show_help; exit 1 ;;
esac
