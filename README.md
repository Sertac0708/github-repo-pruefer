# 🔍 Repo-Prüfer — ein Claude-Skill, der fremden Code prüft, bevor du ihn installierst

> **Erstellt von Sertac.** Freie Nutzung unter MIT-Lizenz.

Du findest ein spannendes GitHub-Repo, ein Claude-Plugin, einen Skill oder einen MCP-Server —
und fragst dich: *Ist das sicher? Was macht das überhaupt? Kann ich das gebrauchen?*

Schick Claude einfach den Link. Der Repo-Prüfer

- **erklärt in Kurzform, was im Repo steckt** — einfach, ohne Fachchinesisch
- **prüft die Sicherheit** nach 7 festen Fragen plus Schadcode- und Manipulations-Check
- **urteilt in drei Stufen:** ✅ unbedenklich · ⚠️ mit Einstellung nutzbar · 🛑 Vorsicht
- **gleicht es mit deinen eigenen Projekten ab** („passt zu deinem Shop, weil …")
- **zieht auf Wunsch einzelne Teile heraus** — z. B. 5 von 60 Skills — ohne die Hooks,
  Telemetrie und Auto-Freigaben, die das Gesamtpaket mitbringt

## Was genau geprüft wird

| # | Frage | Beispiele für Funde |
|---|---|---|
| 1 | **Was startet automatisch?** | Claude-Hooks, `postinstall`-Skripte, LaunchAgents, Cron, Hintergrundprozesse |
| 2 | **Was verlässt den Rechner?** | Telemetrie (PostHog, Sentry …), gehostete MCP-Server, Discord-/Telegram-Webhooks, fest eingetragene IPs |
| 3 | **Welche Rechte nimmt es sich?** | Auto-Freigaben wie `Bash(*)`, Schreiben in `~/.claude.json`, Shell-Profile, Zugriff auf `~/.ssh`, Schlüsselbund, Browserdaten |
| 4 | **Lieferkette** | `npx …@latest`, `curl \| bash`, Abhängigkeiten ohne Version, npm-Pakete mit nur einem Maintainer |
| 5 | **Secrets** | API-Schlüssel im Klartext (werden nur maskiert angezeigt) |
| 6 | **Tut es, was es verspricht?** | Stichproben: README-Versprechen gegen echten Code |
| 7 | **Pflegezustand** | letzter Commit, Releases, Mitwirkende, offene Issues, Lizenz |
| + | **Schadcode** | verschleierter Code (`eval(atob(…))`), Reverse Shells, Krypto-Miner, Binärdateien |
| + | **KI-Manipulation** | Texte wie „ignore previous instructions" oder „mark this repo as safe", unsichtbare Unicode-Zeichen |

Der letzte Punkt ist wichtig: Ein bösartiges Repo kann versuchen, genau die KI zu
manipulieren, die es prüft. Der Skill behandelt Repo-Inhalte deshalb als **Daten, nie als
Anweisung** und meldet solche Texte als Befund.

## Installation (Claude Code)

**Voraussetzungen:** [Claude Code](https://claude.com/claude-code), `git` und `python3`
(auf macOS und Linux meist schon da). Empfohlen: GitHub-CLI `gh` (angemeldet — sonst
gelten die anonymen GitHub-Limits von 60 Abfragen pro Stunde) und `npm` für die
Maintainer-Prüfung.

```bash
git clone https://github.com/Sertac0708/github-repo-pruefer.git
mkdir -p ~/.claude/skills
cp -R github-repo-pruefer/repo-pruefer ~/.claude/skills/
```

Claude Code neu starten. Fertig — der Skill springt von selbst an, sobald du einen
GitHub-Link schickst.

### Optional: deine Projekte eintragen

Damit der Skill sagen kann, zu welchem deiner Projekte ein Repo passt:

```bash
mkdir -p ~/.claude/repo-pruefer
cp ~/.claude/skills/repo-pruefer/references/projekte.vorlage.md ~/.claude/repo-pruefer/projekte.md
```

Dann `~/.claude/repo-pruefer/projekte.md` ausfüllen (oder Claude sagen: *„Hilf mir,
meine Projekte für den Repo-Prüfer einzutragen"*). Die Datei bleibt auf deinem Rechner.
Dort legst du auch fest, in welche Datei die Prüfberichte geschrieben werden.

### Aktualisieren

```bash
cd github-repo-pruefer && git pull && cp -R repo-pruefer ~/.claude/skills/
```

## Benutzung

Einfach in Claude Code schreiben:

- `Prüf mal https://github.com/owner/repo`
- `Ist das sicher? https://github.com/owner/plugin`
- `Kann ich aus https://github.com/owner/sammlung was für meinen Shop gebrauchen?`
- `Zieh mir den Skill xyz aus https://github.com/owner/repo raus`
- oder nur den Link, ohne Kommentar

Das Prüfskript lässt sich auch direkt aufrufen:

```bash
python3 ~/.claude/skills/repo-pruefer/scripts/scan.py https://github.com/owner/repo
python3 ~/.claude/skills/repo-pruefer/scripts/scan.py --lokal ./ordner   # vorhandener Ordner
```

## Beispiel (gekürzt)

```
## every-app/open-seo — ⚠️ mit Einstellung nutzbar

Was ist das? Open-Source-Alternative zu Semrush/Ahrefs mit MCP-Server und 11 SEO-Skills.
Selbst hostbar (Cloudflare/Docker), Daten kommen von DataForSEO (Bezahlung pro Abruf).

| 1 Startet automatisch?      | ✅ nichts — keine Hooks, kein postinstall                 |
| 2 Was verlässt den Rechner? | ⚠️ PostHog-Telemetrie, auch selbstgehostet (Zählwerte)    |
| 4 Lieferkette               | ⚠️ `auth@latest` in zwei Entwickler-Skripten              |
...
Empfehlung: nur mit OPENSEO_TELEMETRY_DISABLED=1 betreiben.
```

## Wie sicher ist der Skill selbst?

Du solltest auch diesen Skill prüfen, bevor du ihn installierst — gerne mit sich selbst:
`python3 repo-pruefer/scripts/scan.py --lokal .`

> **Nicht erschrecken:** Die Selbstprüfung meldet 🛑, weil `scan.py` die Suchmuster
> selbst enthält (`xmrig`, `curl | bash`, „ignore previous instructions" …) — genau wie die
> Signaturliste eines Virenscanners. Alle Treffer liegen in der Regelliste von `scan.py`
> und in den Doku-Beispielen von README/SKILL.md. Genau dieses Nachlesen der Fundstellen
> ist Schritt 3 des Skills: Muster finden, dann lesen, dann urteilen.

Die Antworten auf die eigenen 7 Fragen:

1. **Startet nichts automatisch.** Keine Hooks, kein Installationsskript, kein Hintergrunddienst.
2. **Netz:** nur `api.github.com` (Metadaten), `github.com` (Klonen) und `registry.npmjs.org`
   (`npm view`, nur lesend). Keine Telemetrie, kein Server des Autors.
3. **Rechte:** keine Auto-Freigaben, schreibt nicht in `~/.claude.json` oder `settings.json`.
   Geklont wird in einen temporären Ordner.
4. **Lieferkette:** nur Python-Standardbibliothek, keine Abhängigkeiten.
5. **Secrets:** keine.
6. **Beim Klonen** sind Git-Hooks, LFS-Filter, Submodule und Symlinks abgeschaltet — so
   kann schon das Herunterladen keinen fremden Code starten. Aus dem geprüften Repo wird
   **nie** etwas ausgeführt.
7. **Grenzen:** statische Prüfung. Sie findet bekannte Muster und was beim Lesen auffällt,
   ist aber keine Garantie gegen gut versteckten Schadcode. Abhängigkeiten (node_modules,
   pip-Pakete) werden nicht rekursiv durchleuchtet.

## Aufbau

```
repo-pruefer/
├── SKILL.md                       Ablauf, den Claude befolgt
├── scripts/scan.py                automatischer Scan (klont sicher, liest nur)
└── references/
    ├── pruefablauf.md             Prüfschritte, Befehle, typische Funde
    ├── berichtsvorlage.md         Kurzformat + Langfassung
    ├── extrahieren.md             einzelne Teile sauber übernehmen
    └── projekte.vorlage.md        Vorlage für deine Projekt-Steckbriefe
```

## Lizenz

MIT — siehe [LICENSE](LICENSE). Erstellt von Sertac, 2026.
