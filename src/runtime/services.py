# -*- coding: utf-8 -*-
"""Knowledge base of network services that are dangerous when exposed.

port -> (service, category, severity_if_exposed, why, how_to_fix).
Severity applies when the service listens on ALL interfaces (0.0.0.0 / ::);
on localhost the same service is safe. Process names are matched too, because
many tools move to random ports.
"""

CRITICAL, HIGH, MEDIUM, LOW, INFO = "critical", "high", "medium", "low", "info"
SEVERITY_ORDER = {CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4}

_DB_FIX = "Bind it to 127.0.0.1 or block the port in the firewall."
PORTS = {
    # ---- AI / LLM / vector databases ----
    11434: ("Ollama (local AI models)", "ai", CRITICAL,
            "Anyone who can reach this port can run your models, read prompts and pull or delete models.",
            "Set OLLAMA_HOST=127.0.0.1 and restart Ollama."),
    1234: ("LM Studio server", "ai", CRITICAL, "Exposes your local models to the network without authentication.",
           "In LM Studio: Server settings, turn off 'Serve on Local Network'."),
    8080: ("Web / AI server (llama.cpp, Open WebUI)", "ai", HIGH,
           "Often an AI chat UI or llama.cpp server without a password.", "Start it with --host 127.0.0.1 or add a login."),
    7860: ("Gradio app (AI demos, Stable Diffusion)", "ai", HIGH,
           "Gradio apps run models and file uploads, usually without a password.",
           "Launch with server_name='127.0.0.1' or set auth."),
    8000: ("Python API server (FastAPI, vLLM)", "ai", HIGH,
           "Model and agent APIs are often started without authentication.", "Start with --host 127.0.0.1 or add an API key."),
    8888: ("Jupyter Notebook", "dev", CRITICAL, "An open Jupyter lets anyone run any code on this computer.",
           "Run Jupyter with --ip=127.0.0.1 and keep the token enabled."),
    6333: ("Qdrant vector database", "ai", CRITICAL,
           "Vector databases hold your documents; Qdrant has no auth by default.", "Bind to 127.0.0.1 or set an API key."),
    6334: ("Qdrant gRPC", "ai", CRITICAL, "Same data as Qdrant, via gRPC.", "Bind to 127.0.0.1 or set an API key."),
    8001: ("Chroma vector database", "ai", HIGH, "Chroma stores your documents and has no auth by default.",
           "Bind to 127.0.0.1 or enable auth."),
    19530: ("Milvus vector database", "ai", CRITICAL, "Collections of your data, no auth by default.",
            "Bind to 127.0.0.1 and enable authentication."),
    8265: ("Ray dashboard", "ai", CRITICAL, "An open Ray dashboard lets anyone run jobs on this machine.", "Bind to 127.0.0.1."),
    5000: ("Web app / Flask dev server", "web", MEDIUM, "Dev servers usually have no auth and may have debug mode.",
           "Bind to 127.0.0.1 or stop it when not in use."),
    3000: ("Web app (Next.js, Grafana, Open WebUI)", "web", MEDIUM, "Dashboards may expose data or admin panels.",
           "Bind to 127.0.0.1 or add authentication."),
    # ---- databases ----
    5432: ("PostgreSQL database", "db", CRITICAL, "An open database is the classic SaaS data breach.",
           "Set listen_addresses='localhost' or block the port."),
    3306: ("MySQL / MariaDB database", "db", CRITICAL, "An open database is the classic SaaS data breach.",
           "Set bind-address=127.0.0.1 or block the port."),
    1433: ("Microsoft SQL Server", "db", CRITICAL, "Database reachable from the network.", _DB_FIX),
    27017: ("MongoDB database", "db", CRITICAL, "Open MongoDB servers are routinely wiped and held for ransom.",
            "Set net.bindIp: 127.0.0.1 and enable authorization."),
    6379: ("Redis", "db", CRITICAL, "Open Redis allows reading all data and often running code.",
           "Set bind 127.0.0.1 and requirepass."),
    9200: ("Elasticsearch / OpenSearch", "db", CRITICAL, "One of the most common sources of leaked records.",
           "Bind to 127.0.0.1 and enable security."),
    5984: ("CouchDB", "db", CRITICAL, "Exposes all documents.", "Bind to 127.0.0.1 and set an admin password."),
    11211: ("Memcached", "db", HIGH, "Leaks cached data and can be abused for DDoS.", "Bind to 127.0.0.1."),
    9042: ("Cassandra", "db", HIGH, "Database reachable from the network.", _DB_FIX),
    # ---- remote access ----
    3389: ("Remote Desktop (RDP)", "remote", HIGH, "The most attacked service on the internet (brute force, ransomware).",
           "Turn off Remote Desktop or use it only through a VPN."),
    5900: ("VNC remote desktop", "remote", CRITICAL, "Often unencrypted or weakly protected.", "Use only through a VPN or SSH tunnel."),
    22: ("SSH", "remote", MEDIUM, "Remote shell; safe only with keys and no passwords.", "Use key-only login."),
    23: ("Telnet", "remote", CRITICAL, "Unencrypted remote access.", "Disable Telnet."),
    2375: ("Docker API without TLS", "remote", CRITICAL, "An open Docker API is full control of the machine.",
           "Never expose port 2375."),
    5985: ("WinRM (PowerShell remoting)", "remote", HIGH, "Remote command execution on Windows.", "Disable or restrict to admins."),
    # ---- file sharing ----
    445: ("Windows file sharing (SMB)", "share", MEDIUM,
          "Fine inside a trusted home network; dangerous if forwarded to the internet.",
          "Never forward port 445 on the router. Turn off sharing on public Wi-Fi."),
    139: ("NetBIOS file sharing", "share", MEDIUM, "Legacy file sharing.", "Disable NetBIOS over TCP/IP if unused."),
    21: ("FTP", "share", HIGH, "Unencrypted file transfer.", "Use SFTP instead."),
}

# Process name hints (lowercase, without .exe) for services on random ports.
PROCESSES = {
    "ollama": ("Ollama (local AI models)", "ai", CRITICAL,
               "Anyone on the network can use or delete your models.", "Set OLLAMA_HOST=127.0.0.1."),
    "llama-server": ("llama.cpp server (local AI model)", "ai", CRITICAL,
                     "Your local model and its prompts are reachable from the network.", "Start it with --host 127.0.0.1."),
    "lm studio": ("LM Studio", "ai", CRITICAL, "Local models exposed to the network.", "Turn off 'Serve on Local Network'."),
    "jupyter": ("Jupyter", "dev", CRITICAL, "Anyone can run code on this computer.", "Use --ip=127.0.0.1."),
    "postgres": ("PostgreSQL database", "db", CRITICAL, "Open database.", "Set listen_addresses='localhost'."),
    "mysqld": ("MySQL database", "db", CRITICAL, "Open database.", "Set bind-address=127.0.0.1."),
    "mongod": ("MongoDB database", "db", CRITICAL, "Open database.", "Set net.bindIp: 127.0.0.1."),
    "redis-server": ("Redis", "db", CRITICAL, "Open Redis.", "Set bind 127.0.0.1 and requirepass."),
    "qdrant": ("Qdrant vector database", "ai", CRITICAL, "Your embeddings are reachable.", "Bind to 127.0.0.1."),
    "ngrok": ("ngrok tunnel", "tunnel", CRITICAL,
              "ngrok publishes a local service on the internet, bypassing your router and firewall.",
              "Stop ngrok when you are not sharing, and protect the tunnel with a password."),
    "cloudflared": ("Cloudflare tunnel", "tunnel", HIGH, "Publishes local services on the internet.",
                    "Make sure the tunnel requires a Cloudflare Access login."),
    "anydesk": ("AnyDesk remote access", "remote", HIGH, "Remote control of this computer.",
                "Set an unattended-access password or uninstall it."),
    "teamviewer": ("TeamViewer remote access", "remote", HIGH, "Remote control of this computer.", "Enable 2-factor login."),
    "asusupdatecheck": ("ASUS update service", "vendor", MEDIUM,
                        "Vendor update services listening on the network have had remote-code-execution bugs.",
                        "Keep ASUS software updated, or disable the service if you do not need it."),
    "steam": ("Steam (Remote Play / LAN)", "app", LOW, "Game streaming and LAN discovery.", "Normal for Steam. Nothing to do."),
    "spoolsv": ("Windows Print Spooler", "system", LOW,
                "Printer sharing service. It has had serious remote bugs (PrintNightmare).",
                "If you never print to or from other computers, disable the Print Spooler service."),
}

# Ports Windows itself uses; shown, but not alarming on a private network.
WINDOWS_SYSTEM = {135, 5040, 5357, 7680} | set(range(49664, 49700))
# UDP network-discovery / VPN-negotiation ports used by Windows and browsers.
DISCOVERY_UDP = {137, 138, 500, 1900, 3702, 4500, 5050, 5353, 5355}
EPHEMERAL_START = 49152
TUNNEL_PROCESSES = {"ngrok", "cloudflared", "frpc", "bore", "localtunnel", "lt", "tailscale-funnel"}
