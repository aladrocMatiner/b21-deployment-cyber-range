#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/stop-all.sh [--keep-base] [--dry-run]

Stops/removes all CRL event stacks in Docker Swarm found on this host.

What it targets:
  - All stacks whose name starts with "crl-" (events/worlds)
  - Optionally also removes the base "crl" stack (default: removed)

Options:
  --keep-base   Keep the base stack named "crl" (crld/portd)
  --dry-run     Print what would be removed, do not change anything
  -h, --help    Show this help
EOF
}

keep_base=false
dry_run=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep-base) keep_base=true; shift ;;
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found in PATH" >&2
  exit 127
fi

stacks="$(docker stack ls --format '{{.Name}}' || true)"
if [[ -z "${stacks}" ]]; then
  echo "No docker stacks found."
  exit 0
fi

event_stacks="$(printf '%s\n' "${stacks}" | awk '/^crl-/{print $0}')"
base_stack_present="$(printf '%s\n' "${stacks}" | awk '$0=="crl"{print $0}')"

if [[ -z "${event_stacks}" && -z "${base_stack_present}" ]]; then
  echo "No CRL stacks found (expected names: crl, crl-...)."
  exit 0
fi

to_remove=()

# Remove deeper/namespaced stacks first (e.g. crl-<event>-<world>) to avoid dependency surprises.
if [[ -n "${event_stacks}" ]]; then
  while IFS= read -r stack; do
    [[ -z "${stack}" ]] && continue
    to_remove+=("${stack}")
  done < <(printf '%s\n' "${event_stacks}" | awk '{ print length($0), $0 }' | sort -rn | cut -d' ' -f2-)
fi

if [[ "${keep_base}" == "false" && -n "${base_stack_present}" ]]; then
  to_remove+=("crl")
fi

if [[ ${#to_remove[@]} -eq 0 ]]; then
  echo "Nothing to remove."
  exit 0
fi

echo "Stacks to remove:"
printf '  - %s\n' "${to_remove[@]}"

if [[ "${dry_run}" == "true" ]]; then
  exit 0
fi

for stack in "${to_remove[@]}"; do
  echo "Removing stack: ${stack}"
  docker stack rm "${stack}"
done

echo "Done."
