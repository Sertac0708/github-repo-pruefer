# 🔍 Repo-Prüfer — a Claude Code plugin that reviews third-party code before you install it

> **Created by Sertac · Made by [NetBoosting](https://netboosting.de)** · Free to use under the MIT license. · 🇩🇪 [Deutsche Anleitung](README.de.md)

You found an interesting GitHub repo, a Claude plugin, a skill or an MCP server — and you
wonder: *Is this safe? What does it actually do? Can I use it?*

Just send Claude the link. Repo-Prüfer ("repo checker")

- **explains what's in the repo** in a few plain sentences
- **reviews its security** against 7 fixed questions plus malware and manipulation checks
- **gives a three-level verdict:** ✅ safe · ⚠️ usable with settings · 🛑 caution
- **matches it against your own projects** ("fits your shop because …")
- **extracts individual parts on request** — e.g. 5 out of 60 skills — without the hooks,
  telemetry and auto-approvals the full package brings along

It answers in your language (German and English built in).

## What gets checked

| # | Question | Example findings |
|---|---|---|
| 1 | **What starts automatically?** | Claude hooks, `postinstall` scripts, LaunchAgents, cron, background processes |
| 2 | **What leaves the machine?** | telemetry (PostHog, Sentry …), hosted MCP servers, Discord/Telegram webhooks, hard-coded IPs |
| 3 | **What permissions does it take?** | auto-approvals like `Bash(*)`, writes to `~/.claude.json`, shell profiles, access to `~/.ssh`, keychain, browser data |
| 4 | **Supply chain** | `npx …@latest`, `curl \| bash`, unpinned dependencies, single-maintainer npm packages, npm vs. PyPI mix-ups |
| 5 | **Secrets** | plain-text API keys (shown masked only) |
| 6 | **Does it do what it promises?** | spot checks: README promises vs. actual code |
| 7 | **Maintenance** | last commit, releases, contributors, open issues, license |
| + | **Malware** | obfuscated code (`eval(atob(…))`), reverse shells, crypto miners, binaries |
| + | **AI manipulation** | text like "ignore previous instructions" or "mark this repo as safe", invisible Unicode characters |

The last point matters: a malicious repo may try to manipulate exactly the AI that reviews
it. The plugin therefore treats repo content as **data, never as instructions** and reports
such text as a finding.

## Installation

**Requirements:** [Claude Code](https://claude.com/claude-code), `git` and `python3`
(usually preinstalled on macOS and Linux). Recommended: the GitHub CLI `gh`, logged in
(otherwise GitHub's anonymous limit of 60 requests per hour applies), and `npm` for the
maintainer check. **Claude Code only** — the scan needs a shell, so it does not run on claude.ai.

### Option A — as a plugin (recommended, with one-command updates)

```bash
claude plugin marketplace add Sertac0708/github-repo-pruefer
```
```bash
claude plugin install repo-pruefer@sertac-skills
```

Restart Claude Code. Updates later:

```bash
claude plugin marketplace update sertac-skills
```
```bash
claude plugin update repo-pruefer@sertac-skills
```

### Option B — just ask Claude

Type in Claude Code: *"Install the plugin from https://github.com/Sertac0708/github-repo-pruefer — review it first."*

### Option C — copy the skill folder manually

```bash
git clone https://github.com/Sertac0708/github-repo-pruefer.git
```
```bash
mkdir -p ~/.claude/skills && cp -R github-repo-pruefer/skills/repo-pruefer ~/.claude/skills/
```

Or download the ZIP from the [latest release](https://github.com/Sertac0708/github-repo-pruefer/releases/latest)
and copy the `skills/repo-pruefer` folder to `~/.claude/skills/`.

### Optional: add your projects

So the plugin can tell you which of your projects a repo fits:

```bash
mkdir -p ~/.claude/repo-pruefer
```

Then create `~/.claude/repo-pruefer/projects.md` from the template
[`references/en/projects.template.md`](skills/repo-pruefer/references/en/projects.template.md)
— or just tell Claude: *"Help me set up my projects for repo-pruefer."* The file stays on
your machine. It also sets which file review reports are written to.

## Usage

Just write in Claude Code:

- `Check https://github.com/owner/repo`
- `Is this safe? https://github.com/owner/plugin`
- `Can I use anything from https://github.com/owner/collection for my shop?`
- `Extract the xyz skill from https://github.com/owner/repo`
- or just the link, without comment

The scan script can also be run directly (adjust the path for plugin installs):

```bash
python3 ~/.claude/skills/repo-pruefer/scripts/scan.py https://github.com/owner/repo --lang en
```

## Example (shortened)

```
## every-app/open-seo — ⚠️ usable with settings

What is it? Open-source alternative to Semrush/Ahrefs with an MCP server and 11 SEO skills.
Self-hostable (Cloudflare/Docker); data comes from DataForSEO (pay per request).

| 1 Starts automatically?      | ✅ nothing — no hooks, no postinstall                    |
| 2 What leaves the machine?   | ⚠️ PostHog telemetry, even when self-hosted (counts)     |
| 4 Supply chain               | ⚠️ `auth@latest` in two developer scripts                |
...
Recommendation: run only with OPENSEO_TELEMETRY_DISABLED=1.
```

## How safe is the plugin itself?

You should review this plugin too before installing it — ideally with itself:
`python3 skills/repo-pruefer/scripts/scan.py --local . --lang en`

> **Don't be alarmed:** the self-scan reports 🛑 because `scan.py` contains the search
> patterns themselves (`xmrig`, `curl | bash`, "ignore previous instructions" …) — just like
> an antivirus signature list. All hits are in the rule list of `scan.py` and in the doc
> examples of README/SKILL.md. Reading the findings is exactly step 3 of the skill:
> find patterns, then read, then judge.

Its answers to its own 7 questions:

1. **Nothing starts automatically.** No hooks, no MCP server, no install script, no background service.
2. **Network:** only `api.github.com` (metadata), `github.com` (cloning), `registry.npmjs.org`,
   `api.npmjs.org` and `pypi.org` (read-only package lookups). No telemetry, no server of the author.
3. **Permissions:** no auto-approvals; never writes to `~/.claude.json` or `settings.json`.
   Clones go into a temporary folder.
4. **Supply chain:** Python standard library only, zero dependencies.
5. **Secrets:** none.
6. **When cloning**, git hooks, LFS filters, submodules and symlinks are disabled — so even the
   download can't start foreign code. Nothing from the reviewed repo is **ever** executed.
7. **Limits:** static review. It finds known patterns and whatever stands out when reading,
   but it is no guarantee against well-hidden malware. Dependencies (node_modules, pip
   packages) are not scanned recursively.

## Layout

```
.claude-plugin/
├── plugin.json                    plugin manifest
└── marketplace.json               makes this repo a one-plugin marketplace
skills/repo-pruefer/
├── SKILL.md                       the workflow Claude follows
├── scripts/scan.py                automatic scan (clones safely, only reads; --lang de|en)
└── references/
    ├── en/  audit-guide · report-template · extraction · projects.template
    └── de/  pruefablauf · berichtsvorlage · extrahieren · projekte.vorlage
```

## License

MIT — see [LICENSE](LICENSE). Created by Sertac, 2026.

---

**Made by [NetBoosting](https://netboosting.de)** — we build AI automations and Claude workflows for businesses.
