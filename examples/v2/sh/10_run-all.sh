#!/bin/sh
# End-to-end smoke test: runs every script in sequence.
#
# Usage: examples/v2/sh/10_run-all.sh
# Env:   MEMORY_BACKEND_URL (default: http://127.0.0.1:8080)

set -e

BASE_URL="${MEMORY_BACKEND_URL:-http://127.0.0.1:8080}"
export MEMORY_BACKEND_URL="${BASE_URL}"

DIR="$(cd "$(dirname "$0")" && pwd)"
PASS=0
FAIL=0

run() {
    label="$1"; shift
    printf '\n\033[1;34m=== %s ===\033[0m\n' "$label"
    if "$@"; then
        PASS=$((PASS + 1))
    else
        printf '\033[1;31mFAILED: %s\033[0m\n' "$label"
        FAIL=$((FAIL + 1))
    fi
}

# 1. Health
run "01_health-check"    sh "${DIR}/01_health-check.sh"

# 2. Project management
run "02_create-project"  sh "${DIR}/02_create-project.sh"
run "03_get-project"     sh "${DIR}/03_get-project.sh"
run "04_list-projects"   sh "${DIR}/04_list-projects.sh"

# 3. Memory operations
run "05_add-new-memory"  sh "${DIR}/05_add-new-memory.sh"
run "06_search-memory"   sh "${DIR}/06_search-memory.sh"
run "07_delete-memory"   sh "${DIR}/07_delete-memory.sh"

# 4. Cleanup
run "08_delete-project"  sh "${DIR}/08_delete-project.sh"

# Summary
printf '\n\033[1;32mPassed: %d\033[0m  \033[1;31mFailed: %d\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
