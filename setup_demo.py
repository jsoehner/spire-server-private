#!/usr/bin/env python3
"""setup_demo.py (v2.12) - SPIRE demo setup with robust upstream + TTL defaults

Defaults
--------
- ca_ttl = 60m
- default_x509_svid_ttl = 300s

Upstream behavior
-----------------
- Smart default: if local PKI exists under ./spire_setup/pki, auto-enable upstream unless
  SPIRE_AUTO_USE_LOCAL_PKI=0.
- If SPIRE_USE_UPSTREAM=1 and directory-mode path is wrong/missing, we fall back to local PKI
  (unless SPIRE_AUTO_USE_LOCAL_PKI=0).
- Placeholder direct-file vars like /abs/path/* are warn-only unless SPIRE_UPSTREAM_STRICT=1.

"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from string import Template

POSTGRES_IMAGE = "mirror.gcr.io/chainguard/postgres:latest"
SPIRE_SERVER_IMAGE = "ghcr.io/spiffe/spire-server:1.14.1"
NGINX_IMAGE = "mirror.gcr.io/chainguard/nginx:latest"

CA_TTL = "60m"
DEFAULT_X509_SVID_TTL = "300s"
SERVER_LOG_LEVEL = "DEBUG"

NET_NAME = "spire_demo_net"
NET_SUBNET = "172.28.0.0/24"
IP_LB = "172.28.0.10"
IP_S1 = "172.28.0.11"
IP_S2 = "172.28.0.12"
IP_PG = "172.28.0.13"

USE_UPSTREAM = os.environ.get("SPIRE_USE_UPSTREAM", "0") == "1"
UPSTREAM_STRICT = os.environ.get("SPIRE_UPSTREAM_STRICT", "0") == "1"
AUTO_LOCAL_PKI = os.environ.get("SPIRE_AUTO_USE_LOCAL_PKI", "1") != "0"

UPSTREAM_PKI_DIR = os.environ.get("SPIRE_UPSTREAM_PKI_DIR", "").strip()
UPSTREAM_CA_NAME = os.environ.get("SPIRE_UPSTREAM_CA_NAME", "spire-demo").strip()

UP_ROOT_CERT = os.environ.get("SPIRE_UPSTREAM_ROOT_CERT", "").strip()
UP_INT_CERT = os.environ.get("SPIRE_UPSTREAM_INT_CERT", "").strip()
UP_INT_KEY = os.environ.get("SPIRE_UPSTREAM_INT_KEY", "").strip()
UP_CHAIN = os.environ.get("SPIRE_UPSTREAM_CHAIN", "").strip()

TRUST_DOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def log(msg: str) -> None:
    print(msg, flush=True)


def normalize_trust_domain(td: str) -> str:
    td = (td or "").strip().lower().removeprefix("spiffe://")
    if not td:
        raise ValueError("trust_domain is empty")
    if not TRUST_DOMAIN_RE.match(td):
        raise ValueError("trust domain characters are limited to lowercase letters, numbers, dots, dashes, and underscores")
    return td


def _looks_like_placeholder(p: str) -> bool:
    return p.startswith("/abs/path/")


def _warn_or_raise(msg: str, *, details: str = "") -> None:
    if UPSTREAM_STRICT:
        hint = (
            "\n\nRemediation:\n"
            "  - Unset placeholder env vars (SPIRE_UPSTREAM_*CERT/KEY) or set them to real paths\n"
            "  - OR unset SPIRE_USE_UPSTREAM until PKI exists\n"
            "  - OR unset SPIRE_UPSTREAM_STRICT (or set it to 0) to allow warn-and-continue\n"
        )
        raise RuntimeError(msg + ("\n\nDetails:\n" + details if details else "") + hint)

    log("⚠️  " + msg)
    if details:
        for line in details.splitlines():
            log("   " + line)
    log("   Continuing without UpstreamAuthority (set SPIRE_UPSTREAM_STRICT=1 to make this fatal).")


def _path_if_set(p: str) -> Path | None:
    return Path(p).expanduser().resolve() if p else None


def detect_upstream_materials() -> tuple[str, dict[str, Path]] | None:
    global USE_UPSTREAM, UPSTREAM_PKI_DIR

    # Auto-enable local PKI
    if not USE_UPSTREAM and AUTO_LOCAL_PKI:
        local_base = Path(__file__).parent / "spire_setup" / "pki"
        ca_guess = os.environ.get("SPIRE_UPSTREAM_CA_NAME", "spire-demo")
        local_root = local_base / f"root-{ca_guess}" / "certs" / "ca.cert.pem"
        local_int  = local_base / f"intermediate-{ca_guess}" / "certs" / "intermediate.cert.pem"
        local_key  = local_base / f"intermediate-{ca_guess}" / "private" / "intermediate.key.pem"
        if local_root.exists() and local_int.exists() and local_key.exists():
            log(f"ℹ️ Auto-detected local upstream PKI at {local_base}; enabling upstream")
            os.environ["SPIRE_USE_UPSTREAM"] = "1"
            os.environ.setdefault("SPIRE_UPSTREAM_PKI_DIR", str(local_base))
            os.environ.setdefault("SPIRE_UPSTREAM_CA_NAME", ca_guess)
            USE_UPSTREAM = True
            UPSTREAM_PKI_DIR = os.environ.get("SPIRE_UPSTREAM_PKI_DIR", "").strip()

    if not USE_UPSTREAM:
        return None

    # Placeholder direct-file vars
    direct_vals = {
        "SPIRE_UPSTREAM_ROOT_CERT": UP_ROOT_CERT,
        "SPIRE_UPSTREAM_INT_CERT": UP_INT_CERT,
        "SPIRE_UPSTREAM_INT_KEY": UP_INT_KEY,
        "SPIRE_UPSTREAM_CHAIN": UP_CHAIN,
    }
    placeholders = [k for k, v in direct_vals.items() if v and _looks_like_placeholder(v)]
    if placeholders:
        _warn_or_raise(
            "Direct-file upstream paths look like placeholders (/abs/path/...).",
            details="Placeholder vars:\n" + "\n".join(f"- {k}={direct_vals[k]}" for k in placeholders),
        )
        return None

    # Direct-file mode
    if UP_ROOT_CERT or UP_INT_CERT or UP_INT_KEY:
        if UP_ROOT_CERT and UP_INT_CERT and UP_INT_KEY:
            root = _path_if_set(UP_ROOT_CERT)
            icert = _path_if_set(UP_INT_CERT)
            ikey = _path_if_set(UP_INT_KEY)
            chain = _path_if_set(UP_CHAIN)
            missing = [p for p in (root, icert, ikey) if p and not p.exists()]
            if missing:
                _warn_or_raise("Direct-file upstream materials missing.", details="Missing:\n" + "\n".join(f"- {p}" for p in missing))
                return None
            if chain and not chain.exists():
                _warn_or_raise("SPIRE_UPSTREAM_CHAIN provided but not found.", details=f"- {chain}")
                return None
            mats = {"root_cert": root, "int_cert": icert, "int_key": ikey}
            if chain:
                mats["chain"] = chain
            return "direct", mats

        _warn_or_raise("Direct-file upstream mode selected but not all of ROOT_CERT/INT_CERT/INT_KEY are set.")
        return None

    # Directory mode
    if not UPSTREAM_PKI_DIR:
        _warn_or_raise("SPIRE_USE_UPSTREAM=1 but SPIRE_UPSTREAM_PKI_DIR is not set.")
        return None

    base = Path(UPSTREAM_PKI_DIR).expanduser().resolve()
    root_dir = base / f"root-{UPSTREAM_CA_NAME}"
    int_dir = base / f"intermediate-{UPSTREAM_CA_NAME}"

    root_cert = root_dir / "certs" / "ca.cert.pem"
    int_cert = int_dir / "certs" / "intermediate.cert.pem"
    int_key = int_dir / "private" / "intermediate.key.pem"
    chain = int_dir / "certs" / "chain.pem"

    missing = [p for p in (root_cert, int_cert, int_key) if not p.exists()]
    if missing:
        # Fallback to local PKI if present
        if AUTO_LOCAL_PKI:
            local_base = Path(__file__).parent / "spire_setup" / "pki"
            local_root = local_base / f"root-{UPSTREAM_CA_NAME}" / "certs" / "ca.cert.pem"
            local_int  = local_base / f"intermediate-{UPSTREAM_CA_NAME}" / "certs" / "intermediate.cert.pem"
            local_key  = local_base / f"intermediate-{UPSTREAM_CA_NAME}" / "private" / "intermediate.key.pem"
            if local_root.exists() and local_int.exists() and local_key.exists():
                log(f"⚠️  Directory-mode upstream materials missing under {base}; using local PKI at {local_base} instead")
                chain_local = local_base / f"intermediate-{UPSTREAM_CA_NAME}" / "certs" / "chain.pem"
                return "dir", {"root_cert": local_root, "int_cert": local_int, "int_key": local_key, "chain": chain_local}

        _warn_or_raise("Directory-mode upstream materials missing.", details="Missing:\n" + "\n".join(f"- {p}" for p in missing))
        return None

    mats = {"root_cert": root_cert, "int_cert": int_cert, "int_key": int_key}
    if chain.exists():
        mats["chain"] = chain
    return "dir", mats


def sync_upstream(base_dir: Path, mode: str, mats: dict[str, Path]) -> None:
    upstream_dir = base_dir / "upstream"
    upstream_dir.mkdir(parents=True, exist_ok=True)

    dst_root = upstream_dir / "root.cert.pem"
    dst_int_cert = upstream_dir / "intermediate.cert.pem"
    dst_int_key = upstream_dir / "intermediate.key.pem"
    dst_chain = upstream_dir / "chain.pem"

    shutil.copy2(mats["root_cert"], dst_root)
    shutil.copy2(mats["int_cert"], dst_int_cert)
    shutil.copy2(mats["int_key"], dst_int_key)

    os.chmod(dst_root, 0o644)
    os.chmod(dst_int_cert, 0o644)
    os.chmod(dst_int_key, 0o600)

    if "chain" in mats and mats["chain"].exists():
        shutil.copy2(mats["chain"], dst_chain)
    else:
        chain_pem = dst_int_cert.read_text(encoding="utf-8") + "\n" + dst_root.read_text(encoding="utf-8")
        dst_chain.write_text(chain_pem.strip() + "\n", encoding="utf-8")

    os.chmod(dst_chain, 0o644)
    log(f"✅ UpstreamAuthority materials copied into {upstream_dir} (mode={mode})")


def server_conf(use_upstream: bool) -> str:
    upstream_block = ""
    if use_upstream:
        upstream_block = """

  UpstreamAuthority \"disk\" {
    plugin_data {
      cert_file_path = \"/opt/spire/conf/upstream/intermediate.cert.pem\"
      key_file_path  = \"/opt/spire/conf/upstream/intermediate.key.pem\"
      bundle_path    = \"/opt/spire/conf/upstream/root.cert.pem\"
    }
  }
"""

    return f"""
server {{
  bind_address = \"0.0.0.0\"
  bind_port = 8081
  trust_domain = \"${{SPIFFE_TRUST_DOMAIN}}\"

  data_dir = \"/run/spire\"

  ca_ttl = \"{CA_TTL}\"
  default_x509_svid_ttl = \"{DEFAULT_X509_SVID_TTL}\"

  log_level = \"{SERVER_LOG_LEVEL}\"
}}

plugins {{
  DataStore \"sql\" {{
    plugin_data {{
      database_type = \"postgres\"
      connection_string = \"host=postgres port=5432 user=spire password=spire dbname=spire sslmode=disable connect_timeout=5\"
    }}
  }}

  KeyManager \"disk\" {{
    plugin_data {{
      keys_path = \"/run/spire/keys.json\"
    }}
  }}

  NodeAttestor \"join_token\" {{
    plugin_data {{}}
  }}
{upstream_block}
}}
""".lstrip("\n")


def nginx_conf() -> str:
    return """
events {}
http {
  server {
    listen 8081;
    location / {
      return 200 \"OK\\n\";
    }
  }
}
""".lstrip("\n")


def compose_yaml(use_upstream: bool) -> str:
    upstream_vol = ""
    if use_upstream:
        upstream_vol = "\n      - ./upstream:/opt/spire/conf/upstream:ro"

    return f"""
services:
  postgres:
    image: {POSTGRES_IMAGE}
    environment:
      POSTGRES_PASSWORD: spire
      POSTGRES_USER: spire
      POSTGRES_DB: spire
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - \"5432:5432\"
    healthcheck:
      test: [\"CMD-SHELL\", \"pg_isready -U spire -d spire -h 127.0.0.1 -p 5432\"]
      interval: 2s
      timeout: 3s
      retries: 60
      start_period: 5s
    networks:
      {NET_NAME}:
        ipv4_address: {IP_PG}

  spire-server-1:
    image: {SPIRE_SERVER_IMAGE}
    volumes:
      - ./server1/server.conf:/opt/spire/conf/server/server.conf:ro
      - ./persistence/server1:/run/spire{upstream_vol}
    depends_on:
      postgres:
        condition: service_healthy
    restart: on-failure
    networks:
      {NET_NAME}:
        ipv4_address: {IP_S1}

  spire-server-2:
    image: {SPIRE_SERVER_IMAGE}
    volumes:
      - ./server2/server.conf:/opt/spire/conf/server/server.conf:ro
      - ./persistence/server2:/run/spire{upstream_vol}
    depends_on:
      postgres:
        condition: service_healthy
    restart: on-failure
    networks:
      {NET_NAME}:
        ipv4_address: {IP_S2}

  load-balancer:
    image: {NGINX_IMAGE}
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - \"8081:8081\"
    depends_on:
      - spire-server-1
      - spire-server-2
    networks:
      {NET_NAME}:
        ipv4_address: {IP_LB}

volumes:
  pgdata:

networks:
  {NET_NAME}:
    driver: bridge
    ipam:
      config:
        - subnet: {NET_SUBNET}
""".lstrip("\n")


def write_file(path: Path, content: str) -> None:
    lines = content.splitlines()
    if lines and lines[0].strip() == "\\":
        content = "\n".join(lines[1:]).lstrip("\n")
    content = content if content.endswith("\n") else content + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log(f"Updated: {path}")


def prepare_dirs(base_dir: Path, mode: int) -> None:
    log("--- Preparing Directories ---")
    for d in [
        base_dir,
        base_dir / "persistence" / "server1",
        base_dir / "persistence" / "server2",
        base_dir / "persistence" / "agent",
        base_dir / "server1",
        base_dir / "server2",
        base_dir / "nginx",
        base_dir / "upstream",
    ]:
        d.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(d, mode)
        except Exception:
            pass


def docker_compose(base_dir: Path, project: str, compose_file: Path, args: list[str]) -> None:
    subprocess.run(["docker", "compose", "-p", project, "-f", str(compose_file)] + args, cwd=str(base_dir), check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=str(Path(__file__).parent / "spire_setup"))
    ap.add_argument("--project-name", default="spire_setup")
    ap.add_argument("--dir-mode", default="0775")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--trust-domain", default=os.environ.get("SPIFFE_TRUST_DOMAIN") or "bns-demo.test")
    ap.add_argument("--generate-only", action="store_true")
    ap.add_argument("--clean", dest="clean", action="store_true", default=True)
    ap.add_argument("--no-clean", dest="clean", action="store_false")

    args = ap.parse_args()

    td = normalize_trust_domain(args.trust_domain)
    os.environ["SPIFFE_TRUST_DOMAIN"] = td

    log(f"🔎 TTL sanity: ca_ttl={CA_TTL}, default_x509_svid_ttl={DEFAULT_X509_SVID_TTL}, trust_domain={td}")

    base_dir = Path(args.base_dir).expanduser().resolve()
    compose_file = base_dir / "docker-compose.yaml"
    mode = int(args.dir_mode, 8)

    prepare_dirs(base_dir, mode)

    upstream = detect_upstream_materials()
    use_upstream = upstream is not None
    if use_upstream:
        mode_name, mats = upstream
        sync_upstream(base_dir, mode_name, mats)
        log("🔗 UpstreamAuthority: ENABLED")
    else:
        log("ℹ️ UpstreamAuthority: disabled")

    write_file(base_dir / "server1" / "server.conf", Template(server_conf(use_upstream)).safe_substitute(os.environ))
    write_file(base_dir / "server2" / "server.conf", Template(server_conf(use_upstream)).safe_substitute(os.environ))
    write_file(base_dir / "nginx" / "nginx.conf", nginx_conf())
    write_file(compose_file, compose_yaml(use_upstream))

    if args.generate_only:
        log("✅ generate-only: configs written; not starting containers")
        return 0

    log("\n--- Launching Infrastructure ---")
    if args.clean:
        docker_compose(base_dir, args.project_name, compose_file, ["down", "--remove-orphans"])
    docker_compose(base_dir, args.project_name, compose_file, ["up", "-d", "--remove-orphans"])
    log("✅ Stack launched successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
