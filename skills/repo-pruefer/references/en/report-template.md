# Report template

## A · Short format (always, in chat)

```markdown
## <owner/repo> — <✅ safe | ⚠️ usable with settings | 🛑 caution>

**What is it?** <2–3 sentences in plain words: what it does, for whom, how it's used
(skill to copy / plugin / MCP server / framework to build on / desktop program).>

**Profile:** <stars> ⭐ · <license> · created <date> · last active <date> ·
<company X | individual Y (Z % of commits)> · <version>

**Security**
| Question | Result |
|---|---|
| 1 Starts automatically? | ✅ nothing / ⚠️ … / 🛑 … |
| 2 What leaves the machine? | … |
| 3 What permissions? | … |
| 4 Supply chain | … |
| 5 Secrets | … |
| 6 Does it do what it promises? | … |
| 7 Maintenance | … |
| Malware / AI manipulation | … |

**Fits your projects**
- <project> — <one concrete sentence: which open problem it solves>
- (or: "Doesn't fit any current project.")

**Already have it?** <existing skill/plugin/MCP that does the same — or "no">

**Useful parts to extract:** <list or "can't be extracted on their own because …">

**Costs/requirements:** <API keys, subscriptions, paid services>

**Recommendation:** <install · take individual parts · watch · stay away> — <1 sentence why>
<If ⚠️: the exact setting, e.g. set `DO_NOT_TRACK=1`>
```

Rules for the short format:
- Every ⚠️/🛑 line names the location (`file:line`) or the reason.
- No jargon without explanation ("hook = runs automatically on every tool call").
- Quote the repo verbatim only as evidence (e.g. an AI instruction, a telemetry promise).
- Write in the user's language.

## B · Long format (entry in the log file, newest on top)

```markdown
## YYYY-MM-DD · <owner/repo> reviewed (<INSTALLED | NOT installed | PARTS taken>)

**What:** <description, license, language, stars/forks, created/pushed, version,
contributors + main developer's share, open issues, who is behind it, website>

**What it does:** <features; for collections: number of skills/agents/commands/hooks>

**Security review (7 questions) — rating: <LEVEL>**
- Hooks/autostart: …
- Network/telemetry: … (what exactly, where to, how often, how to turn off)
- Permissions/auto-approvals: …
- Supply chain: … (dependencies, pinned?, npx/@latest, maintainers)
- Secrets: …
- Code vs. promise: …
- Maintenance: …

**By the way:** <affiliate links, invalid JSON, broken config, license traps>

**Fits:** <projects with reasons>

**Decision YYYY-MM-DD:** <what was done / why not / when to look again>
<If parts were taken: list + destination + commit>

**Installation (if ever needed):** <exact commands, with pinned version>
```
