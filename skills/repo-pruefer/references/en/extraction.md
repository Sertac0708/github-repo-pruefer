# Extracting individual parts

Goal: take only what is useful from a reviewed repo — without the entanglement (hooks,
telemetry, auto-approvals, hosted servers) that the full package brings along.

Precedent: from a collection with 292 skills and 24 hooks, 44 skills were copied
individually — result: 0 executable files, `settings.json` unchanged. From a marketplace
with 63 skills, the 5 domain-independent ones were taken and the rest documented.

## 1 · Show the inventory
Build a table from the scan inventory: part · kind (skill/agent/command/script/component/
function/prompt) · what it does (1 sentence) · **dependencies** · recommendation.

Determine the dependencies per part:
- Does the skill call MCP tools (`mcp__…`, tool names from a `.mcp.json`)?
  → **Worthless** without a running server. Say so, don't copy.
- Does it need files outside its folder (`../shared/…`, scripts, templates)?
- Does it need API keys, paid services, specific programs (`ffmpeg`, `node`, Python packages)?
- Does it reference other skills/agents that would have to come along?
- Is it tied to a stack none of the user's projects use?

## 2 · Selection
Decide with the user. Propose based on the project profiles.
Name the destination first:
- Skill/agent/command, cross-project → `~/.claude/skills/<name>/` (or `agents/`, `commands/`)
- Skill for one project only → `<project>/.claude/skills/<name>/`
- Code (function, component, script) → into the project currently being worked on,
  in the place that fits its structure

Check for name conflicts: does the destination folder already exist? Then don't overwrite — ask.

## 3 · Take it over
- **Unchanged** (e.g. instruction-only skills): copy the folder, without `.git`, without hooks.
- **Adapted** (code into your own project): adapt to the style, language and stack of the
  target project, remove third-party telemetry/analytics, configuration via your own env
  variables, no plain-text keys.
- **Never take along:** `hooks/`, `hooks.json`, `settings.json` approvals, telemetry modules,
  hosted MCP entries, `postinstall` scripts, binaries, `.env`.
- If a script needs Python packages and the system Python is locked (PEP 668): create a
  dedicated venv, **not** `--break-system-packages`. Add a section "On this machine" with
  the interpreter path to the skill.

## 4 · Record the origin
In the adopted part (frontmatter `metadata` for skills, header comment for code):
```
Source: https://github.com/<owner>/<repo>/tree/<commit>/<path>
Taken: YYYY-MM-DD · License: <SPDX>
Modified: <no | what>
```
Mind the license: MIT/Apache/BSD allow reuse with the license notice (Apache also NOTICE).
GPL/AGPL: not simply into closed code — flag it.
No license = not legally released → flag it, use as inspiration only.

## 5 · Post-check (mandatory, report the result)
```bash
# executable files in the adopted area
find <dest> -type f -perm +111
# hooks / approvals accidentally included?
grep -rl '"hooks"\|"permissions"\|mcpServers' <dest>
# frontmatter valid (skills): name + description present
head -5 <dest>/SKILL.md
# global settings unchanged?
git -C ~/.claude diff --stat 2>/dev/null || ls -la ~/.claude/settings.json
```
Then in the report: what was taken, where to, commit, what was deliberately left out and why.
Record it under "Decision" in the log file.
