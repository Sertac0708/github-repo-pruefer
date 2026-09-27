# Herausziehen einzelner Teile

Ziel: aus einem geprüften Repo nur das übernehmen, was nützt — ohne die Verzahnung
(Hooks, Telemetrie, Auto-Freigaben, gehostete Server), die das Gesamtpaket mitbringt.

Vorbild: Aus einer Sammlung mit 292 Skills und 24 Hooks wurden 44 Skills einzeln kopiert —
Ergebnis: 0 ausführbare Dateien, `settings.json` unverändert. Aus einem Marktplatz mit
63 Skills wurden die 5 fachunabhängigen übernommen, der Rest dokumentiert.

## 1 · Inventar zeigen
Aus dem Scan-Inventar eine Tabelle bauen: Teil · Art (Skill/Agent/Befehl/Skript/Komponente/
Funktion/Prompt) · was es kann (1 Satz) · **Abhängigkeiten** · Empfehlung.

Abhängigkeiten pro Teil ermitteln:
- Ruft der Skill MCP-Werkzeuge auf (`mcp__…`, Werkzeugnamen aus einer `.mcp.json`)?
  → Ohne laufenden Server **wertlos**. So sagen, nicht kopieren.
- Braucht er Dateien außerhalb seines Ordners (`../shared/…`, Skripte, Vorlagen)?
- Braucht er API-Keys, Bezahldienste, bestimmte Programme (`ffmpeg`, `node`, Python-Pakete)?
- Verweist er auf andere Skills/Agenten, die mitkommen müssten?
- Ist er an einen fremden Stack gebunden, den keines der eigenen Projekte nutzt?

## 2 · Auswahl
Mit dem Nutzer entscheiden. Vorschlag machen anhand der Projekt-Steckbriefe.
Zielort vorher nennen:
- Skill/Agent/Befehl, projektübergreifend → `~/.claude/skills/<name>/` (bzw. `agents/`, `commands/`)
- Skill nur für ein Projekt → `<projekt>/.claude/skills/<name>/`
- Code (Funktion, Komponente, Skript) → in das Projekt, an dem gerade gearbeitet wird,
  an die Stelle, die zur dortigen Struktur passt

Namenskonflikt prüfen: existiert der Zielordner schon? Dann nicht überschreiben — fragen.

## 3 · Übernehmen
- **Unverändert** (z. B. reine Anleitungs-Skills): Ordner kopieren, ohne `.git`, ohne Hooks.
- **Angepasst** (Code in eigenes Projekt): an Stil, Sprache und Stack des Zielprojekts
  anpassen, fremde Telemetrie/Analytics entfernen, Konfiguration auf eigene env-Variablen,
  keine Klartext-Keys.
- **Nie mitnehmen:** `hooks/`, `hooks.json`, `settings.json`-Freigaben, Telemetrie-Module,
  gehostete MCP-Einträge, `postinstall`-Skripte, Binärdateien, `.env`.
- Braucht ein Skript Python-Pakete und das System-Python ist gesperrt (PEP 668): eigene
  venv anlegen, **nicht** `--break-system-packages`. Im Skill einen Abschnitt
  „Auf diesem Rechner" mit dem Interpreter-Pfad ergänzen.

## 4 · Herkunft festhalten
Im übernommenen Teil (Frontmatter-`metadata` bei Skills, Kopfkommentar bei Code):
```
Quelle: https://github.com/<owner>/<repo>/tree/<commit>/<pfad>
Übernommen: JJJJ-MM-TT · Lizenz: <SPDX>
Geändert: <nein | was>
```
Lizenz beachten: MIT/Apache/BSD erlauben Übernahme mit Lizenzhinweis (bei Apache auch
NOTICE). GPL/AGPL: Übernahme in geschlossenen Code **nicht** ohne Weiteres — melden.
Keine Lizenz = rechtlich nicht freigegeben → melden, nur als Anregung nutzen.

## 5 · Nachkontrolle (Pflicht, Ergebnis nennen)
```bash
# ausführbare Dateien im übernommenen Bereich
find <ziel> -type f -perm +111
# Hooks / Freigaben aus Versehen mitgekommen?
grep -rl '"hooks"\|"permissions"\|mcpServers' <ziel>
# Frontmatter gültig (Skills): name + description vorhanden
head -5 <ziel>/SKILL.md
# globale Einstellungen unverändert?
git -C ~/.claude diff --stat 2>/dev/null || ls -la ~/.claude/settings.json
```
Danach im Bericht: was übernommen, wohin, Commit-Stand, was bewusst weggelassen und warum.
In der Ablage-Datei unter „Entscheidung" festhalten.
