# Privacy policy — Repo-Prüfer

🇩🇪 [Deutsche Fassung weiter unten](#datenschutzerklärung--repo-prüfer)

Repo-Prüfer is a Claude Code plugin created by Sertac and published by
[NetBoosting](https://netboosting.de). It runs entirely on your own machine.

## What the plugin does NOT do
- It collects **no** personal data and has **no** telemetry, analytics or tracking.
- It sends **nothing** to the author, to NetBoosting or to any server operated by them.
- It never reads or transmits your Claude configuration, API keys or other credentials.

## Which servers it contacts, and why
When you ask it to review a repository, the bundled script `scripts/scan.py` contacts only
these public services, only to read public information about the repository or package you
asked about:

| Service | What is requested | Purpose |
|---|---|---|
| `api.github.com` | metadata of the requested repository (stars, license, commits, issue titles) | repository profile |
| `github.com` | a shallow `git clone` of the requested repository | reading the code |
| `registry.npmjs.org`, `api.npmjs.org` | metadata and weekly downloads of npm packages the repo launches | supply-chain check |
| `pypi.org` | metadata of Python packages the repo launches | supply-chain check |

What these services receive is what any such request carries: the name of the repository
or package, your IP address and a user-agent string. Their own privacy policies apply
(GitHub, npm, Python Software Foundation).

If you are logged in with the GitHub CLI `gh`, the script uses that login for the GitHub
lookups. The token is handled by `gh` and goes **only to GitHub itself**. `git` and `npm`
are started with a minimal environment that contains no tokens or keys.

## What stays on your machine
- Cloned repositories go into a temporary folder and are deleted after the review unless you
  ask to extract parts.
- Review reports are written only to a local file that you choose (configured in
  `~/.claude/repo-pruefer/projects.md` or `projekte.md`), and only if you set one up.
- Your project profiles are a local file that you write yourself; the plugin only reads it.

## Contact
Questions or concerns: open an issue at
<https://github.com/Sertac0708/github-repo-pruefer/issues>.

---

# Datenschutzerklärung – Repo-Prüfer

Der Repo-Prüfer ist ein Claude-Code-Plugin, erstellt von Sertac und herausgegeben von
[NetBoosting](https://netboosting.de). Er läuft vollständig auf deinem eigenen Rechner.

## Was das Plugin NICHT tut
- Es erhebt **keine** personenbezogenen Daten und hat **keine** Telemetrie, Analyse oder Nachverfolgung.
- Es sendet **nichts** an den Autor, an NetBoosting oder an Server, die diese betreiben.
- Es liest oder überträgt niemals deine Claude-Konfiguration, API-Schlüssel oder andere Zugangsdaten.

## Welche Server es kontaktiert und warum
Wenn du ein Repo prüfen lässt, kontaktiert das mitgelieferte Skript `scripts/scan.py` nur
diese öffentlichen Dienste. Es liest dort nur öffentliche Informationen über das Repo oder
Paket, nach dem du gefragt hast:

| Dienst | Was abgefragt wird | Zweck |
|---|---|---|
| `api.github.com` | Metadaten des angefragten Repos (Sterne, Lizenz, Commits, Issue-Titel) | Steckbrief |
| `github.com` | ein flacher `git clone` des angefragten Repos | Code lesen |
| `registry.npmjs.org`, `api.npmjs.org` | Metadaten und Wochendownloads der npm-Pakete, die das Repo startet | Lieferketten-Prüfung |
| `pypi.org` | Metadaten der Python-Pakete, die das Repo startet | Lieferketten-Prüfung |

Diese Dienste erhalten, was jede solche Anfrage enthält: den Namen des Repos oder Pakets,
deine IP-Adresse und eine Programmkennung (User-Agent). Es gelten deren eigene
Datenschutzerklärungen (GitHub, npm, Python Software Foundation).

Bist du mit der GitHub-CLI `gh` angemeldet, nutzt das Skript diese Anmeldung für die
GitHub-Abfragen. Das Token verwaltet `gh`, und es geht **nur an GitHub selbst**. `git` und
`npm` werden mit einer abgespeckten Umgebung gestartet, die keine Tokens oder Schlüssel enthält.

## Was auf deinem Rechner bleibt
- Geklonte Repos landen in einem temporären Ordner. Sie werden nach der Prüfung gelöscht,
  außer du lässt Teile herausziehen.
- Prüfberichte werden nur in eine lokale Datei geschrieben, die du selbst festlegst
  (in `~/.claude/repo-pruefer/projekte.md` oder `projects.md`), und nur, wenn du eine einrichtest.
- Deine Projekt-Steckbriefe sind eine lokale Datei, die du selbst schreibst; das Plugin liest sie nur.

## Kontakt
Fragen oder Bedenken: Eröffne ein Issue unter
<https://github.com/Sertac0708/github-repo-pruefer/issues>.
