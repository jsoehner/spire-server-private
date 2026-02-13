#!/usr/bin/env bash
set -euo pipefail

# run.sh (v2.12) - SPIRE Demo Runner
# Fixes:
# - Uses local PKI under spire_setup/pki automatically
# - If pki.sh is older, falls back from --subject-root to legacy --subject

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${REPO_DIR}/spire_setup"
COMPOSE_BASE="${BASE_DIR}/docker-compose.yaml"
COMPOSE_AGENT="${BASE_DIR}/docker-compose.agent.yaml"
PROJECT_NAME="spire_setup"

SETUP_SCRIPT="setup_demo.py"
AGENT_SCRIPT="add_agent.py"
PKI_SCRIPT="${REPO_DIR}/pki.sh"

DEBUG=0
RESET=0
NEWROOT=0

for a in "$@"; do
  case "$a" in
    -d|--debug) DEBUG=1 ;;
    -r|--reset) RESET=1 ;;
    --newroot) NEWROOT=1 ;;
  esac
done

banner() {
  echo "=========================================="
  echo "   🚀 Starting SPIRE Demo Runner (v2.12)"
  echo "   ${SETUP_SCRIPT} | ${AGENT_SCRIPT}"
  if [[ "$DEBUG" -eq 1 ]]; then echo "   DEBUG: enabled"; fi
  if [[ "$RESET" -eq 1 ]]; then echo "   RESET: enabled"; fi
  if [[ "$NEWROOT" -eq 1 ]]; then echo "   NEWROOT: enabled"; fi
  echo "=========================================="
}

is_compose_valid() {
  [[ -f "${COMPOSE_BASE}" ]] || return 1
  local first_nonempty
  first_nonempty=$(grep -v -e '^\s*$' "${COMPOSE_BASE}" | head -n 1 || true)
  [[ "$first_nonempty" == "services:" ]] || return 1
  if grep -q -x '\\' "${COMPOSE_BASE}"; then return 1; fi
  return 0
}

ensure_compose_exists() {
  mkdir -p "${BASE_DIR}"
  if [[ ! -f "${COMPOSE_BASE}" ]]; then
    echo "Compose file missing (${COMPOSE_BASE}). Generating configs only..."
    if [[ "$DEBUG" -eq 1 ]]; then
      python3 "${REPO_DIR}/${SETUP_SCRIPT}" --generate-only --debug
    else
      python3 "${REPO_DIR}/${SETUP_SCRIPT}" --generate-only
    fi
  fi
  if ! is_compose_valid; then
    echo "Invalid compose detected; regenerating ${COMPOSE_BASE}"
    rm -f "${COMPOSE_BASE}"
    if [[ "$DEBUG" -eq 1 ]]; then
      python3 "${REPO_DIR}/${SETUP_SCRIPT}" --generate-only --debug
    else
      python3 "${REPO_DIR}/${SETUP_SCRIPT}" --generate-only
    fi
  fi
}

maybe_enable_local_pki() {
  local local_pki_dir="${BASE_DIR}/pki"
  local ca_name="${SPIRE_UPSTREAM_CA_NAME:-spire-demo}"

  local local_root="${local_pki_dir}/root-${ca_name}/certs/ca.cert.pem"
  local local_int="${local_pki_dir}/intermediate-${ca_name}/certs/intermediate.cert.pem"
  local local_key="${local_pki_dir}/intermediate-${ca_name}/private/intermediate.key.pem"

  if [[ -f "$local_root" && -f "$local_int" && -f "$local_key" ]]; then
    if [[ "${SPIRE_USE_UPSTREAM:-0}" != "1" ]]; then
      echo "--- Found local upstream PKI in ${local_pki_dir}; enabling upstream (auto) ---"
      export SPIRE_USE_UPSTREAM=1
    fi

    if [[ -z "${SPIRE_UPSTREAM_PKI_DIR:-}" ]]; then
      export SPIRE_UPSTREAM_PKI_DIR="${local_pki_dir}"
      export SPIRE_UPSTREAM_CA_NAME="${ca_name}"
    else
      local configured_dir="${SPIRE_UPSTREAM_PKI_DIR}"
      local cfg_root="${configured_dir}/root-${ca_name}/certs/ca.cert.pem"
      local cfg_int="${configured_dir}/intermediate-${ca_name}/certs/intermediate.cert.pem"
      local cfg_key="${configured_dir}/intermediate-${ca_name}/private/intermediate.key.pem"
      if [[ "${SPIRE_USE_UPSTREAM:-0}" == "1" && ( ! -f "$cfg_root" || ! -f "$cfg_int" || ! -f "$cfg_key" ) ]]; then
        echo "--- SPIRE_UPSTREAM_PKI_DIR points to missing materials (${configured_dir}); overriding to ${local_pki_dir} ---"
        export SPIRE_UPSTREAM_PKI_DIR="${local_pki_dir}"
        export SPIRE_UPSTREAM_CA_NAME="${ca_name}"
      fi
    fi
  fi
}

reset_stack() {
  ensure_compose_exists
  echo "--- Reset requested: wiping compose volumes ---"
  (cd "${BASE_DIR}" && docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_BASE}" down -v --remove-orphans) || true
  echo "--- Reset complete ---"
}

maybe_newroot() {
  local pki_dir="${BASE_DIR}/pki"
  local ca_name="${SPIRE_UPSTREAM_CA_NAME:-spire-demo}"

  local td="${SPIFFE_TRUST_DOMAIN:-bns-demo.test}"
  local default_root_dn="/C=CA/ST=ON/L=Scarborough/O=Scotiabank/OU=PKI/CN=${td} Root CA"
  local default_int_dn="/C=CA/ST=ON/L=Scarborough/O=Scotiabank/OU=PKI/CN=${td} SPIRE Upstream Intermediate CA"
  local root_dn="${SPIRE_PKI_SUBJECT_ROOT:-${default_root_dn}}"
  local int_dn="${SPIRE_PKI_SUBJECT_INT:-${default_int_dn}}"
  local pathlen="${SPIRE_PKI_PATHLEN:-1}"

  local root_cert="${pki_dir}/root-${ca_name}/certs/ca.cert.pem"
  local int_cert="${pki_dir}/intermediate-${ca_name}/certs/intermediate.cert.pem"
  local int_key="${pki_dir}/intermediate-${ca_name}/private/intermediate.key.pem"

  if [[ "$NEWROOT" -eq 1 || ! -f "$root_cert" || ! -f "$int_cert" || ! -f "$int_key" ]]; then
    echo "--- Generating upstream root+intermediate via pki.sh (force) ---"
    chmod +x "${PKI_SCRIPT}" || true

    if "${PKI_SCRIPT}" --help 2>/dev/null | grep -q -- "--subject-root"; then
      "${PKI_SCRIPT}" all create --base-dir "${pki_dir}" --ca-name "${ca_name}" --force --yes \
        --subject-root "${root_dn}" --subject-int "${int_dn}" --pathlen "${pathlen}"
    else
      echo "(pki.sh does not support --subject-root/--subject-int; using legacy --subject)"
      "${PKI_SCRIPT}" root create --base-dir "${pki_dir}" --ca-name "${ca_name}" --force --yes --subject "${root_dn}"
      "${PKI_SCRIPT}" intermediate create --base-dir "${pki_dir}" --ca-name "${ca_name}" --force --yes --subject "${int_dn}" --pathlen "${pathlen}"
    fi

    echo "--- Upstream PKI ready at: ${pki_dir} ---"
  fi

  export SPIRE_USE_UPSTREAM=1
  export SPIRE_UPSTREAM_PKI_DIR="${pki_dir}"
  export SPIRE_UPSTREAM_CA_NAME="${ca_name}"
}

banner
maybe_enable_local_pki

if [[ "$NEWROOT" -eq 1 ]]; then
  maybe_newroot
fi

if [[ "$RESET" -eq 1 ]]; then
  reset_stack
fi

echo "Step 1: Running Infrastructure Setup (${SETUP_SCRIPT})..."
if [[ "$DEBUG" -eq 1 ]]; then
  python3 "${REPO_DIR}/${SETUP_SCRIPT}" --debug
else
  python3 "${REPO_DIR}/${SETUP_SCRIPT}"
fi

echo "✅ Infrastructure setup complete."

echo "⏳ Waiting 15 seconds for Postgres and SPIRE Server to stabilize..."
sleep 15

echo "Step 2: Registering Agent (${AGENT_SCRIPT})..."
if [[ "$DEBUG" -eq 1 ]]; then
  python3 "${REPO_DIR}/${AGENT_SCRIPT}" --debug
else
  python3 "${REPO_DIR}/${AGENT_SCRIPT}"
fi

echo "✅ Agent registration complete."

if [[ -f "${COMPOSE_AGENT}" ]]; then
  (cd "${BASE_DIR}" && docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_BASE}" -f "${COMPOSE_AGENT}" logs -f --tail=200)
else
  (cd "${BASE_DIR}" && docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_BASE}" logs -f --tail=200)
fi
