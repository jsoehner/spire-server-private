(spire2) ➜  spire-server-private git:(main) ./run.sh --newroot --reset                                         
==========================================
   🚀 Starting SPIRE Demo Runner (v2.12)
   setup_demo.py | add_agent.py
   RESET: enabled
   NEWROOT: enabled
==========================================
--- Found local upstream PKI in /Users/jsoehner/spire-server-private/spire_setup/pki; enabling upstream (auto) ---
--- Generating upstream root+intermediate via pki.sh (force) ---
(pki.sh does not support --subject-root/--subject-int; using legacy --subject)
==> Removing existing Root CA dir (force): /Users/jsoehner/spire-server-private/spire_setup/pki/root-spire-demo
==> Creating Root CA at: /Users/jsoehner/spire-server-private/spire_setup/pki/root-spire-demo
==> Generating Root CA private key (rsa)...
...+....+......+.....+....+..+....+........+............+.+...+..+.........+..........+.........+.....+....+++++++++++++++++++++++++++++++++++++++++++++*....+...+..+...+..........+.....+.+.....+......+....+.....+.+......+..+.............+.....+...+.+...+..+.+++++++++++++++++++++++++++++++++++++++++++++*..+......+.....+.........+....+......+.....+....+...+..+.+.....+...................+..+..........+.......................+...+.......+.....+.......+......+............+.......................+...+.+...+............+.....+.........+....+...+...+..............+.+.........+.....+.......+........+...............+.......+........+.......+......+...+..+.........+.+............+.....+.+.........+...+..+.+......+...+..+.+..................+..+.........+.+........+............+...+..........+......+...+......+.....................+......+.........+......+.................+............+.............+............+.....+.............+......+.....+......+...+.............+...+.........+...+..................+.........+............+...........+.......+........+.......+.....+.+......+...............+.....+...+..........+...+........+.......+..+..................+.......+............+...+....................+.+..............+......+....+...+...+...........+..........+.....+....+..+....+......+..+...+...+.....................+.+..............+..........+..............+......+....+......+...+..+...+...+...+....+...........+.+......+..+.+.................+...+...............+....+...+............+............+...........+...+.....................+...+..................+....+........+......+............+...+....+............+...+......+...............+..+.........+....+...........+.+...+............+........+......+.............+.....+.+..+..................+....+...+..+...+..........+........+.+........+.+.....+.+...........+...+....+..+....+..+...+....+.....+..........+.....................+............+.........+.....+.+............+...........+.+.........+...........+.+..................+..............+...+...+.+...+......+......+...........+...+......+.............+...+........+.......+..+...+.......+.....+................+.....+.......+..+.......+.....+...+..........+.....+......+............+.............+..+.........+...+.+..............+.+......+.....+.+.........+.....+....+......+......+.....+.......+.....................+......+.....+.........+....+............+..............+.+......+........+.........+..........+++++
.........+...+...+.......+..+............+.+..+......+.+....................+....+.........+.....+.+......+...+..+++++++++++++++++++++++++++++++++++++++++++++*....+......................+++++++++++++++++++++++++++++++++++++++++++++*....+......+........................+...........+..........+..............+.+..+..................+.......+..+.+.........+...+..+................+..+....+...+........+...+.+.........+..+.......+..+.............+...........+.........+.......+.....+...+............+...+......+......+...+..........+......+..+............+.......+.....................+..+.......+...+...+.........+..................+............+......+........+......+....+...........+......+.......+......+...........+...+............+......+....+...............+......+........+............+.........+...+.+..+..........+...+............+....................+.........+.+..+......+....+.....................+..+.......+..+...+......+...............+.......+..+..................+...+......+.+..............+.+...............+........................+.........+......+.....+...+.+...........+.+...+.....+.......+........+.....................+...+.......+.....+.........+.........+.+.....+.......+........+++++
==> Generating self-signed Root CA certificate (days=3650)...
==> Root CA created:
 Root key : /Users/jsoehner/spire-server-private/spire_setup/pki/root-spire-demo/private/ca.key.pem
 Root cert: /Users/jsoehner/spire-server-private/spire_setup/pki/root-spire-demo/certs/ca.cert.pem
==> Removing existing Intermediate CA dir (force): /Users/jsoehner/spire-server-private/spire_setup/pki/intermediate-spire-demo
==> Creating Intermediate CA at: /Users/jsoehner/spire-server-private/spire_setup/pki/intermediate-spire-demo
==> Generating Intermediate CA private key (rsa)...
..+.........+..+++++++++++++++++++++++++++++++++++++++++++++*.....+........+....+...+..+....+..+...+....+...+..+...+....+.....+.............+...+..+.+.........+..+...+.+...........+....+.....+.+......+........+....+...........+....+....................+..........+...+..+.+.........+..+...+.+......+......+............+..+.+........+.+......+.....+..........+..+.+..+.......+......+..+....+..............+..........+...........+.+++++++++++++++++++++++++++++++++++++++++++++*....+....+...+.....+.+......+........+.+..+...+......+.+.....+.......+...........+.......+............+...........+.......+.......................+.+..............+.+...+..+...+..................+..........+.................+...+..........+.....+.......+..+.+..+......+......+.+..............+...+.......+......+...+..+..........+............+........+..........+..+......+.+.....+.+..................+.....+............+....+......+.....+.......+.....+.+..+.......+..+....+.....+....+......+..+...+.......+...+......+.........+.........+..+......+..........+.....+...+.......+.....+............+.............+............+..+....+......+......+..+............+..........+...........+.............+..+......................+............+........+......+.+.....+.........+.......+.....+.............+...........+....+...........+...+...............+..........+...+..................+.........+.................+....+...........+...+...+.........+.........................+.....+.+...+.....+.......+............+..+.+........+..........+.........+.................+......+............+...+...+......+...+......+.+......+...+..+...............+....+....................+.+.....+....+.....................+..+.+..+.......+.....+......+......+...+.+......+......+..+..........+..+.+........+......+....+..+....+.........+..+...+.+......+.....+...+....+............+......+.....+....+..................+++++
....+......+...+..........+..+......+....+......+..............+.+.....+++++++++++++++++++++++++++++++++++++++++++++*..+++++++++++++++++++++++++++++++++++++++++++++*....+.+.........+....................+.......+..............+.+..+............+....+.........+.....+......+....+..+...+.+.....+.+......+..+......+.........+............+.+............+......+.........+........+.......+...+.........+.........+.....+.......+.........+........+...+.....................................+..+......+..........+........+.+..............+..........+..+...+....+...+.....+.......+......+.....+....+..+......+...............+....+...........+....+...............+.....+.+..+...+...+....+...+.........+.........+.....+......+.+.....+++++
==> Generating Intermediate CSR...
==> Signing Intermediate certificate with Root CA (non-interactive -batch)...
Using configuration from /Users/jsoehner/spire-server-private/spire_setup/pki/root-spire-demo/openssl.cnf
Check that the request matches the signature
Signature ok
The Subject's Distinguished Name is as follows
countryName           :PRINTABLE:'CA'
stateOrProvinceName   :ASN.1 12:'ON'
localityName          :ASN.1 12:'Scarborough'
organizationName      :ASN.1 12:'Scotiabank'
organizationalUnitName:ASN.1 12:'PKI'
commonName            :ASN.1 12:'bns-demo.test SPIRE Upstream Intermediate CA'
Certificate is to be certified until Feb 12 20:42:13 2031 GMT (1825 days)

Write out database with 1 new entries
Database updated
==> Creating chain.pem (Intermediate + Root)...
==> Intermediate CA created:
 Intermediate key : /Users/jsoehner/spire-server-private/spire_setup/pki/intermediate-spire-demo/private/intermediate.key.pem
 Intermediate cert: /Users/jsoehner/spire-server-private/spire_setup/pki/intermediate-spire-demo/certs/intermediate.cert.pem
 Chain (int+root) : /Users/jsoehner/spire-server-private/spire_setup/pki/intermediate-spire-demo/certs/chain.pem
--- Upstream PKI ready at: /Users/jsoehner/spire-server-private/spire_setup/pki ---
--- Reset requested: wiping compose volumes ---
--- Reset complete ---
Step 1: Running Infrastructure Setup (setup_demo.py)...
🔎 TTL sanity: ca_ttl=60m, default_x509_svid_ttl=300s, trust_domain=bns-demo.test
--- Preparing Directories ---
✅ UpstreamAuthority materials copied into /Users/jsoehner/spire-server-private/spire_setup/upstream (mode=dir)
🔗 UpstreamAuthority: ENABLED
Updated: /Users/jsoehner/spire-server-private/spire_setup/server1/server.conf
Updated: /Users/jsoehner/spire-server-private/spire_setup/server2/server.conf
Updated: /Users/jsoehner/spire-server-private/spire_setup/nginx/nginx.conf
Updated: /Users/jsoehner/spire-server-private/spire_setup/docker-compose.yaml

--- Launching Infrastructure ---
[+] up 35/35
 ✔ Image mirror.gcr.io/chainguard/postgres:latest Pulled                                                                                                                                                                                     18.2s
 ✔ Image ghcr.io/spiffe/spire-server:1.14.1       Pulled                                                                                                                                                                                     11.8s
 ✔ Image mirror.gcr.io/chainguard/nginx:latest    Pulled                                                                                                                                                                                     5.3ss
 ✔ Network spire_setup_spire_demo_net             Created                                                                                                                                                                                    0.0s
 ✔ Volume spire_setup_pgdata                      Created                                                                                                                                                                                    0.0s
 ✔ Container spire_setup-postgres-1               Healthy                                                                                                                                                                                    6.2s
 ✔ Container spire_setup-spire-server-2-1         Created                                                                                                                                                                                    0.1s
 ✔ Container spire_setup-spire-server-1-1         Created                                                                                                                                                                                    0.1s
 ✔ Container spire_setup-load-balancer-1          Created                                                                                                                                                                                    0.0s
✅ Stack launched successfully.
✅ Infrastructure setup complete.
⏳ Waiting 15 seconds for Postgres and SPIRE Server to stabilize...
Step 2: Registering Agent (add_agent.py)...
--- Cleaning Stale Agent Data ---
Removing old agent data: /Users/jsoehner/spire-server-private/spire_setup/persistence/agent
Agent SPIFFE ID: spiffe://bns-demo.test/agent/demo-agent
✅ Agent registration complete.
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=warning msg="Current umask 0022 is too permissive; setting umask 0027"
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg=Configured admin_ids="[]" data_dir=/run/spire launch_log_level=debug version=1.14.1
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Opening SQL database" db_type=postgres subsystem_name=sql
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Initializing new database" subsystem_name=sql
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Connected to SQL database" read_only=false subsystem_name=sql type=postgres version=18.2
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Configured DataStore" reconfigurable=false subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Configured plugin" external=false plugin_name=disk plugin_type=KeyManager reconfigurable=false subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Plugin loaded" external=false plugin_name=disk plugin_type=KeyManager subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Configured plugin" external=false plugin_name=join_token plugin_type=NodeAttestor reconfigurable=false subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Plugin loaded" external=false plugin_name=join_token plugin_type=NodeAttestor subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Configured plugin" external=false plugin_name=disk plugin_type=UpstreamAuthority reconfigurable=false subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Plugin loaded" external=false plugin_name=disk plugin_type=UpstreamAuthority subsystem_name=catalog
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=debug msg="Loading journal from datastore" subsystem_name=ca_manager
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="There is not a CA journal record that matches any of the local X509 authority IDs" subsystem_name=ca_manager
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=info msg="Journal loaded" jwt_keys=0 subsystem_name=ca_manager wit_keys=0 x509_cas=0
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=debug msg="Preparing X509 CA" slot=A subsystem_name=ca_manager
spire-server-1-1  | time="2026-02-13T20:42:40Z" level=debug msg="There is no active X.509 authority yet. Can't save CA journal in the datastore" subsystem_name=ca_manager
