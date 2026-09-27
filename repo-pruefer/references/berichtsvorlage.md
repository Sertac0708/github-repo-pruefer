# Berichtsvorlage

## A · Kurzformat (immer, im Chat)

```markdown
## <owner/repo> — <✅ unbedenklich | ⚠️ mit Einstellung nutzbar | 🛑 Vorsicht>

**Was ist das?** <2–3 Sätze, einfach erklärt: was es tut, für wen, wie man es nutzt
(Skill zum Kopieren / Plugin / MCP-Server / Framework zum Selberbauen / Desktop-Programm).>

**Steckbrief:** <Sterne> ⭐ · <Lizenz> · erstellt <Datum> · zuletzt aktiv <Datum> ·
<Firma X | Einzelentwickler Y (Z % der Commits)> · <Version>

**Sicherheit**
| Frage | Ergebnis |
|---|---|
| 1 Startet automatisch? | ✅ nichts / ⚠️ … / 🛑 … |
| 2 Was verlässt den Rechner? | … |
| 3 Welche Rechte? | … |
| 4 Lieferkette | … |
| 5 Secrets | … |
| 6 Tut es, was es verspricht? | … |
| 7 Pflegezustand | … |
| Schadcode / KI-Manipulation | … |

**Passt zu deinen Projekten**
- <Projekt> — <ein konkreter Satz: welche Baustelle es löst>
- (oder: „Passt zu keinem laufenden Projekt.")

**Haben wir schon?** <vorhandener Skill/Plugin/MCP, der dasselbe kann — oder „nein">

**Brauchbare Teile zum Herausziehen:** <Liste oder „nicht einzeln herauslösbar, weil …">

**Kosten/Voraussetzungen:** <API-Keys, Abos, Bezahldienste>

**Empfehlung:** <installieren · einzelne Teile übernehmen · beobachten · Finger weg> — <1 Satz warum>
<Falls ⚠️: die genaue Einstellung, z. B. `DO_NOT_TRACK=1` setzen>
```

Regeln für das Kurzformat:
- Jede ⚠️/🛑-Zeile nennt die Fundstelle (`datei:zeile`) oder den Grund.
- Keine Fachwörter ohne Erklärung („Hook = läuft automatisch bei jedem Werkzeugaufruf").
- Wörtliche Zitate aus dem Repo nur, wenn sie Beleg sind (z. B. KI-Anweisung, Telemetrie-Zusage).

## B · Langfassung (Eintrag in der Ablage-Datei, neuester oben)

```markdown
## JJJJ-MM-TT · <owner/repo> geprüft (<INSTALLIERT | NICHT installiert | TEILE übernommen>)

**Was:** <Beschreibung, Lizenz, Sprache, Sterne/Forks, erstellt/gepusht, Version,
Mitwirkende + Hauptentwickler-Anteil, offene Issues, wer dahinter steht, Webseite>

**Was es kann:** <Funktionsumfang; bei Sammlungen: Anzahl Skills/Agenten/Befehle/Hooks>

**Sicherheitsprüfung (7 Fragen) — Einstufung: <STUFE>**
- Hooks/Autostart: …
- Netz/Telemetrie: … (was genau, wohin, wie oft, wie abschalten)
- Rechte/Auto-Freigaben: …
- Lieferkette: … (Abhängigkeiten, gepinnt?, npx/@latest, Maintainer)
- Secrets: …
- Code vs. Versprechen: …
- Pflege: …

**Nebenbei:** <Affiliate-Links, ungültiges JSON, kaputte Konfig, Lizenzfallen>

**Passt zu:** <Projekte mit Begründung>

**Entscheidung JJJJ-MM-TT:** <was gemacht wurde / warum nicht / wann wieder anschauen>
<Falls Teile übernommen: Liste + Zielort + Commit-Stand>

**Installation (falls je gebraucht):** <exakte Befehle, mit festgenagelter Version>
```
