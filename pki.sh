#!/usr/bin/env bash
set -euo pipefail

# pki.sh (v2.12) - Root+Intermediate PKI for SPIRE UpstreamAuthority
# - Supports subject stamping: --subject-root / --subject-int
# - Supports upstream intermediate pathlen: --pathlen (default 1)
# - all create generates both root + intermediate, producing chain.pem

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "==> $*"; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

DEFAULT_BASE_DIR="./pki"
if [[ -d "./spire_setup" ]]; then
  DEFAULT_BASE_DIR="./spire_setup/pki"
fi

BASE_DIR="${DEFAULT_BASE_DIR}"
CA_NAME="spire-demo"
ROOT_DAYS=3650
INT_DAYS=1825
# IMPORTANT: SPIRE Server mints its own X509CA (an intermediate) under the upstream intermediate.
# Therefore upstream intermediate must allow one subordinate intermediate: pathlen>=1.
PATHLEN=1

ALGO="rsa" # rsa|ec
RSA_BITS=4096
EC_CURVE="prime256v1"

SUBJECT_ROOT="/C=CA/ST=ON/L=Scarborough/O=Lab/OU=PKI/CN=Lab Root CA"
SUBJECT_INT="/C=CA/ST=ON/L=Scarborough/O=Lab/OU=PKI/CN=SPIRE Upstream Intermediate CA"

FORCE=0
YES=0

usage() {
  cat <<'EOF'
Usage:
  pki.sh root create|delete|show [options]
  pki.sh intermediate create|delete|show [options]
  pki.sh all create|delete|show [options]

Options:
  --base-dir PATH
  --ca-name NAME
  --algo rsa|ec
  --rsa-bits N
  --ec-curve NAME
  --days N
  --pathlen N            (intermediate basicConstraints pathlen; default: 1)
  --subject "DN"          (legacy; applies to the current realm)
  --subject-root "DN"     (applies to root even with all:create)
  --subject-int "DN"      (applies to intermediate even with all:create)
  --force
  --yes
EOF
}

REALM="${1:-}"; ACTION="${2:-}"
shift $(( $#>0 ? 1 : 0 )) || true
shift $(( $#>0 ? 1 : 0 )) || true

DAYS_OVERRIDE=""
SUBJECT_OVERRIDE=""
SUBJECT_ROOT_OVERRIDE=""
SUBJECT_INT_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-dir) BASE_DIR="${2:-}"; shift 2;;
    --ca-name) CA_NAME="${2:-}"; shift 2;;
    --algo) ALGO="${2:-}"; shift 2;;
    --rsa-bits) RSA_BITS="${2:-}"; shift 2;;
    --ec-curve) EC_CURVE="${2:-}"; shift 2;;
    --days) DAYS_OVERRIDE="${2:-}"; shift 2;;
    --pathlen) PATHLEN="${2:-}"; shift 2;;
    --subject) SUBJECT_OVERRIDE="${2:-}"; shift 2;;
    --subject-root) SUBJECT_ROOT_OVERRIDE="${2:-}"; shift 2;;
    --subject-int) SUBJECT_INT_OVERRIDE="${2:-}"; shift 2;;
    --force) FORCE=1; shift;;
    --yes) YES=1; shift;;
    -h|--help) usage; exit 0;;
    *) die "Unknown option: $1 (use --help)";;
  esac
done

need_cmd openssl
need_cmd mkdir
need_cmd chmod
need_cmd rm
need_cmd cat

[[ -n "${REALM}" && -n "${ACTION}" ]] || { usage; exit 1; }
[[ "${ALGO}" == "rsa" || "${ALGO}" == "ec" ]] || die "--algo must be rsa or ec"
[[ "${PATHLEN}" =~ ^[0-9]+$ ]] || die "--pathlen must be an integer >= 0"

ROOT_DIR="${BASE_DIR}/root-${CA_NAME}"
INT_DIR="${BASE_DIR}/intermediate-${CA_NAME}"

root_days="${ROOT_DAYS}"
int_days="${INT_DAYS}"
subject_root="${SUBJECT_ROOT}"
subject_int="${SUBJECT_INT}"

if [[ "${REALM}" == "root" ]]; then
  [[ -n "${DAYS_OVERRIDE}" ]] && root_days="${DAYS_OVERRIDE}"
  [[ -n "${SUBJECT_OVERRIDE}" ]] && subject_root="${SUBJECT_OVERRIDE}"
elif [[ "${REALM}" == "intermediate" ]]; then
  [[ -n "${DAYS_OVERRIDE}" ]] && int_days="${DAYS_OVERRIDE}"
  [[ -n "${SUBJECT_OVERRIDE}" ]] && subject_int="${SUBJECT_OVERRIDE}"
fi

[[ -n "${SUBJECT_ROOT_OVERRIDE}" ]] && subject_root="${SUBJECT_ROOT_OVERRIDE}"
[[ -n "${SUBJECT_INT_OVERRIDE}" ]] && subject_int="${SUBJECT_INT_OVERRIDE}"


gen_key() {
  local out="$1"
  if [[ "${ALGO}" == "rsa" ]]; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:"${RSA_BITS}" -out "${out}"
  else
    openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:"${EC_CURVE}" -out "${out}"
  fi
  chmod 600 "${out}"
}

init_ca_dir() {
  local dir="$1"
  mkdir -p "${dir}"/{certs,crl,newcerts,private,csr}
  chmod 700 "${dir}/private"
  : > "${dir}/index.txt"
  [[ -f "${dir}/serial" ]] || echo 1000 > "${dir}/serial"
  [[ -f "${dir}/crlnumber" ]] || echo 1000 > "${dir}/crlnumber"
}

write_root_openssl_conf() {
  local conf="$1"
  cat > "${conf}" <<EOF
[ ca ]
default_ca = CA_default

[ CA_default ]
dir = ${ROOT_DIR}
certs = \$dir/certs
crl_dir = \$dir/crl
new_certs_dir = \$dir/newcerts
database = \$dir/index.txt
serial = \$dir/serial
crlnumber = \$dir/crlnumber
private_key = \$dir/private/ca.key.pem
certificate = \$dir/certs/ca.cert.pem
default_md = sha256
policy = policy_strict

[ policy_strict ]
countryName = supplied
stateOrProvinceName = supplied
localityName = optional
organizationName = supplied
organizationalUnitName = optional
commonName = supplied
emailAddress = optional

[ req ]
distinguished_name = req_distinguished_name
string_mask = utf8only
default_md = sha256
x509_extensions = v3_ca
prompt = no

[ req_distinguished_name ]

[ v3_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true
keyUsage = critical, keyCertSign, cRLSign

[ v3_intermediate_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:${PATHLEN}
keyUsage = critical, keyCertSign, cRLSign
EOF
}

confirm_delete() {
  local target="$1"
  if [[ "${YES}" -eq 1 ]]; then return 0; fi
  read -r -p "Really delete '${target}'? Type 'delete' to proceed: " ans
  [[ "${ans}" == "delete" ]] || die "Aborted."
}

root_create() {
  if [[ -d "${ROOT_DIR}" ]]; then
    if [[ "${FORCE}" -eq 1 ]]; then
      log "Removing existing Root CA dir (force): ${ROOT_DIR}"
      rm -rf "${ROOT_DIR}"
    else
      die "Root CA already exists at ${ROOT_DIR}. Use --force to overwrite."
    fi
  fi

  log "Creating Root CA at: ${ROOT_DIR}"
  init_ca_dir "${ROOT_DIR}"

  local conf="${ROOT_DIR}/openssl.cnf"
  write_root_openssl_conf "${conf}"

  local key="${ROOT_DIR}/private/ca.key.pem"
  local cert="${ROOT_DIR}/certs/ca.cert.pem"

  log "Generating Root CA private key (${ALGO})..."
  gen_key "${key}"

  log "Generating self-signed Root CA certificate (days=${root_days})..."
  openssl req -config "${conf}" -key "${key}" \
    -new -x509 -days "${root_days}" -sha256 -extensions v3_ca \
    -subj "${subject_root}" -out "${cert}"

  chmod 644 "${cert}"
  log "Root CA created:"
  echo " Root key : ${key}"
  echo " Root cert: ${cert}"
}

intermediate_create() {
  [[ -d "${ROOT_DIR}" ]] || die "Root CA must exist first at: ${ROOT_DIR}"
  local root_cert="${ROOT_DIR}/certs/ca.cert.pem"
  [[ -f "${root_cert}" ]] || die "Root cert missing: ${root_cert}"

  if [[ -d "${INT_DIR}" ]]; then
    if [[ "${FORCE}" -eq 1 ]]; then
      log "Removing existing Intermediate CA dir (force): ${INT_DIR}"
      rm -rf "${INT_DIR}"
    else
      die "Intermediate CA already exists at ${INT_DIR}. Use --force to overwrite."
    fi
  fi

  log "Creating Intermediate CA at: ${INT_DIR}"
  init_ca_dir "${INT_DIR}"

  local key="${INT_DIR}/private/intermediate.key.pem"
  local csr="${INT_DIR}/csr/intermediate.csr.pem"
  local cert="${INT_DIR}/certs/intermediate.cert.pem"
  local chain="${INT_DIR}/certs/chain.pem"

  log "Generating Intermediate CA private key (${ALGO})..."
  gen_key "${key}"

  log "Generating Intermediate CSR..."
  openssl req -new -sha256 -key "${key}" -subj "${subject_int}" -out "${csr}"

  log "Signing Intermediate certificate with Root CA (non-interactive -batch)..."
  openssl ca -batch -config "${ROOT_DIR}/openssl.cnf" \
    -extensions v3_intermediate_ca \
    -days "${int_days}" -notext -md sha256 \
    -in "${csr}" -out "${cert}"

  chmod 644 "${cert}"

  log "Creating chain.pem (Intermediate + Root)..."
  cat "${cert}" "${root_cert}" > "${chain}"
  chmod 644 "${chain}"

  log "Intermediate CA created:"
  echo " Intermediate key : ${key}"
  echo " Intermediate cert: ${cert}"
  echo " Chain (int+root) : ${chain}"
}

root_delete() { [[ -d "${ROOT_DIR}" ]] || die "Root CA dir not found: ${ROOT_DIR}"; confirm_delete "${ROOT_DIR}"; rm -rf "${ROOT_DIR}"; log "Deleted Root CA: ${ROOT_DIR}"; }
intermediate_delete() { [[ -d "${INT_DIR}" ]] || die "Intermediate CA dir not found: ${INT_DIR}"; confirm_delete "${INT_DIR}"; rm -rf "${INT_DIR}"; log "Deleted Intermediate CA: ${INT_DIR}"; }

root_show() { [[ -f "${ROOT_DIR}/certs/ca.cert.pem" ]] || die "Root cert not found"; openssl x509 -in "${ROOT_DIR}/certs/ca.cert.pem" -noout -subject -issuer -dates -serial; }
intermediate_show() { [[ -f "${INT_DIR}/certs/intermediate.cert.pem" ]] || die "Intermediate cert not found"; openssl x509 -in "${INT_DIR}/certs/intermediate.cert.pem" -noout -subject -issuer -dates -serial; }

all_create() { root_create; intermediate_create; }
all_delete() { [[ -d "${INT_DIR}" ]] && intermediate_delete || true; [[ -d "${ROOT_DIR}" ]] && root_delete || true; }
all_show() { [[ -d "${ROOT_DIR}" ]] && root_show || true; [[ -d "${INT_DIR}" ]] && intermediate_show || true; }

case "${REALM}:${ACTION}" in
  root:create) root_create ;;
  root:delete) root_delete ;;
  root:show) root_show ;;
  intermediate:create) intermediate_create ;;
  intermediate:delete) intermediate_delete ;;
  intermediate:show) intermediate_show ;;
  all:create) all_create ;;
  all:delete) all_delete ;;
  all:show) all_show ;;
  *) usage; die "Unknown command: ${REALM} ${ACTION}" ;;
esac
