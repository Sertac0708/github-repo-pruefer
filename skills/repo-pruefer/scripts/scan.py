#!/usr/bin/env python3
"""repo-pruefer / scan.py — statische Sicherheitsprüfung eines fremden Repos.
Static security scan of a third-party repository.

Erstellt von / created by Sertac. Nur Python-Standardbibliothek / stdlib only.
Sprache der Ausgabe / output language: --lang de|en (Standard: Systemsprache).

Was das Skript tut:
  1. GitHub-Metadaten holen (über `gh api`, sonst anonym über api.github.com)
  2. Das Repo flach klonen, dabei alles abschalten, was beim Klonen Code starten
     könnte (Git-Hooks, LFS-Filter, Submodule, Symlinks, fsmonitor)
  3. Jede Datei nur LESEN und nach Mustern durchsuchen
  4. Einen Markdown-Bericht mit Fundstellen (Datei:Zeile) ausgeben

Was das Skript NIE tut: Code aus dem Repo ausführen, Pakete installieren,
Skripte aus dem Repo starten.

Aufruf:
  python3 scan.py https://github.com/owner/repo [--ziel DIR] [--json DATEI]
  python3 scan.py --lokal /pfad/zu/ordner          (bereits vorhandener Ordner)
  Optionen: --ohne-npm  (keine `npm view`-Abfragen), --lang de|en

Usage (English):
  python3 scan.py https://github.com/owner/repo --lang en [--ziel DIR] [--json FILE]
  python3 scan.py --lokal /path/to/folder --lang en      (existing folder)
  Options: --ohne-npm (no npm/PyPI lookups)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

LANG = "de"   # wird in main() gesetzt / set in main()

# Deutsch → Englisch. Interne Schlüssel bleiben deutsch; übersetzt wird nur die Ausgabe.
EN = {
    # Regeltitel / rule titles
    "macOS-Autostart (LaunchAgent/launchctl)": "macOS autostart (LaunchAgent/launchctl)",
    "Cron/Autostart beim Booten": "Cron / start at boot",
    "Hintergrundprozess (nohup/daemon/detached)": "Background process (nohup/daemon/detached)",
    "Datei-Watcher": "File watcher",
    "Bekannter Abflusskanal (Webhook/Paste/Tunnel)": "Known exfiltration channel (webhook/paste/tunnel)",
    "Telemetrie/Analytics-SDK": "Telemetry/analytics SDK",
    "Fest eingebauter Analytics-Schlüssel": "Hard-coded analytics key",
    "Netzwerkaufruf im Code": "Network call in code",
    "Fest eingetragene IP-Adresse": "Hard-coded IP address",
    "Schreibt/liest Claude-Konfiguration": "Reads/writes Claude configuration",
    "Berechtigungen umgehen": "Bypasses permissions",
    "Shell-Profil verändern": "Modifies shell profile",
    "Zugriff auf Schlüssel/Zugangsdaten-Dateien": "Accesses key/credential files",
    "Schlüsselbund / Browserdaten / Krypto-Wallets": "Keychain / browser data / crypto wallets",
    "Liest alle Umgebungsvariablen": "Reads all environment variables",
    "sudo / Systemverzeichnisse / chmod 777": "sudo / system directories / chmod 777",
    "Fest eingetragener fremder Benutzerpfad": "Hard-coded foreign user path",
    "Skript aus dem Netz direkt ausgeführt (curl | sh)": "Remote script executed directly (curl | sh)",
    "Unversionierter Paketaufruf (@latest / npx -y ohne Version)": "Unpinned package run (@latest / npx -y without version)",
    "npx/uvx-Aufruf (Version prüfen)": "npx/uvx call (check version)",
    "Installation direkt aus Git/URL": "Install directly from Git/URL",
    "Anthropic/OpenAI-Schlüssel": "Anthropic/OpenAI key",
    "GitHub-Token": "GitHub token",
    "AWS-Schlüssel": "AWS key",
    "Slack/Stripe/Google-Schlüssel": "Slack/Stripe/Google key",
    "SendGrid/Mailgun/Slack-Webhook": "SendGrid/Mailgun/Slack webhook",
    "Datenbank-/URL-Zugang mit Passwort": "Database/URL credentials with password",
    "JWT-Token im Klartext": "Plain-text JWT",
    "Privater Schlüssel im Repo": "Private key in repo",
    "Möglicher Klartext-Schlüssel": "Possible plain-text secret",
    "Lokaler Datenbank-Zugang (Entwicklung)": "Local database credentials (development)",
    "Verschleierter Code wird ausgeführt": "Obfuscated code is executed",
    "Reverse Shell": "Reverse shell",
    "Krypto-Miner": "Crypto miner",
    "Zerstörerischer Befehl": "Destructive command",
    "Tastatur/Zwischenablage mitlesen": "Keyboard/clipboard capture",
    "Lange Hex-/Zeichencode-Folge (Verschleierung?)": "Long hex/char-code sequence (obfuscation?)",
    "Startet Shell-Befehle": "Runs shell commands",
    "Text, der eine KI umsteuern will": "Text trying to redirect an AI",
    "Richtet sich direkt an einen KI-Assistenten": "Addresses an AI assistant directly",
    "Echte .env-Datei im Repo": "Real .env file in repo",
    "Ausführbare Binärdatei im Repo": "Executable binary in repo",
    "Archiv im Repo (Inhalt ungeprüft)": "Archive in repo (contents not scanned)",
    "setup.py mit eigenem Installationsschritt": "setup.py with custom install step",
    "Autostart-/Hook-Datei vorhanden": "Autostart/hook file present",
    "Extrem lange Codezeile (verschleiert/minifiziert?)": "Extremely long code line (obfuscated/minified?)",
    "Unsichtbare Steuerzeichen (Bidi/Tag-Zeichen)": "Invisible control characters (bidi/tag)",
    "Unsichtbare Zeichen im Code": "Invisible characters in code",
    "Lange Base64-Folge im Code": "Long Base64 string in code",
    "Ungültiges JSON": "Invalid JSON",
    "npm-Lebenszyklus-Skript (läuft bei npm install)": "npm lifecycle script (runs on npm install)",
    "npm-Skript (läuft bei Installation aus Git)": "npm script (runs when installed from Git)",
    "Abhängigkeit ohne feste Version / aus Git/URL": "Dependency without pinned version / from Git/URL",
    "Ungültiges JSON in Claude-Konfiguration": "Invalid JSON in Claude configuration",
    "Claude-Hook (läuft automatisch bei Ereignis)": "Claude hook (runs automatically on event)",
    "Automatische Freigabe von Werkzeugen": "Automatic tool permission grant",
    "Ungültiges JSON in MCP-Konfiguration": "Invalid JSON in MCP configuration",
    "Gehosteter MCP-Server (Daten gehen an Fremdserver)": "Hosted MCP server (data goes to a third-party server)",
    "MCP-Server startet unversioniertes Paket": "MCP server runs unpinned package",
    " (in Test-/Beispieldatei)": " (in test/example file)",
    # Stufen / verdicts
    "unbedenklich": "safe",
    "mit Einstellung nutzbar": "usable with settings",
    "Vorsicht": "caution",
    # Binärarten / binary kinds
    "ELF (Linux-Programm)": "ELF (Linux program)",
    "PE (Windows-Programm)": "PE (Windows program)",
    "Mach-O (macOS-Programm)": "Mach-O (macOS program)",
    "Mach-O Universal / Java-Klasse": "Mach-O universal / Java class",
}


def T(de: str, en: str | None = None) -> str:
    """Gibt den Text in der gewählten Sprache zurück / returns text in the chosen language."""
    if LANG != "en":
        return de
    if en is not None:
        return en
    if de.endswith(" (in Test-/Beispieldatei)"):
        return EN.get(de[:-25], de[:-25]) + EN[" (in Test-/Beispieldatei)"]
    return EN.get(de, de)


MAX_TEXT_BYTES = 1_500_000        # größere Dateien werden nur gelistet, nicht durchsucht
MAX_TREFFER_PRO_REGEL = 12        # Beispiele pro Regel im Bericht
REPO_GROESSE_WARNUNG_KB = 500_000

CODE_EXT = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".sh", ".bash", ".zsh",
    ".fish", ".ps1", ".psm1", ".bat", ".cmd", ".vbs", ".rb", ".go", ".rs", ".php",
    ".java", ".kt", ".swift", ".lua", ".pl", ".html", ".htm", ".vue", ".svelte",
    ".json", ".jsonc", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".plist",
    ".service", ".applescript", ".scpt", ".mdc",
}
DOC_EXT = {".md", ".mdx", ".txt", ".rst", ".adoc"}
BINAER_EXT = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".jar", ".class", ".pyc", ".pyo",
    ".whl", ".node", ".wasm", ".msi", ".dmg", ".pkg", ".app", ".deb", ".rpm",
    ".apk", ".scr", ".com",
}
ARCHIV_EXT = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}
BINAER_MAGIC = {
    b"\x7fELF": "ELF (Linux-Programm)",
    b"MZ": "PE (Windows-Programm)",
    b"\xcf\xfa\xed\xfe": "Mach-O (macOS-Programm)",
    b"\xce\xfa\xed\xfe": "Mach-O (macOS-Programm)",
    b"\xca\xfe\xba\xbe": "Mach-O Universal / Java-Klasse",
}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
             "Cargo.lock", "uv.lock", "bun.lockb", "composer.lock", "Gemfile.lock"}

# Adressen, die fast immer harmlos sind (Doku, Standards, Paketquellen)
HARMLOSE_DOMAINS = {
    "github.com", "raw.githubusercontent.com", "docs.github.com", "npmjs.com",
    "www.npmjs.com", "registry.npmjs.org", "pypi.org", "nodejs.org", "python.org",
    "docs.python.org", "developer.mozilla.org", "w3.org", "www.w3.org",
    "schema.org", "json-schema.org", "example.com", "example.org", "localhost",
    "opensource.org", "choosealicense.com", "semver.org", "shields.io",
    "img.shields.io", "keepachangelog.com", "creativecommons.org", "apache.org",
    "www.apache.org", "gnu.org", "www.gnu.org", "mit-license.org",
    "docs.anthropic.com", "docs.claude.com", "code.claude.com", "anthropic.com",
    "www.anthropic.com", "claude.ai", "modelcontextprotocol.io",
}

# ---------------------------------------------------------------------------
# Regeln: (kategorie, stufe, titel, muster, bereich)
#   stufe:   hoch | mittel | info
#   bereich: code | doku | alle
# ---------------------------------------------------------------------------
I = re.IGNORECASE
REGELN: list[tuple[str, str, str, re.Pattern, str]] = [
    # --- 1 Autostart --------------------------------------------------------
    ("autostart", "hoch", "macOS-Autostart (LaunchAgent/launchctl)",
     re.compile(r"LaunchAgents|LaunchDaemons|launchctl\s+(load|bootstrap|enable)", I), "code"),
    ("autostart", "hoch", "Cron/Autostart beim Booten",
     re.compile(r"crontab\s+-|@reboot|systemctl\s+(--user\s+)?enable|/etc/init\.d|rc\.local", I), "code"),
    ("autostart", "mittel", "Hintergrundprozess (nohup/daemon/detached)",
     re.compile(r"\bnohup\b|daemonize|detached\s*:\s*true|\.unref\(\)|start_new_session\s*=\s*True"), "code"),
    ("autostart", "info", "Datei-Watcher",
     re.compile(r"chokidar|fs\.watch\(|watchdog\.observers|fsevents", I), "code"),

    # --- 2 Netzwerk / Datenabfluss -----------------------------------------
    ("netzwerk", "hoch", "Bekannter Abflusskanal (Webhook/Paste/Tunnel)",
     re.compile(r"discord(app)?\.com/api/webhooks|api\.telegram\.org/bot|pastebin\.com|"
                r"hastebin|webhook\.site|requestbin|pipedream\.net|ngrok\.(io|app)|"
                r"transfer\.sh|file\.io|anonfiles|interact\.sh|oast\.(pro|fun|live)|burpcollaborator", I), "alle"),
    ("netzwerk", "mittel", "Telemetrie/Analytics-SDK",
     re.compile(r"posthog|segment\.(io|com)|analytics\.js|mixpanel|amplitude|"
                r"google-analytics|googletagmanager|gtag\(|sentry\.io|@sentry/|datadoghq|"
                r"plausible\.io|umami|heap\.io|hotjar|telemetry", I), "code"),
    ("netzwerk", "mittel", "Fest eingebauter Analytics-Schlüssel",
     re.compile(r"\bphc_[A-Za-z0-9]{30,}|\bUA-\d{4,}-\d+|\bG-[A-Z0-9]{8,}\b|sentry\.io/\d+|ingest\.sentry"), "code"),
    ("netzwerk", "info", "Netzwerkaufruf im Code",
     re.compile(r"\bfetch\(|axios[.(]|requests\.(get|post|put|delete|request)\(|urllib\.request|"
                r"http\.request\(|https\.request\(|XMLHttpRequest|new WebSocket\(|"
                r"socket\.connect\(|httpx\.|aiohttp\.|got\(|node-fetch|\bcurl\s|\bwget\s"), "code"),
    ("netzwerk", "hoch", "Fest eingetragene IP-Adresse",
     re.compile(r"(?<![\d.])(?!127\.|0\.0\.0\.0|10\.|192\.168\.|255\.|1\.1\.1\.1|8\.8\.[48]\.[48])"
                r"(?:\d{1,3}\.){3}\d{1,3}(?::\d{2,5})(?![\d.])"), "code"),

    # --- 3 Rechte / Zugriff auf Zugangsdaten -------------------------------
    ("rechte", "hoch", "Schreibt/liest Claude-Konfiguration",
     re.compile(r"\.claude\.json|\.claude/settings(\.local)?\.json|claude_desktop_config\.json"), "code"),
    ("rechte", "hoch", "Berechtigungen umgehen",
     re.compile(r"dangerously-skip-permissions|bypassPermissions|--yolo\b|--full-auto\b|"
                r"--dangerously-bypass|approval[_-]?policy[\"']?\s*[:=]\s*[\"']?never|"
                r"\"defaultMode\"\s*:\s*\"(bypassPermissions|acceptEdits)\"", I), "alle"),
    ("rechte", "hoch", "Shell-Profil verändern",
     re.compile(r"\.(zshrc|bashrc|bash_profile|zprofile|profile)\b.*(>>|write|append|open\()|"
                r"(>>|echo).*\.(zshrc|bashrc|bash_profile|zprofile)", I), "code"),
    ("rechte", "hoch", "Zugriff auf Schlüssel/Zugangsdaten-Dateien",
     re.compile(r"\.ssh/|id_rsa|id_ed25519|\.aws/credentials|(~|HOME|homedir\(\)[^\n]{0,20})/?\.npmrc|\.pypirc|\.netrc|"
                r"\.git-credentials|\.docker/config\.json|\.kube/config|gcloud/credentials"), "code"),
    ("rechte", "hoch", "Schlüsselbund / Browserdaten / Krypto-Wallets",
     re.compile(r"security\s+(find|dump)-(generic|internet)-password|dump-keychain|Keychains/|"
                r"[\"'/]Login Data[\"']|Cookies\.binarycookies|Application Support/(Google/Chrome|BraveSoftware|Firefox|"
                r"Exodus|Electrum|com\.bitcoin)|[\"'/]Local State[\"']|wallet\.dat|(?i:metamask)"), "code"),
    ("rechte", "mittel", "Liest alle Umgebungsvariablen",
     re.compile(r"Object\.(keys|entries)\(process\.env\)|JSON\.stringify\(process\.env|"
                r"dict\(os\.environ\)|os\.environ\.copy\(\)|os\.environ\.items\(\)|\bprintenv\b|\benv\s*\|"), "code"),
    ("rechte", "mittel", "sudo / Systemverzeichnisse / chmod 777",
     re.compile(r"\bsudo\s|chmod\s+(-R\s+)?777|/etc/(hosts|sudoers|passwd|shadow)|/usr/local/bin/|"
                r"/Library/(LaunchDaemons|Preferences|Extensions|PrivilegedHelperTools)"), "code"),

    ("rechte", "info", "Fest eingetragener fremder Benutzerpfad",
     re.compile(r"/(Users|home)/(?!(user|username|you|me|runner|name|<[^>]+>|\$\w+|\{)\b)[a-z][\w.-]{2,}/"), "code"),

    # --- 4 Lieferkette ------------------------------------------------------
    ("lieferkette", "hoch", "Skript aus dem Netz direkt ausgeführt (curl | sh)",
     re.compile(r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(\w+=\S*\s+)*(ba|z)?sh\b|iwr[^\n|]*\|\s*iex|"
                r"Invoke-WebRequest[^\n|]*\|\s*Invoke-Expression|irm[^\n|]*\|\s*iex", I), "alle"),
    ("lieferkette", "mittel", "Unversionierter Paketaufruf (@latest / npx -y ohne Version)",
     re.compile(r"(npx|bunx|pnpx|pnpm\s+dlx|yarn\s+dlx)\s+(-y\s+|--yes\s+)?[@\w./-]+@latest|"
                r"(uvx|pipx\s+run)\s+[\w.-]+(?!==)\s|go\s+install\s+\S+@latest", I), "alle"),
    ("lieferkette", "info", "npx/uvx-Aufruf (Version prüfen)",
     re.compile(r"\b(npx|bunx|uvx)\s+(-y\s+|--yes\s+)?(@?[\w.-]+(/[\w.-]+)?)"), "alle"),
    ("lieferkette", "mittel", "Installation direkt aus Git/URL",
     re.compile(r"pip3?\s+install\s+[^\n]*(git\+|https?://)|npm\s+i(nstall)?\s+[^\n]*(github:|git\+|https?://)", I), "alle"),

    # --- 5 Secrets (Werte werden im Bericht maskiert) ----------------------
    ("secrets", "hoch", "Anthropic/OpenAI-Schlüssel",
     re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|sk-(proj-)?[A-Za-z0-9]{32,}"), "alle"),
    ("secrets", "hoch", "GitHub-Token",
     re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}"), "alle"),
    ("secrets", "hoch", "AWS-Schlüssel", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "alle"),
    ("secrets", "hoch", "Slack/Stripe/Google-Schlüssel",
     re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}|(sk|rk)_live_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{35}"), "alle"),
    ("secrets", "hoch", "SendGrid/Mailgun/Slack-Webhook",
     re.compile(r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}|\bkey-[0-9a-zA-Z]{32}\b|"
                r"hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+"), "alle"),
    ("secrets", "hoch", "Datenbank-/URL-Zugang mit Passwort",
     re.compile(r"(postgres(ql)?|mysql|mongodb(\+srv)?|redis|amqp)://[^\s:/'\"]+:[^\s@/'\"]{6,}@[^\s'\"]+", I), "alle"),
    ("secrets", "mittel", "JWT-Token im Klartext",
     re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "alle"),
    ("secrets", "hoch", "Privater Schlüssel im Repo",
     re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"), "alle"),
    ("secrets", "mittel", "Möglicher Klartext-Schlüssel",
     re.compile(r"(api[_-]?key|secret|token|passw(or)?d|auth)[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_\-+/=.]{16,})[\"']", I), "code"),

    # --- 6 Schadcode / Verschleierung --------------------------------------
    ("schadcode", "hoch", "Verschleierter Code wird ausgeführt",
     re.compile(r"eval\s*\(\s*(atob|Buffer\.from|unescape|decodeURIComponent|String\.fromCharCode)|"
                r"new\s+Function\s*\(\s*(atob|Buffer\.from)|"
                r"exec\s*\(\s*(base64\.b64decode|zlib\.decompress|marshal\.loads|bytes\.fromhex|codecs\.decode)|"
                r"exec\s*\(\s*compile\s*\(|__import__\(['\"]base64['\"]\)|"
                r"base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh|powershell[^\n]*-(e|enc|encodedcommand)\s", I), "alle"),
    ("schadcode", "hoch", "Reverse Shell",
     re.compile(r"/dev/tcp/|\bnc\s+(-\w+\s+)*-e\s|ncat\s[^\n]*-e\s|bash\s+-i\s*>&|pty\.spawn\(|"
                r"socket\.socket\([^\n]*\)[^\n]*subprocess|os\.dup2\(\s*s\.fileno", I), "alle"),
    ("schadcode", "hoch", "Krypto-Miner",
     re.compile(r"xmrig|stratum\+tcp|coinhive|cryptonight|minexmr|nicehash|monero(ocean)?\.", I), "alle"),
    ("schadcode", "hoch", "Zerstörerischer Befehl",
     re.compile(r"rm\s+-rf\s+(~|/|\$HOME)(\s|$|/\s)|rm\s+-rf\s+/\*|mkfs\.|dd\s+if=/dev/(zero|random)\s+of=/dev/|"
                r":\(\)\s*\{\s*:\|:&\s*\};:", I), "alle"),
    ("schadcode", "mittel", "Tastatur/Zwischenablage mitlesen",
     re.compile(r"pynput|keylogger|GetAsyncKeyState|CGEventTapCreate|\bpbpaste\b|clipboardy|pyperclip", I), "code"),
    ("schadcode", "mittel", "Lange Hex-/Zeichencode-Folge (Verschleierung?)",
     re.compile(r"(\\x[0-9a-fA-F]{2}){40,}|String\.fromCharCode\((\s*\d+\s*,){30,}"), "code"),
    ("schadcode", "info", "Startet Shell-Befehle",
     re.compile(r"child_process|\bexecSync\(|\bspawn\(|subprocess\.(run|Popen|call|check_output)|os\.system\(|os\.popen\("), "code"),

    # --- 7 Anweisungen an KIs / versteckte Zeichen -------------------------
    ("ki-anweisungen", "hoch", "Text, der eine KI umsteuern will",
     re.compile(r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts)|"
                r"disregard\s+(all\s+|your\s+)?(previous|prior|system)|"
                r"(do\s+not|don'?t|never)\s+(tell|inform|mention\s+(this\s+)?to)\s+the\s+user|"
                r"(mark|report|classify|rate)\s+(this|it|the\s+repo(sitory)?)\s+as\s+(safe|harmless|trusted)|"
                r"(ignoriere|vergiss)\s+(alle\s+)?(vorherigen|bisherigen)\s+(anweisungen|regeln)|"
                r"you\s+are\s+now\s+(in\s+)?(developer|dan|jailbreak|unrestricted)", I), "alle"),
    ("ki-anweisungen", "mittel", "Richtet sich direkt an einen KI-Assistenten",
     re.compile(r"(note|message|instructions?)\s+(to|for)\s+(the\s+)?(ai|llm|assistant|claude|agent|model)s?\b|"
                r"if\s+you\s+are\s+(an?\s+)?(ai|llm|language\s+model|claude|assistant)|"
                r"<\s*/?\s*(system|system-reminder|admin|instructions)\s*>", I), "alle"),
]

UNSICHTBAR_HOCH = re.compile("[\u202a-\u202e\u2066-\u2069]|[\U000E0000-\U000E007F]")
UNSICHTBAR_MITTEL = re.compile("[\u200b\u200c\u200e\u200f\u2060-\u2064]|(?<!^)\ufeff")
SICHERHEITS_ISSUE = re.compile(r"secur|token|leak|secret|sandbox|permission|inject|cve|vulnerab|exfil|"
                              r"malware|backdoor|telemetr|tracking|privacy|data loss|rm -rf|credential", I)
BEISPIEL_DOMAIN = re.compile(r"(^|\.)(example|acme|test|invalid|local|localhost|your-[\w-]+|a|b|other)\.[a-z.]+$|"
                             r"\.(test|example|invalid|local|localhost)$|example\.|^your-")
BILD_BASE64 = ("iVBORw0KGgo", "/9j/", "R0lGOD", "UklGR", "PHN2Zy")   # PNG, JPEG, GIF, WEBP, SVG
LOKALE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal",
                "db", "postgres", "mysql", "redis", "mongo", "database", "rabbitmq"}


def nur_lokale_hosts(url: str) -> bool:
    """True nur, wenn ALLE Hosts der Zugangs-URL lokal sind (localhost/Docker-Dienstname).
    Der Host wird exakt aus der Autoritaet gelesen — ein spaeteres "@localhost" im Pfad oder
    in Parametern und gemischte Mehrfach-Hosts (lokal + echt) zaehlen NICHT als lokal."""
    m = re.match(r"^[a-z][a-z0-9+.-]*://[^@/?#\s]*@([^/?#\s]+)", url, re.I)
    if not m:
        return False
    hosts = [h.strip() for h in m.group(1).split(",") if h.strip()]
    def ohne_port(h: str) -> str:
        if h.startswith("["):                      # [::1]:5432
            return h[1:h.find("]")] if "]" in h else h
        return h.rsplit(":", 1)[0] if h.count(":") == 1 else h
    return bool(hosts) and all(ohne_port(h).lower() in LOKALE_HOSTS for h in hosts)
LANGES_BASE64 = re.compile(r"[A-Za-z0-9+/]{300,}={0,2}")
URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+\.[A-Za-z]{2,}|localhost)(:\d+)?[^\s'\"<>)\]}`]*")
PLATZHALTER = ("your", "xxx", "example", "placeholder", "changeme", "<", "${", "{{",
               "process.env", "os.environ", "dummy", "fake", "sample", "***", "…", "...",
               "replace", "insert", "todo", "redacted", "0000", "1234", "abcd")
SECRET_KATEGORIE = "secrets"
LIFECYCLE_HOCH = {"preinstall", "install", "postinstall", "preuninstall", "postuninstall"}
LIFECYCLE_MITTEL = {"prepare", "prepublish", "prepack", "postpack"}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
# Nur diese Umgebungsvariablen bekommen git/npm mit — keine Tokens oder Schlüssel.
# Only these environment variables are passed to git/npm — no tokens or keys.
BASIS_ENV = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
             "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
             "https_proxy", "http_proxy", "no_proxy")
# gh darf zusätzlich seine eigene GitHub-Anmeldung sehen (Token geht nur an GitHub selbst).
# gh may additionally see its own GitHub login (the token only goes to GitHub itself).
GH_ENV = ("GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "GH_CONFIG_DIR", "XDG_CONFIG_HOME")


def sh(cmd: list[str], timeout: int = 60, env: dict | None = None) -> tuple[int, str, str]:
    erlaubt = BASIS_ENV + (GH_ENV if cmd and cmd[0] == "gh" else ())
    umgebung = {k: v for k, v in os.environ.items() if k in erlaubt}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**umgebung, **(env or {})})
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", T(f"{cmd[0]} nicht gefunden", f"{cmd[0]} not found")
    except subprocess.TimeoutExpired:
        return 124, "", T("Zeitüberschreitung", "timeout")


def parse_github(url: str) -> tuple[str, str, str | None, str | None]:
    """Gibt (owner, repo, branch, unterpfad) zurück."""
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/#?]+)(?:/(?:tree|blob)/([^/]+)(?:/(.*))?)?", url)
    if not m:
        m2 = re.match(r"^([\w.-]+)/([\w.-]+)$", url)
        if m2:
            return m2.group(1), m2.group(2), None, None
        raise ValueError(T(f"Keine GitHub-Adresse erkannt: {url}", f"Not a GitHub address: {url}"))
    return m.group(1), m.group(2), m.group(3), m.group(4)


def gh_api(pfad: str) -> tuple[object | None, str | None]:
    code, out, err = sh(["gh", "api", pfad, "-H", "Accept: application/vnd.github+json"], timeout=30)
    if code == 0:
        try:
            return json.loads(out), None
        except json.JSONDecodeError:
            return None, T("ungültige Antwort", "invalid response")
    if code == 127:  # gh fehlt → anonym (60 Anfragen/Stunde)
        try:
            req = urllib.request.Request(f"https://api.github.com/{pfad.lstrip('/')}",
                                         headers={"Accept": "application/vnd.github+json",
                                                  "User-Agent": "repo-pruefer"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode()), None
        except Exception as e:  # noqa: BLE001
            return None, str(e)
    return None, (err or out).strip()[:200]


def tage_seit(iso: str | None) -> int | None:
    if not iso:
        return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def maskiere(wert: str) -> str:
    return f"{wert[:4]}…({len(wert)} {T('Zeichen', 'chars')})" if len(wert) > 4 else "…"


def kuerze(zeile: str, n: int = 160) -> str:
    zeile = zeile.strip().replace("|", "\\|")
    return zeile if len(zeile) <= n else zeile[:n] + " …"


# ---------------------------------------------------------------------------
# Metadaten
# ---------------------------------------------------------------------------
def metadaten(owner: str, repo: str) -> dict:
    meta: dict = {"owner": owner, "repo": repo}
    r, fehler = gh_api(f"repos/{owner}/{repo}")
    if not isinstance(r, dict):
        meta["fehler"] = fehler
        return meta
    meta.update({
        "beschreibung": r.get("description"),
        "homepage": r.get("homepage"),
        "sterne": r.get("stargazers_count"),
        "forks": r.get("forks_count"),
        "offene_issues": r.get("open_issues_count"),
        "lizenz": (r.get("license") or {}).get("spdx_id"),
        "sprache": r.get("language"),
        "erstellt": r.get("created_at"),
        "gepusht": r.get("pushed_at"),
        "groesse_kb": r.get("size"),
        "archiviert": r.get("archived"),
        "ist_fork": r.get("fork"),
        "fork_von": (r.get("parent") or {}).get("full_name"),
        "standard_branch": r.get("default_branch"),
        "besitzer_typ": (r.get("owner") or {}).get("type"),
        "themen": r.get("topics"),
    })
    c, _ = gh_api(f"repos/{owner}/{repo}/contributors?per_page=100")
    if isinstance(c, list) and c:
        gesamt = sum(x.get("contributions", 0) for x in c)
        top = c[0]
        meta["mitwirkende"] = f"{len(c)}{'+' if len(c) == 100 else ''}"
        meta["hauptentwickler"] = f"{top.get('login')} ({top.get('contributions')} commits, " \
                                  f"{round(100 * top.get('contributions', 0) / max(gesamt, 1))} %)"
    rel, _ = gh_api(f"repos/{owner}/{repo}/releases/latest")
    if isinstance(rel, dict) and rel.get("tag_name"):
        meta["letztes_release"] = f"{rel.get('tag_name')} ({(rel.get('published_at') or '')[:10]})"
    commits, _ = gh_api(f"repos/{owner}/{repo}/commits?per_page=3")
    if isinstance(commits, list):
        meta["letzte_commits"] = [
            f"{(c.get('commit', {}).get('author', {}).get('date') or '')[:10]} · "
            f"{(c.get('commit', {}).get('message') or '').splitlines()[0][:80]}" for c in commits]
    issues, _ = gh_api(f"repos/{owner}/{repo}/issues?state=open&per_page=100")
    if isinstance(issues, list):
        treffer = [f"#{i.get('number')} {i.get('title')}" for i in issues
                   if "pull_request" not in i and SICHERHEITS_ISSUE.search(i.get("title") or "")]
        meta["sicherheits_issues"] = treffer[:8]
    if meta.get("besitzer_typ") == "Organization":
        org, _ = gh_api(f"orgs/{owner}")
        if isinstance(org, dict):
            meta["organisation"] = {k: org.get(k) for k in ("name", "blog", "location", "is_verified")}
    return meta


# ---------------------------------------------------------------------------
# Klonen (sicher)
# ---------------------------------------------------------------------------
def klonen(owner: str, repo: str, branch: str | None, ziel: Path) -> tuple[Path, str | None]:
    ziel.mkdir(parents=True, exist_ok=True)
    dest = ziel / f"{owner}__{repo}"
    if dest.exists():
        shutil.rmtree(dest)
    sicher = [
        "-c", "core.hooksPath=/dev/null", "-c", "core.symlinks=false",
        "-c", "core.fsmonitor=false", "-c", "protocol.file.allow=never",
        "-c", "protocol.ext.allow=never", "-c", "filter.lfs.smudge=",
        "-c", "filter.lfs.process=", "-c", "filter.lfs.required=false",
        "-c", "submodule.recurse=false",
    ]
    env = {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GIT_CONFIG_NOSYSTEM": "1"}
    basis = ["git", *sicher, "clone", "--depth", "1", "--no-recurse-submodules", "--single-branch"]
    url = f"https://github.com/{owner}/{repo}.git"
    cmd = basis + (["--branch", branch] if branch else []) + [url, str(dest)]
    code, _, err = sh(cmd, timeout=600, env=env)
    if code != 0 and branch:  # Branch mit Schrägstrich o. ä. → Standardbranch
        code, _, err = sh(basis + [url, str(dest)], timeout=600, env=env)
    if code != 0:
        raise RuntimeError(T("Klonen fehlgeschlagen: ", "Clone failed: ") + err.strip()[:300])
    _, commit, _ = sh(["git", "-C", str(dest), "rev-parse", "HEAD"])
    return dest, commit.strip() or None


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------
TEST_PFAD = re.compile(r"(^|/)(tests?|__tests__|spec|fixtures?|__mocks__|testdata)/|[._-](test|spec)\.[a-z]+$", I)
NIE_ABSTUFEN = {"schadcode", "ki-anweisungen"}   # Schadcode versteckt sich gern in Testordnern
ABSTUFUNG = {"hoch": "mittel", "mittel": "info", "info": "info"}


class Befunde:
    def __init__(self) -> None:
        self.treffer: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self.anzahl: Counter = Counter()
        self.dateien: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    def add(self, kat: str, stufe: str, titel: str, ort: str, text: str) -> None:
        datei = ort.split(":")[0]
        if kat not in NIE_ABSTUFEN and TEST_PFAD.search(datei):
            stufe, titel = ABSTUFUNG[stufe], f"{titel} (in Test-/Beispieldatei)"
        key = (kat, stufe, titel)
        self.anzahl[key] += 1
        neu = datei not in self.dateien[key]
        self.dateien[key].add(datei)
        if neu and len(self.treffer[key]) < MAX_TREFFER_PRO_REGEL:   # ein Beispiel je Datei
            self.treffer[key].append(f"`{ort}` — {text}")

    def stufen(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for kat, stufe, _ in self.anzahl:
            out[stufe].add(kat)
        return out


def ist_binaer(pfad: Path) -> str | None:
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(8)
    except OSError:
        return None
    for magic, name in BINAER_MAGIC.items():
        if kopf.startswith(magic):
            if magic == b"MZ" and pfad.suffix.lower() not in BINAER_EXT:
                continue  # "MZ" ist zu kurz für Textdateien
            return name
    return None


def bereich_von(pfad: Path, text_kopf: str) -> str:
    ext = pfad.suffix.lower()
    if ext in DOC_EXT:
        return "doku"
    if ext in CODE_EXT or text_kopf.startswith("#!") or pfad.name in {"Makefile", "Dockerfile", "Justfile"}:
        return "code"
    return "doku" if ext == "" else "code"


def scan(wurzel: Path, unterpfad: str | None) -> dict:
    basis = wurzel / unterpfad if unterpfad and (wurzel / unterpfad).exists() else wurzel
    b = Befunde()
    inventar: dict = {
        "dateien": 0, "bytes": 0, "endungen": Counter(), "skills": [], "agenten": [],
        "befehle": [], "plugins": [], "marktplaetze": [], "hooks": [], "mcp": [],
        "claude_settings": [], "package_json": [], "npx_pakete": set(), "uvx_pakete": set(), "grosse_dateien": [],
        "binaer": [], "archive": [], "env_dateien": [], "domains_code": Counter(),
        "domains_doku": Counter(), "lizenzdatei": None, "workflows": [], "readme": None,
    }
    for pfad in sorted(basis.rglob("*")):
        if ".git" in pfad.relative_to(wurzel).parts or not pfad.is_file() or pfad.is_symlink():
            continue
        rel = str(pfad.relative_to(wurzel))
        groesse = pfad.stat().st_size
        inventar["dateien"] += 1
        inventar["bytes"] += groesse
        ext = pfad.suffix.lower()
        inventar["endungen"][ext or "(ohne)"] += 1
        name = pfad.name

        # Inventar für Claude-Bausteine
        if name == "SKILL.md":
            inventar["skills"].append(rel)
        elif "/agents/" in f"/{rel}" and ext == ".md":
            inventar["agenten"].append(rel)
        elif "/commands/" in f"/{rel}" and ext == ".md":
            inventar["befehle"].append(rel)
        if name == "plugin.json":
            inventar["plugins"].append(rel)
        if name == "marketplace.json":
            inventar["marktplaetze"].append(rel)
        if name.upper().startswith(("LICENSE", "COPYING")):
            if pfad.parent == basis or inventar["lizenzdatei"] is None:
                inventar["lizenzdatei"] = rel if pfad.parent == basis else \
                    f"{rel} {T('(nur Unterordner!)', '(subfolder only!)')}"
        if name.lower().startswith("readme") and inventar["readme"] is None and pfad.parent == basis:
            inventar["readme"] = rel
        if rel.startswith(".github/workflows/"):
            inventar["workflows"].append(rel)
        if name == ".env" or (name.startswith(".env") and not any(
                s in name for s in ("example", "sample", "template", "dist"))):
            inventar["env_dateien"].append(rel)
            b.add("secrets", "hoch", "Echte .env-Datei im Repo", rel,
                  T("Datei mitgeliefert — Inhalt prüfen", "file is shipped — check its contents"))

        if ext in BINAER_EXT or ist_binaer(pfad):
            art = T(ist_binaer(pfad) or ext)
            inventar["binaer"].append(f"{rel} ({art}, {groesse // 1024} KB)")
            b.add("schadcode", "mittel", "Ausführbare Binärdatei im Repo", rel, art)
            continue
        if ext in ARCHIV_EXT:
            inventar["archive"].append(f"{rel} ({groesse // 1024} KB)")
            b.add("schadcode", "mittel", "Archiv im Repo (Inhalt ungeprüft)", rel, f"{groesse // 1024} KB")
            continue
        if groesse > MAX_TEXT_BYTES:
            inventar["grosse_dateien"].append(f"{rel} ({groesse // 1024} KB)")
            continue
        try:
            roh = pfad.read_bytes()
            if b"\x00" in roh[:4096]:
                continue  # Bild, Schrift o. ä.
            text = roh.decode("utf-8", errors="replace")
        except OSError:
            continue

        bereich = bereich_von(pfad, text[:2])
        ist_lock = name in LOCKFILES

        # Strukturierte Dateien
        if name == "package.json":
            pruefe_package_json(rel, text, b, inventar)
        if name in {"hooks.json", "settings.json", "settings.local.json", "plugin.json"} or \
                rel.endswith(".claude/settings.json"):
            pruefe_claude_json(rel, text, b, inventar)
        if name in {".mcp.json", "mcp.json", "claude_desktop_config.json"} or name.endswith(".mcp.json"):
            pruefe_mcp_json(rel, text, b, inventar)
        if name == "setup.py" and re.search(r"cmdclass|class\s+\w+\((install|develop|build_py)\)", text):
            b.add("autostart", "mittel", "setup.py mit eigenem Installationsschritt", rel,
                  T("Code läuft bei `pip install`", "code runs on `pip install`"))
        if ext in {".plist", ".service"} or name in {"crontab", ".pre-commit-config.yaml"} or \
                rel.startswith(".husky/"):
            b.add("autostart", "info", "Autostart-/Hook-Datei vorhanden", rel, T("Datei lesen", "read this file"))

        if ist_lock:
            continue

        # Zeilenweise Regeln
        for nr, zeile in enumerate(text.splitlines(), 1):
            if len(zeile) > 5000:
                if ext in {".js", ".mjs", ".cjs", ".py"} and ".min." not in name:
                    b.add("schadcode", "mittel", "Extrem lange Codezeile (verschleiert/minifiziert?)",
                          f"{rel}:{nr}", f"{len(zeile)} {T('Zeichen', 'chars')}")
                zeile = zeile[:5000]
            for kat, stufe, titel, muster, geltung in REGELN:
                if geltung != "alle" and geltung != bereich:
                    continue
                m = muster.search(zeile)
                if not m:
                    continue
                if kat == SECRET_KATEGORIE:
                    _stufe_orig, _titel_orig = stufe, titel
                    generisch = titel.startswith("Möglicher")
                    wert = m.group(m.lastindex) if generisch and m.lastindex else m.group(0)
                    # Eindeutige Formate (sk-ant-, ghp_, AKIA …) nur bei offensichtlichen Platzhaltern
                    # verwerfen; die generische Regel braucht den strengen Filter.
                    filter_ = PLATZHALTER if generisch else ("xxxx", "your", "example", "<", "...", "…")
                    if any(p in wert.lower() for p in filter_) or len(set(wert)) < 6:
                        continue
                    if titel.startswith("Datenbank") and nur_lokale_hosts(wert):
                        # Entwicklungs-DB auf localhost/Docker: Beispielwert, kein echter Zugang
                        stufe, titel = "info", "Lokaler Datenbank-Zugang (Entwicklung)"
                    b.add(kat, stufe, titel, f"{rel}:{nr}", f"{T('Wert maskiert', 'value masked')}: {maskiere(wert)}")
                    stufe, titel = _stufe_orig, _titel_orig
                else:
                    b.add(kat, stufe, titel, f"{rel}:{nr}", kuerze(zeile))
                if titel.startswith("npx/uvx"):
                    paket = m.group(3)
                    if paket and m.group(1) == "uvx" and not paket.startswith("-"):
                        inventar["uvx_pakete"].add(re.sub(r"[@=<>].*$", "", paket))
                    elif paket and not paket.startswith("-") and paket not in {"skills", "create"}:
                        inventar["npx_pakete"].add(re.sub(r"@[\w.^~-]*$", "", paket) if not paket.startswith("@")
                                                   else re.sub(r"(?<=.)@[\w.^~-]*$", "", paket))
            if UNSICHTBAR_HOCH.search(zeile):
                b.add("ki-anweisungen", "hoch", "Unsichtbare Steuerzeichen (Bidi/Tag-Zeichen)",
                      f"{rel}:{nr}", T("Text wird anders angezeigt, als er gelesen wird",
                                       "text is displayed differently from how it is read"))
            elif bereich == "code" and UNSICHTBAR_MITTEL.search(zeile):
                b.add("ki-anweisungen", "mittel", "Unsichtbare Zeichen im Code", f"{rel}:{nr}", kuerze(repr(zeile), 120))
            b64 = LANGES_BASE64.search(zeile) if bereich == "code" and ext not in {".svg", ".css", ".map"} \
                and "data:" not in zeile else None
            if b64 and not b64.group(0).startswith(BILD_BASE64):
                b.add("schadcode", "mittel", "Lange Base64-Folge im Code", f"{rel}:{nr}",
                      f"{len(b64.group(0))} {T('Zeichen', 'chars')}")
            for um in URL_RE.finditer(zeile):
                dom = um.group(1).lower()
                if dom in HARMLOSE_DOMAINS or BEISPIEL_DOMAIN.search(dom):
                    continue
                (inventar["domains_code"] if bereich == "code" else inventar["domains_doku"])[dom] += 1

    inventar["npx_pakete"] = sorted(inventar["npx_pakete"])
    inventar["uvx_pakete"] = sorted(inventar["uvx_pakete"])
    return {"befunde": b, "inventar": inventar, "basis": str(basis)}


def pruefe_package_json(rel: str, text: str, b: Befunde, inv: dict) -> None:
    try:
        pj = json.loads(text)
    except json.JSONDecodeError as e:
        b.add("rechte", "info", "Ungültiges JSON", rel, str(e))
        return
    if not isinstance(pj, dict):
        return
    inv["package_json"].append({"datei": rel, "name": pj.get("name"), "version": pj.get("version"),
                                "privat": pj.get("private", False),
                                "abhaengigkeiten": len(pj.get("dependencies") or {}),
                                "dev": len(pj.get("devDependencies") or {}),
                                "bin": list((pj.get("bin") or {}).keys()) if isinstance(pj.get("bin"), dict) else pj.get("bin")})
    for k, v in (pj.get("scripts") or {}).items():
        if k in LIFECYCLE_HOCH:
            b.add("autostart", "hoch", "npm-Lebenszyklus-Skript (läuft bei npm install)", rel, f"`{k}`: {kuerze(str(v))}")
        elif k in LIFECYCLE_MITTEL:
            b.add("autostart", "mittel", "npm-Skript (läuft bei Installation aus Git)", rel, f"`{k}`: {kuerze(str(v))}")
    for feld in ("dependencies", "optionalDependencies", "peerDependencies"):
        for dep, ver in (pj.get(feld) or {}).items():
            v = str(ver)
            if v in {"*", "latest", ""} or v.startswith(("git", "http", "github:", "file:")) or \
                    re.match(r"^[\w-]+/[\w.-]+(#.*)?$", v):
                b.add("lieferkette", "mittel", "Abhängigkeit ohne feste Version / aus Git/URL",
                      rel, f"{dep}: {v}")


def _sammle_befehle(obj, pfad: str = "") -> list[tuple[str, str]]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "command" and isinstance(v, str):
                out.append((pfad, v))
            else:
                out += _sammle_befehle(v, f"{pfad}.{k}" if pfad else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _sammle_befehle(v, pfad)
    return out


def pruefe_claude_json(rel: str, text: str, b: Befunde, inv: dict) -> None:
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        if rel.endswith(("hooks.json", "plugin.json", ".claude/settings.json")):
            b.add("rechte", "mittel", "Ungültiges JSON in Claude-Konfiguration", rel, str(e))
        return
    if not isinstance(d, dict):
        return
    hooks = d.get("hooks")
    if isinstance(hooks, dict):
        if not hooks:
            inv["hooks"].append(f"{rel}: {T('leer (Platzhalter)', 'empty (placeholder)')}")
        for ereignis, eintraege in hooks.items():
            for _, cmd in _sammle_befehle(eintraege):
                inv["hooks"].append(f"{rel}: {ereignis} → {kuerze(cmd, 140)}")
                b.add("autostart", "hoch", "Claude-Hook (läuft automatisch bei Ereignis)", rel,
                      f"{ereignis} → {kuerze(cmd, 120)}")
    elif isinstance(hooks, str):
        inv["hooks"].append(f"{rel}: {T('verweist auf', 'points to')} {hooks}")
    perms = d.get("permissions")
    if isinstance(perms, dict):
        allow = perms.get("allow") or []
        inv["claude_settings"].append(f"{rel}: allow={allow} defaultMode={perms.get('defaultMode')}")
        for eintrag in allow:
            stufe = "hoch" if re.search(r"Bash\((\*|.*:\*)\)|Bash$|railway|rm |git push|curl|npm publish", str(eintrag)) else "mittel"
            b.add("rechte", stufe, "Automatische Freigabe von Werkzeugen", rel, str(eintrag))
    if isinstance(d.get("mcpServers"), dict):
        pruefe_mcp_json(rel, json.dumps({"mcpServers": d["mcpServers"]}), b, inv)
    if "env" in d and isinstance(d["env"], dict) and rel.endswith("settings.json"):
        inv["claude_settings"].append(f"{rel}: {T('setzt env', 'sets env')} {list(d['env'].keys())}")


def pruefe_mcp_json(rel: str, text: str, b: Befunde, inv: dict) -> None:
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        b.add("rechte", "mittel", "Ungültiges JSON in MCP-Konfiguration", rel, str(e))
        inv["mcp"].append(f"{rel}: {T('UNGÜLTIGES JSON', 'INVALID JSON')} ({e})")
        return
    server = d.get("mcpServers", d) if isinstance(d, dict) else {}
    if not isinstance(server, dict):
        return
    for name, cfg in server.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("url"):
            inv["mcp"].append(f"{rel}: {name} → {T('GEHOSTET', 'HOSTED')} {cfg['url']}")
            b.add("netzwerk", "mittel", "Gehosteter MCP-Server (Daten gehen an Fremdserver)", rel,
                  f"{name} → {cfg['url']}")
        else:
            befehl = " ".join([str(cfg.get("command", ""))] + [str(a) for a in cfg.get("args", [])])
            inv["mcp"].append(f"{rel}: {name} → {T('lokal', 'local')} `{kuerze(befehl, 120)}`")
            if re.search(r"@latest|-y\s", befehl):
                b.add("lieferkette", "mittel", "MCP-Server startet unversioniertes Paket", rel, kuerze(befehl))
        if cfg.get("env"):
            inv["mcp"].append(f"    {T('verlangt env', 'requires env')}: {list(cfg['env'].keys())}")


# ---------------------------------------------------------------------------
# npm-Prüfung (Maintainer, Alter) — nur lesen, installiert nichts
# ---------------------------------------------------------------------------
def npm_check(pakete: list[str]) -> list[str]:
    zeilen = []
    for p in pakete[:10]:
        code, out, _ = sh(["npm", "view", p, "name", "version", "maintainers", "time.modified",
                           "time.created", "repository.url", "--json"], timeout=25)
        if code != 0:
            zeilen.append(f"- `{p}`: " + T("nicht auf npm gefunden — lokales Skript, geplantes Paket oder "
                                           "Tippfehler-/Namensklau-Gefahr (wer den Namen registriert, liefert den Code)",
                                           "not found on npm — local script, planned package, or typosquatting/"
                                           "name-squatting risk (whoever registers the name ships the code)"))
            continue
        try:
            d = json.loads(out)
        except json.JSONDecodeError:
            continue
        m = d.get("maintainers") or []
        m = m if isinstance(m, list) else [m]
        warn = T(" ⚠️ nur 1 Maintainer", " ⚠️ single maintainer") if len(m) == 1 else ""
        try:
            with urllib.request.urlopen(f"https://api.npmjs.org/downloads/point/last-week/{p}", timeout=10) as r:
                dl = json.loads(r.read().decode()).get("downloads")
            if isinstance(dl, int):
                warn += T(f" · {dl:,} Downloads/Woche".replace(",", "."), f" · {dl:,} downloads/week")
        except Exception:  # noqa: BLE001
            pass
        zeilen.append(f"- `{p}` v{d.get('version')} · {len(m)} maintainer{warn} · {T('erstellt', 'created')} "
                      f"{str(d.get('time.created', ''))[:10]} · {T('geändert', 'modified')} "
                      f"{str(d.get('time.modified', ''))[:10]} · {T('Quelle', 'source')} {d.get('repository.url', '—')}")
    return zeilen


def pypi_check(pakete: list[str]) -> list[str]:
    """uvx/pipx-Pakete kommen von PyPI, nicht von npm — nur lesend abfragen."""
    zeilen = []
    for p in pakete[:10]:
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{p}/json", timeout=15) as r:
                d = json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            zeilen.append(f"- `{p}` (PyPI): " + T("nicht gefunden — Tippfehler-/Namensklau-Gefahr prüfen",
                                                   "not found — check for typosquatting/name-squatting"))
            continue
        info, rel = d.get("info", {}), d.get("releases", {})
        up = (rel.get(info.get("version")) or [{}])[0].get("upload_time", "")[:10]
        quelle = (info.get("project_urls") or {}).get("Source") or info.get("home_page") or "—"
        zeilen.append(f"- `{p}` (PyPI) v{info.get('version')} {T('vom', 'from')} {up} · {len(rel)} releases · "
                      f"{T('Quelle', 'source')} {quelle}")
    return zeilen


# ---------------------------------------------------------------------------
# Vorläufige Einstufung
# ---------------------------------------------------------------------------
KAT_KURZ_EN = {"autostart": "autostart", "netzwerk": "network", "rechte": "permissions",
               "lieferkette": "supply chain", "secrets": "secrets", "schadcode": "malware",
               "ki-anweisungen": "AI instructions"}


def _kats(kategorien: set[str]) -> str:
    return ", ".join(sorted(KAT_KURZ_EN.get(k, k) if LANG == "en" else k for k in kategorien))


def vorlaeufige_einstufung(befunde: Befunde, meta: dict) -> tuple[str, list[str]]:
    """Automatische Vor-Ampel. Das endgültige Urteil trifft Claude nach dem Lesen
    der Fundstellen — Muster finden auch Harmloses (z. B. `fetch(` in einer Doku-Demo).

    Rückgabe: (stufe, gründe) mit stufe ∈ {"unbedenklich", "mit Einstellung nutzbar", "Vorsicht"}
    """
    s = befunde.stufen()
    gruende: list[str] = []
    if {"schadcode", "ki-anweisungen"} & s.get("hoch", set()):
        gruende.append(T("Schadcode- oder KI-Manipulationsmuster gefunden", "malware or AI-manipulation patterns found"))
        return "Vorsicht", gruende
    if "secrets" in s.get("hoch", set()):
        gruende.append(T("echte Zugangsdaten im Repo (schlampig oder absichtlich)",
                         "real credentials in the repo (careless or deliberate)"))
    hoch_rest = s.get("hoch", set()) - {"secrets"}
    if hoch_rest:
        gruende.append(T("hohe Befunde in: ", "high findings in: ") + _kats(hoch_rest))
    if meta.get("archiviert"):
        gruende.append(T("Repo ist archiviert (keine Pflege mehr)", "repo is archived (no longer maintained)"))
    tage = tage_seit(meta.get("gepusht"))
    if tage is not None and tage > 365:
        gruende.append(T(f"seit {tage} Tagen kein Push", f"no push for {tage} days"))
    alter = tage_seit(meta.get("erstellt"))
    if alter is not None and alter < 30 and (meta.get("sterne") or 0) > 1000:
        gruende.append(T("sehr jung, aber viele Sterne (gekaufte Sterne möglich)",
                         "very young but many stars (bought stars possible)"))
    if gruende:
        return "mit Einstellung nutzbar", gruende
    if s.get("mittel"):
        return "mit Einstellung nutzbar", [T("mittlere Befunde in: ", "medium findings in: ") + _kats(s["mittel"])]
    return "unbedenklich", [T("keine auffälligen Muster", "no suspicious patterns")]


# ---------------------------------------------------------------------------
# Bericht
# ---------------------------------------------------------------------------
KAT_TITEL_EN = {
    "autostart": "1 · What starts automatically?",
    "netzwerk": "2 · What leaves the machine?",
    "rechte": "3 · What permissions does it take?",
    "lieferkette": "4 · Supply chain",
    "secrets": "5 · Secrets",
    "schadcode": "Malware / obfuscation",
    "ki-anweisungen": "Instructions to AIs / hidden characters",
}
KAT_TITEL = {
    "autostart": "1 · Was startet automatisch?",
    "netzwerk": "2 · Was verlässt den Rechner?",
    "rechte": "3 · Welche Rechte nimmt es sich?",
    "lieferkette": "4 · Lieferkette",
    "secrets": "5 · Secrets",
    "schadcode": "Schadcode / Verschleierung",
    "ki-anweisungen": "Anweisungen an KIs / versteckte Zeichen",
}
STUFE_ORDNUNG = {"hoch": 0, "mittel": 1, "info": 2}
STUFE_ICON = {"hoch": "🔴", "mittel": "🟡", "info": "⚪"}


def bericht(meta: dict, erg: dict, commit: str | None, klon: str, npm: list[str]) -> str:
    b: Befunde = erg["befunde"]
    inv = erg["inventar"]
    L: list[str] = []
    titel = f"{meta.get('owner')}/{meta.get('repo')}" if meta.get("owner") else klon
    L.append(f"# Scan: {titel}")
    L.append(f"{T('Klon', 'Clone')}: `{klon}` · Commit `{(commit or '?')[:12]}` · "
             f"{T('Stand', 'As of')} {datetime.now():{'%d.%m.%Y %H:%M' if LANG != 'en' else '%Y-%m-%d %H:%M'}}")
    L.append("")
    tage = T("vor {n} Tagen", "{n} days ago")
    if meta.get("fehler"):
        L.append(f"⚠️ {T('Metadaten nicht abrufbar', 'metadata unavailable')}: {meta['fehler']}")
    elif meta.get("owner"):
        L.append(T("## Steckbrief (GitHub)", "## Profile (GitHub)"))
        lizenz = meta.get("lizenz") if meta.get("lizenz") not in (None, "NOASSERTION") else \
            f"{meta.get('lizenz') or T('KEINE', 'NONE')} — " + T("ohne klare Lizenz: anschauen ja, Code kopieren nein",
                                                           "no clear license: look yes, copy code no")
        felder = [
            (T("Beschreibung", "Description"), meta.get("beschreibung")), (T("Webseite", "Website"), meta.get("homepage")),
            (T("Besitzer", "Owner"), f"{meta.get('owner')} ({meta.get('besitzer_typ')})"),
            (T("Organisation", "Organization"), meta.get("organisation")),
            (T("Sterne / Forks", "Stars / forks"), f"{meta.get('sterne')} / {meta.get('forks')}"),
            (T("Lizenz", "License"), lizenz),
            (T("Sprache", "Language"), meta.get("sprache")),
            (T("Erstellt", "Created"), f"{(meta.get('erstellt') or '')[:10]} ({tage.format(n=tage_seit(meta.get('erstellt')))})"),
            (T("Zuletzt gepusht", "Last push"), f"{(meta.get('gepusht') or '')[:10]} ({tage.format(n=tage_seit(meta.get('gepusht')))})"),
            (T("Letztes Release", "Latest release"), meta.get("letztes_release") or T("keins", "none")),
            (T("Mitwirkende", "Contributors"), meta.get("mitwirkende")),
            (T("Hauptentwickler", "Main developer"), meta.get("hauptentwickler")),
            (T("Offene Issues", "Open issues"), meta.get("offene_issues")),
            (T("Größe", "Size"), f"{(meta.get('groesse_kb') or 0) // 1024} MB"),
            (T("Archiviert", "Archived"), T("JA", "YES") if meta.get("archiviert") else T("nein", "no")),
            (T("Fork von", "Fork of"), meta.get("fork_von")),
            (T("Themen", "Topics"), ", ".join(meta.get("themen") or []) or None),
        ]
        for k, v in felder:
            if v not in (None, "", [], {}):
                L.append(f"- **{k}:** {v}")
        if meta.get("letzte_commits"):
            L.append(f"- **{T('Letzte Commits', 'Latest commits')}:** " + " | ".join(meta["letzte_commits"]))
        if meta.get("sicherheits_issues"):
            L.append(f"- **{T('Offene Issues mit Sicherheitsbezug (Titel)', 'Open security-related issues (titles)')}:**")
            L += [f"  - {t}" for t in meta["sicherheits_issues"]]
    L.append("")
    L.append(T("## Inventar", "## Inventory"))
    top_ext = ", ".join(f"{e} {n}" for e, n in inv["endungen"].most_common(8))
    L.append(f"- {inv['dateien']} {T('Dateien', 'files')}, {inv['bytes'] // 1024} KB · {top_ext}")
    L.append(f"- README: `{inv['readme']}` · {T('Lizenzdatei', 'License file')}: `{inv['lizenzdatei']}`")
    for key, name in (("skills", "Skills (SKILL.md)"), ("agenten", T("Agenten", "Agents")),
                      ("befehle", T("Befehle", "Commands")),
                      ("plugins", "plugin.json"), ("marktplaetze", "marketplace.json"),
                      ("workflows", T("GitHub-Workflows (laufen nur bei GitHub, nicht bei dir)",
                                      "GitHub workflows (run on GitHub only, not on your machine)"))):
        if inv[key]:
            beispiele = ", ".join(f"`{x}`" for x in inv[key][:6])
            L.append(f"- **{name}: {len(inv[key])}** — {beispiele}{' …' if len(inv[key]) > 6 else ''}")
    for pj in inv["package_json"][:6]:
        L.append(f"- package.json `{pj['datei']}`: {pj['name']}@{pj['version']} · {pj['abhaengigkeiten']} "
                 f"{T('Abh.', 'deps')} + {pj['dev']} dev{T(' · privat', ' · private') if pj['privat'] else ''}"
                 f"{' · bin: ' + str(pj['bin']) if pj['bin'] else ''}")
    if inv["hooks"]:
        L.append("- **Hooks:**")
        L += [f"  - {h}" for h in inv["hooks"][:20]]
    if inv["mcp"]:
        L.append(f"- **{T('MCP-Server', 'MCP servers')}:**")
        L += [f"  - {m}" for m in inv["mcp"][:20]]
    if inv["claude_settings"]:
        L.append(f"- **{T('Claude-Einstellungen', 'Claude settings')}:**")
        L += [f"  - {c}" for c in inv["claude_settings"][:10]]
    for key, name in (("binaer", T("Binärdateien", "Binaries")), ("archive", T("Archive", "Archives")),
                      ("grosse_dateien", T("Nicht durchsucht (zu groß)", "Not scanned (too large)")),
                      ("env_dateien", T(".env-Dateien", ".env files"))):
        if inv[key]:
            L.append(f"- **{name}:** " + ", ".join(f"`{x}`" for x in inv[key][:10]))
    L.append("")
    L.append(T("## Adressen", "## Addresses"))
    if inv["domains_code"]:
        L.append(T("**Im Code/Konfig** (jede davon ist ein möglicher Datenabfluss — Zweck prüfen):",
                   "**In code/config** (each one is a possible data outflow — check its purpose):"))
        L.append(", ".join(f"`{d}` ×{n}" for d, n in inv["domains_code"].most_common(40)))
    else:
        L.append(T("Im Code/Konfig: keine (außer Standard-Domains).", "In code/config: none (apart from standard domains)."))
    if inv["domains_doku"]:
        L.append("")
        L.append(T("**Nur in Doku:** ", "**Docs only:** ") +
                 ", ".join(f"`{d}`" for d, _ in inv["domains_doku"].most_common(25)))
    L.append("")
    if npm:
        L.append(T("## Pakete, die per npx (npm) / uvx (PyPI) gestartet werden",
                   "## Packages launched via npx (npm) / uvx (PyPI)"))
        L += npm
        L.append("")
    L.append(T("## Befunde nach Prüffragen", "## Findings by question"))
    for kat in KAT_TITEL:
        eintraege = sorted([k for k in b.anzahl if k[0] == kat], key=lambda k: STUFE_ORDNUNG[k[1]])
        L.append(f"### {KAT_TITEL_EN[kat] if LANG == 'en' else KAT_TITEL[kat]}")
        if not eintraege:
            L.append(T("Keine Muster gefunden.", "No patterns found."))
            L.append("")
            continue
        for key in eintraege:
            _, stufe, titel = key
            n_dat = len(b.dateien[key])
            dateiwort = T("Datei" if n_dat == 1 else "Dateien", "file" if n_dat == 1 else "files")
            L.append(f"**{STUFE_ICON[stufe]} {T(titel)}** — {b.anzahl[key]}× {T('in', 'in')} {n_dat} {dateiwort}")
            L += [f"- {t}" for t in b.treffer[key]]
            if n_dat > len(b.treffer[key]):
                L.append(T(f"- … und {n_dat - len(b.treffer[key])} weitere Dateien",
                           f"- … and {n_dat - len(b.treffer[key])} more files"))
        L.append("")
    stufe, gruende = vorlaeufige_einstufung(b, meta)
    L.append(T("## Vorläufige Ampel (automatisch)", "## Preliminary verdict (automatic)"))
    L.append(f"**{T(stufe)}** — {'; '.join(gruende)}")
    L.append("")
    L.append(T("_Automatische Mustersuche. Fundstellen lesen, bevor geurteilt wird — "
               "Frage 6 (tut der Code, was er verspricht?) und 7 (Pflege) beantwortet erst das Lesen._",
               "_Automatic pattern search. Read the findings before judging — question 6 (does the code do "
               "what it promises?) and 7 (maintenance) are only answered by reading._"))
    return "\n".join(L)


def main() -> None:
    global LANG
    ap = argparse.ArgumentParser(description="Statische Sicherheitsprüfung eines Repos (führt nichts aus). "
                                             "Static security scan of a repo (executes nothing).")
    ap.add_argument("url", nargs="?", help="GitHub-URL oder owner/repo / GitHub URL or owner/repo")
    ap.add_argument("--lokal", "--local", dest="lokal",
                    help="vorhandenen Ordner prüfen statt klonen / scan an existing folder instead of cloning")
    ap.add_argument("--ziel", "--dest", dest="ziel", help="Ordner für den Klon / folder for the clone")
    ap.add_argument("--json", help="Rohdaten zusätzlich als JSON / also write raw data as JSON")
    ap.add_argument("--ohne-npm", "--no-registry", dest="ohne_npm", action="store_true",
                    help="keine npm/PyPI-Abfragen / no npm/PyPI lookups")
    ap.add_argument("--lang", choices=("de", "en"),
                    help="Ausgabesprache / output language (Standard/default: Systemsprache/system locale)")
    a = ap.parse_args()
    systemsprache = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "")
    LANG = a.lang or ("de" if systemsprache.lower().startswith("de") else "en")
    if not a.url and not a.lokal:
        ap.error(T("URL oder --lokal angeben", "give a URL or --local"))

    meta: dict = {}
    commit = None
    unterpfad = None
    if a.lokal:
        wurzel = Path(a.lokal).expanduser().resolve()
        _, c, _ = sh(["git", "-C", str(wurzel), "rev-parse", "HEAD"])
        commit = c.strip() or None
    else:
        owner, repo, branch, unterpfad = parse_github(a.url)
        meta = metadaten(owner, repo)
        if (meta.get("groesse_kb") or 0) > REPO_GROESSE_WARNUNG_KB:
            print(T(f"⚠️ Repo ist {meta['groesse_kb'] // 1024} MB groß — Klonen dauert.",
                    f"⚠️ Repo is {meta['groesse_kb'] // 1024} MB — cloning takes a while."), file=sys.stderr)
        ziel = Path(a.ziel).expanduser() if a.ziel else Path(tempfile.mkdtemp(prefix="repo-pruefer-"))
        wurzel, commit = klonen(owner, repo, branch, ziel)

    erg = scan(wurzel, unterpfad)
    pakete = list(erg["inventar"]["npx_pakete"])
    for pj in erg["inventar"]["package_json"]:
        if pj["name"] and not pj["privat"] and pj["datei"].count("/") == 0:
            pakete.insert(0, pj["name"])
    npm = [] if a.ohne_npm or not pakete else npm_check(list(dict.fromkeys(pakete)))
    if not a.ohne_npm and erg["inventar"]["uvx_pakete"]:
        npm += pypi_check(erg["inventar"]["uvx_pakete"])
    print(bericht(meta, erg, commit, str(wurzel), npm))

    if a.json:
        b: Befunde = erg["befunde"]
        inv = dict(erg["inventar"])
        inv["endungen"] = dict(inv["endungen"])
        inv["domains_code"] = dict(inv["domains_code"])
        inv["domains_doku"] = dict(inv["domains_doku"])
        Path(a.json).write_text(json.dumps({
            "meta": meta, "commit": commit, "klon": str(wurzel), "inventar": inv,
            "befunde": [{"kategorie": k, "stufe": s, "titel": t, "anzahl": b.anzahl[(k, s, t)],
                         "beispiele": b.treffer[(k, s, t)]} for (k, s, t) in b.anzahl],
            "ampel": vorlaeufige_einstufung(b, meta), "sprache": LANG,
        }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
