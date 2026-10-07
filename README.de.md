# 🔍 Repo-Prüfer: ein Claude-Code-Plugin, das fremden Code prüft, bevor du ihn installierst

> **Erstellt von Sertac · Made by [NetBoosting](https://netboosting.de)** · Freie Nutzung unter MIT-Lizenz. · 🇬🇧 [English](README.md)

Du findest ein spannendes GitHub-Repo, ein Claude-Plugin, einen Skill oder einen MCP-Server
und fragst dich: *Ist das sicher? Was macht das überhaupt? Kann ich das gebrauchen?*

Schick Claude einfach den Link. Der Repo-Prüfer

- **erklärt kurz und einfach, was im Repo steckt**
- **prüft die Sicherheit** nach 7 festen Fragen, dazu kommen ein Schadcode- und ein Manipulations-Check
- **urteilt in drei Stufen:** ✅ unbedenklich · ⚠️ mit Einstellung nutzbar · 🛑 Vorsicht
- **gleicht es mit deinen eigenen Projekten ab** („passt zu deinem Shop, weil …“)
- **zieht auf Wunsch einzelne Teile heraus**, z. B. 5 von 60 Skills, ohne die Hooks,
  Telemetrie und Auto-Freigaben, die das Gesamtpaket mitbringt

Er antwortet in deiner Sprache (Deutsch und Englisch eingebaut).

## Was genau geprüft wird

| # | Frage | Beispiele für Funde |
|---|---|---|
| 1 | **Was startet automatisch?** | Claude-Hooks, `postinstall`-Skripte, LaunchAgents, Cron, Hintergrundprozesse |
| 2 | **Was verlässt den Rechner?** | Telemetrie (PostHog, Sentry …), gehostete MCP-Server, Discord-/Telegram-Webhooks, fest eingetragene IPs |
| 3 | **Welche Rechte nimmt es sich?** | Auto-Freigaben wie `Bash(*)`, Schreiben in Claudes eigene Konfigurationsdateien, Shell-Profile, Zugriff auf `~/.ssh`, Schlüsselbund, Browserdaten |
| 4 | **Lieferkette** | `npx …@latest`, `curl \| bash`, Abhängigkeiten ohne Version, npm-Pakete mit nur einem Maintainer, npm/PyPI-Verwechslungen |
| 5 | **Secrets** | API-Schlüssel im Klartext (werden nur maskiert angezeigt) |
| 6 | **Tut es, was es verspricht?** | Stichproben: README-Versprechen gegen echten Code |
| 7 | **Pflegezustand** | letzter Commit, Releases, Mitwirkende, offene Issues, Lizenz |
| + | **Schadcode** | verschleierter Code (`eval(atob(…))`), Reverse Shells, Krypto-Miner, Binärdateien |
| + | **KI-Manipulation** | Texte wie „ignore previous instructions“ oder „mark this repo as safe“, unsichtbare Unicode-Zeichen |

Der letzte Punkt ist wichtig: Ein bösartiges Repo kann versuchen, genau die KI zu
manipulieren, die es prüft. Das Plugin behandelt Repo-Inhalte deshalb als **Daten, nie als
Anweisung** und meldet solche Texte als Befund.

## Installation

**Voraussetzungen:** [Claude Code](https://claude.com/claude-code), `git` und `python3`
(auf macOS und Linux meist schon da). Empfohlen sind außerdem die GitHub-CLI `gh`
(angemeldet, sonst gilt GitHubs Grenze von 60 anonymen Abfragen pro Stunde) und `npm`
für die Maintainer-Prüfung. **Nur Claude Code:** Der Scan braucht ein Terminal und läuft
deshalb nicht auf claude.ai.

### Weg A: als Plugin (empfohlen, Updates mit einem Befehl)

```bash
claude plugin marketplace add Sertac0708/github-repo-pruefer
```
```bash
claude plugin install repo-pruefer@sertac-skills
```

Danach Claude Code neu starten. So holst du dir später Updates:

```bash
claude plugin marketplace update sertac-skills
```
```bash
claude plugin update repo-pruefer@sertac-skills
```

### Weg B: Claude einfach fragen

In Claude Code schreiben: *„Installiere mir das Plugin von https://github.com/Sertac0708/github-repo-pruefer. Prüf es vorher.“*

### Weg C: den Skill-Ordner von Hand kopieren

```bash
git clone https://github.com/Sertac0708/github-repo-pruefer.git
```
```bash
mkdir -p ~/.claude/skills && cp -R github-repo-pruefer/skills/repo-pruefer ~/.claude/skills/
```

Du kannst auch die ZIP aus dem [neuesten Release](https://github.com/Sertac0708/github-repo-pruefer/releases/latest)
herunterladen und den Ordner `skills/repo-pruefer` nach `~/.claude/skills/` kopieren.

### Optional: deine Projekte eintragen

Damit das Plugin sagen kann, zu welchem deiner Projekte ein Repo passt:

```bash
mkdir -p ~/.claude/repo-pruefer
```

Dann `~/.claude/repo-pruefer/projekte.md` nach der Vorlage
[`references/de/projekte.vorlage.md`](skills/repo-pruefer/references/de/projekte.vorlage.md)
anlegen. Oder du sagst Claude einfach: *„Hilf mir, meine Projekte für den Repo-Prüfer
einzutragen.“* Die Datei bleibt auf deinem Rechner. Dort legst du auch fest, in welche
Datei die Prüfberichte geschrieben werden.

## Benutzung

Schreib in Claude Code zum Beispiel:

- `Prüf mal https://github.com/owner/repo`
- `Ist das sicher? https://github.com/owner/plugin`
- `Kann ich aus https://github.com/owner/sammlung was für meinen Shop gebrauchen?`
- `Zieh mir den Skill xyz aus https://github.com/owner/repo raus`
- oder schick nur den Link, ohne Kommentar

Das Prüfskript lässt sich auch direkt aufrufen. Bei einer Plugin-Installation ist der Pfad ein anderer:

```bash
python3 ~/.claude/skills/repo-pruefer/scripts/scan.py https://github.com/owner/repo --lang de
```

## Wie sicher ist das Plugin selbst?

Du solltest auch dieses Plugin prüfen, bevor du es installierst, am besten mit sich selbst:
`python3 skills/repo-pruefer/scripts/scan.py --lokal . --lang de`

> **Nicht erschrecken:** Die Selbstprüfung meldet 🛑, weil `scan.py` die Suchmuster
> selbst enthält (`xmrig`, `curl | bash`, „ignore previous instructions“ …), genau wie die
> Signaturliste eines Virenscanners. Alle Treffer liegen in der Regelliste von `scan.py`
> und in den Doku-Beispielen. Genau dieses Nachlesen der Fundstellen ist Schritt 3 des
> Skills: Muster finden, dann lesen, dann urteilen.

Die Antworten auf die eigenen 7 Fragen:

1. **Nichts startet automatisch.** Es gibt keine Hooks, keinen MCP-Server, kein Installationsskript und keinen Hintergrunddienst.
2. **Netz:** Kontakt nur zu `api.github.com` (Metadaten), `github.com` (Klonen) sowie `registry.npmjs.org`,
   `api.npmjs.org` und `pypi.org` (nur lesende Paketabfragen). Keine Telemetrie, kein Server des Autors. Wenn du mit der GitHub-CLI `gh` angemeldet bist, nutzt das Skript deren GitHub-Anmeldung für die GitHub-Abfragen; dieses Token geht nur an GitHub selbst. `git` und `npm` bekommen eine abgespeckte Umgebung ohne Tokens.
3. **Rechte:** Es gibt keine Auto-Freigaben. Das Plugin schreibt nie in Claudes Konfigurations- oder Einstellungsdateien.
   Geklont wird in einen temporären Ordner.
4. **Lieferkette:** nur die Python-Standardbibliothek, keine Abhängigkeiten.
5. **Secrets:** keine.
6. **Beim Klonen** sind Git-Hooks, LFS-Filter, Submodule und Symlinks abgeschaltet. So kann
   schon das Herunterladen keinen fremden Code starten. Aus dem geprüften Repo wird **nie** etwas ausgeführt.
7. **Grenzen:** Das Plugin prüft statisch. Es findet bekannte Muster und alles, was beim Lesen auffällt,
   ist aber keine Garantie gegen gut versteckten Schadcode. Abhängigkeiten (node_modules,
   pip-Pakete) werden nicht rekursiv durchleuchtet.

## Datenschutz

Das Plugin erhebt keine Daten und hat keine Telemetrie. Welche öffentlichen Dienste es genau kontaktiert und warum, steht in [PRIVACY.md](PRIVACY.md#datenschutzerklärung--repo-prüfer).

## Prüfung als Dienstleistung

Wenn du ein Plugin, einen Skill oder einen MCP-Server einsetzen willst und niemand den Code
vorher liest, prüft die NetBoosting GmbH ihn für dich: dieselben sieben Fragen wie dieses
Plugin, von Hand nachgeprüft, mit schriftlichem Ergebnis und Empfehlung. Schreib an
<hello@netboosting.de>, nenn das Repo und wofür du es einsetzen willst, und du bekommst ein
Angebot zum Festpreis.

## Lizenz

MIT, siehe [LICENSE](LICENSE). Erstellt von Sertac, 2026.

---

**Made by [NetBoosting](https://netboosting.de)**: Wir bauen KI-Automatisierungen und Claude-Workflows für Unternehmen.
