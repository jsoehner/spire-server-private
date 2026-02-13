#!/usr/bin/env python3
"""add_agent.py (v2.12) - SPIRE Agent registration with diagnostics

If the SPIRE server crashes (e.g., upstream chain invalid), the admin socket won't exist.
When socket discovery fails, this script dumps server logs for quick root-cause.

"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_DIR = Path.cwd()
BASE_DIR = REPO_DIR / "spire_setup"
COMPOSE_FILE = BASE_DIR / "docker-compose.yaml"
AGENT_OVERRIDE_FILE = BASE_DIR / "docker-compose.agent.yaml"

AGENT_SPIFFE_ID = os.environ.get("AGENT_SPIFFE_ID", "").strip()
SERVER_ADDR = os.environ.get("SPIRE_SERVER_ADDR", "172.28.0.11").strip()
SERVER_PORT = os.environ.get("SPIRE_SERVER_PORT", "8081").strip()

SOCKET_CANDIDATES = [
    "/tmp/spire-server/private/api.sock",
    "/run/spire/private/api.sock",
    "/run/spire/server/sockets/main/private/api.sock",
    "/run/spire/server/sockets/default/private/api.sock",
]


def run_cmd(args: list[str], *, cwd: Path | None = None, check: bool = True) -> str:
    cp = subprocess.run(args, cwd=str(cwd) if cwd else None, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = (cp.stdout or "").strip()
    if check and cp.returncode != 0:
        raise RuntimeError(f"Command failed ({cp.returncode}): {' '.join(args)}\n{out}")
    return out


def _dump_server_logs() -> None:
    try:
        print("\n--- Diagnostics: docker compose ps ---")
        subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "ps"], cwd=str(BASE_DIR), check=False)
        print("\n--- Diagnostics: spire-server-1 logs (tail) ---")
        subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "logs", "--tail=200", "spire-server-1"], cwd=str(BASE_DIR), check=False)
        print("\n--- Diagnostics: spire-server-2 logs (tail) ---")
        subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "logs", "--tail=200", "spire-server-2"], cwd=str(BASE_DIR), check=False)
    except Exception:
        pass


def get_container_id(service_name: str) -> str:
    out = run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "-q", service_name], cwd=BASE_DIR, check=True)
    if not out:
        raise RuntimeError(f"Service '{service_name}' is not running.")
    return out


def container_running(container_id: str) -> bool:
    out = run_cmd(["docker", "inspect", "-f", "{{.State.Status}}", container_id], check=False)
    return out.strip() == "running"


def parse_trust_domain() -> str:
    td = os.environ.get("SPIFFE_TRUST_DOMAIN", "").strip().lower()
    if td:
        return td
    server_conf = BASE_DIR / "server1" / "server.conf"
    if server_conf.exists():
        m = re.search(r'\btrust_domain\s*=\s*"([^"]+)"', server_conf.read_text(encoding="utf-8"))
        if m:
            return m.group(1).strip().lower()
    raise RuntimeError("Unable to determine trust domain. Set SPIFFE_TRUST_DOMAIN env var.")


def clean_agent_state() -> None:
    print("--- Cleaning Stale Agent Data ---")
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "stop", "spire-agent"], cwd=str(BASE_DIR),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    agent_data_path = BASE_DIR / "persistence" / "agent"
    if agent_data_path.exists():
        print(f"Removing old agent data: {agent_data_path}")
        try:
            shutil.rmtree(agent_data_path)
        except PermissionError:
            subprocess.run(["sudo", "rm", "-rf", str(agent_data_path)], check=False)
    agent_data_path.mkdir(parents=True, exist_ok=True)
    os.chmod(agent_data_path, 0o775)


def discover_admin_socket(container_id: str) -> str:
    for sock in SOCKET_CANDIDATES:
        out = run_cmd(["docker", "exec", container_id,
                       "/opt/spire/bin/spire-server", "bundle", "show",
                       "-format", "pem", "-socketPath", sock], check=False)
        if out.startswith("-----BEGIN"):
            return sock
    _dump_server_logs()
    raise RuntimeError("Could not discover SPIRE admin socket. Tried: " + ", ".join(SOCKET_CANDIDATES))


def write_agent_override_compose() -> None:
    content = """\
services:
  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.14.1
    restart: on-failure
    depends_on:
      - spire-server-1
    volumes:
      - ./agent/agent.conf:/opt/spire/conf/agent/agent.conf:ro
      - ./agent/bootstrap.crt:/opt/spire/conf/agent/bootstrap.crt:ro
      - ./persistence/agent:/opt/spire/data/agent
      - /var/run/docker.sock:/var/run/docker.sock
    command: ["run", "-config", "/opt/spire/conf/agent/agent.conf"]
    pid: "host"
    networks:
      spire_demo_net:
"""
    AGENT_OVERRIDE_FILE.write_text(content, encoding="utf-8")


def _load_external_chain_if_present() -> str | None:
    chain_path = BASE_DIR / "upstream" / "chain.pem"
    if chain_path.exists():
        return chain_path.read_text(encoding="utf-8")
    return None


def write_agent_files(server_bundle_pem: str, join_token: str, trust_domain: str, agent_spiffe_id: str) -> None:
    agent_dir = BASE_DIR / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(agent_dir, 0o775)

    external_chain = _load_external_chain_if_present()
    bootstrap_pem = (external_chain.strip() + "\n") if external_chain else (server_bundle_pem.strip() + "\n")

    (agent_dir / "bootstrap.crt").write_text(bootstrap_pem, encoding="utf-8")

    agent_conf_content = f"""
    agent {{
        data_dir = "/opt/spire/data/agent"
        log_level = "DEBUG"

        server_address = "{SERVER_ADDR}"
        server_port = "{SERVER_PORT}"

        socket_path = "/tmp/spire-agent/public/api.sock"

        trust_bundle_path = "/opt/spire/conf/agent/bootstrap.crt"
        trust_domain = "{trust_domain}"

        join_token = "{join_token}"
    }}

    plugins {{
        NodeAttestor "join_token" {{
            plugin_data {{}}
        }}

        KeyManager "disk" {{
            plugin_data {{
                directory = "/opt/spire/data/agent"
            }}
        }}

        WorkloadAttestor "docker" {{
            plugin_data {{
                use_new_container_locator = true
            }}
        }}
    }}
    """

    (agent_dir / "agent.conf").write_text(textwrap.dedent(agent_conf_content).strip() + "\n", encoding="utf-8")
    print(f"Agent SPIFFE ID: {agent_spiffe_id}")


def main() -> None:
    if not COMPOSE_FILE.exists():
        raise SystemExit(f"ERROR: Missing compose file: {COMPOSE_FILE}. Run setup first.")

    clean_agent_state()

    server_id = None
    for idx in (1, 2):
        try:
            cid = get_container_id(f"spire-server-{idx}")
            if container_running(cid):
                server_id = cid
                break
        except Exception:
            continue

    if not server_id:
        _dump_server_logs()
        raise SystemExit("ERROR: Could not find a running spire-server container.")

    trust_domain = parse_trust_domain()
    agent_spiffe_id = AGENT_SPIFFE_ID or f"spiffe://{trust_domain}/agent/demo-agent"

    sock = discover_admin_socket(server_id)

    server_bundle = run_cmd(["docker", "exec", server_id,
                             "/opt/spire/bin/spire-server", "bundle", "show",
                             "-format", "pem", "-socketPath", sock], check=True)

    token_out = run_cmd(["docker", "exec", server_id,
                         "/opt/spire/bin/spire-server", "token", "generate",
                         "-spiffeID", agent_spiffe_id,
                         "-socketPath", sock], check=True)

    m = re.search(r"Token:\s+([a-f0-9-]+)", token_out, re.IGNORECASE)
    if not m:
        raise SystemExit(f"Failed to parse token from output:\n{token_out}")

    join_token = m.group(1)
    write_agent_files(server_bundle, join_token, trust_domain, agent_spiffe_id)
    write_agent_override_compose()

    run_cmd(["docker", "compose", "-f", str(COMPOSE_FILE), "-f", str(AGENT_OVERRIDE_FILE),
             "up", "-d", "--force-recreate", "spire-agent"], cwd=BASE_DIR, check=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
