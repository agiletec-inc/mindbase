---
title: "Claude Code Kept Making the Same Mistakes, So I Trained It Into a Senior Engineer"
description: "After months of loops, hallucinations, and broken environments, I built a 4-layer defense architecture for Claude Code. CLAUDE.md, Hooks, MCP Gateway, and Superpowers plugin — here's the full setup with all the failures along the way."
author: "Kazuki Nakai"
date: "2026-03-28"
tags: ["claude-code", "ai-coding", "mcp", "developer-tools", "productivity"]
language: "en"
---

# Claude Code Kept Making the Same Mistakes, So I Trained It Into a Senior Engineer

I've been using Claude Code for two years. The first six months were, honestly, disappointing.

It could write code. But it would run `npm install` on the host and break my Docker environment. It would skip tests and report "Done!" It would fix the same bug three times with the same wrong approach. It would create files I never asked for. It nearly committed `.env` files.

I almost gave up on it.

But the problem wasn't Claude Code. **The problem was me.** I was treating it like a magic box instead of a team member. A junior engineer thrown into a codebase without rules will cause the same chaos. What Claude Code lacked wasn't ability — it was **discipline**.

This article walks through the 4-layer defense architecture that transformed Claude Code from "an unpredictable junior" into "a self-verifying senior engineer." Every configuration shown here is from my actual production setup.

---

## The First Failure: Too Much Freedom

When I first set up Claude Code, my CLAUDE.md had one line: "Respond in Japanese."

The results:

- **Environment destruction**: Ran `npm install` on host → Docker build cache invalidated → 2 hours debugging
- **Infinite loops**: Fixing a TypeScript error → build → different error → fix → build → back to the original error. Five times.
- **False completion reports**: "Tests pass!" → Actually ran them → 3 failures → "I couldn't find the test files so I skipped them"
- **Unsolicited refactoring**: Asked to fix a bug → "improved" surrounding code → introduced a new bug

The worst incident: I asked Claude Code to fix a bug on Friday night and went to sleep. Saturday morning, `node_modules` had been generated on the host, and my entire Docker environment was broken. I spent Saturday morning rebuilding it.

That's when I realized: **Claude Code needs to learn what NOT to do before learning what to do.**

---

## Layer 1: CLAUDE.md — Write the Constitution

CLAUDE.md is Claude Code's constitution. It's loaded at the start of every conversation and governs all behavior.

The core of mine:

```markdown
## Docker-First

Everything runs inside Docker containers. Never execute package managers
or runtimes directly on the host.

## Safety

- Never disable or bypass hooks (including --no-verify)
- Fix the cause of test/lint failures, don't disable the checks
- Get user confirmation before push/deploy
- Never modify config files without explicit instruction

## Verify — Confirm Before Reporting

- Don't just say "implemented" — verify with Playwright or browser
- Run `airis test` before push, confirm zero errors
- After push, `gh run watch` to wait for CI, fix failures yourself
- Don't use the user as a debugger
```

### Why "Docker-First" Comes First

Because it's the most violated rule. Claude Code defaults to running `npm install` on the host because it's "easiest." In a Docker environment, that's catastrophic.

But CLAUDE.md alone wasn't enough. Claude Code "forgets" rules in long conversations. Rules at the edge of the context window lose to new instructions.

That's why I needed Layer 2.

---

## Layer 2: Hooks — Physically Block Dangerous Actions

CLAUDE.md is a request. Hooks are the law.

Claude Code has three hook points:

- **PreToolUse**: Intercept before tool execution
- **SessionStart**: Run at session start
- **Stop**: Run at session end

### Docker-First Guard

The single most impactful change:

```bash
#!/bin/bash
# PreToolUse hook for Bash tool

COMMAND="$1"

if echo "$COMMAND" | grep -qE '^\s*(pnpm|npm|yarn)\s+(install|add|remove|update)' ||
   echo "$COMMAND" | grep -qE '^\s*pip\s+install' ||
   echo "$COMMAND" | grep -qE '^\s*brew\s+install'; then
  echo "BLOCKED: Host package manager execution detected."
  echo "Use: docker compose exec <service> <command>"
  exit 1
fi
```

When Claude Code tries `pnpm install` on the host, **the command is blocked before execution**. Claude Code gets: "Blocked. Use `docker compose exec` instead."

Before: Cleaning up host `node_modules` 2-3 times per week.
After: **Zero.**

### Pre-Push Test Enforcement

```bash
if ! airis test; then
  echo "ERROR: Tests failed. Fix before pushing."
  exit 1
fi
```

The "tests pass!" lie? Gone. If they don't pass, the push physically cannot happen.

---

## Layer 3: MCP Gateway — 60+ Tools in One Command

This is where it gets interesting.

MCP (Model Context Protocol) lets you connect external tools to Claude Code. But naively registering 60 tools with their schemas eats **thousands of tokens** from your context window. Every conversation. Whether you use them or not. And managing dozens of server configs becomes its own nightmare.

So I built [**airis-mcp-gateway**](https://github.com/agiletec-inc/airis-mcp-gateway).

### Setup: 3 Lines

```bash
git clone https://github.com/agiletec-inc/airis-mcp-gateway.git
cd airis-mcp-gateway && docker compose up -d
claude mcp add --scope user --transport sse airis-mcp-gateway http://localhost:9400/sse
```

That's it. These 3 lines give you documentation lookup (context7), web search (tavily), database operations (supabase), payments (stripe), infrastructure management (cloudflare), browser automation (chrome-devtools), design files (figma) — 60+ tools, ready to use.

### The Core Idea: `airis-exec` — One Tool to Call Them All

Traditional MCP requires registering each tool individually. airis-mcp-gateway flips this: **Claude Code sees only one meta-tool called `airis-exec`**.

```
Claude Code
    ↓ "calls airis-exec once"
airis-mcp-gateway (FastAPI)
    ↓ routes to the right server internally
┌─────────────────────────────────┐
│ context7  tavily  supabase      │
│ stripe  cloudflare  figma       │
│ chrome-devtools  memory  ...    │
│         25+ servers             │
└─────────────────────────────────┘
```

The trick: the full list of available tools is **embedded in `airis-exec`'s tool description**. Claude Code reads the description, knows what's available, and calls it directly. **No discovery step needed.**

```
Claude Code's reasoning:
"I need to look up Next.js docs"
→ reads airis-exec description
→ sees [context7] resolve-library-id, query-docs
→ airis-exec("context7:resolve-library-id", { "libraryName": "next.js" })
→ official docs come back
→ writes code based on actual documentation
```

One tool call to access official documentation, then write code. **This alone cut hallucinations dramatically.**

### Token Reduction

- Before: 60 tools × ~700 tokens/schema = **42,000 tokens** (always consumed)
- After: `airis-exec` + 6 supporting meta-tools = **~1,400 tokens**

**97% reduction.** Not an estimate — measured.

Freeing up 40K tokens of context window means longer conversations, bigger refactors, and multi-file changes without hitting limits.

### HOT/COLD Lifecycle

Not every server needs to run all the time. Frequently used ones (context7, tavily) stay HOT. Occasional ones (figma, stripe) go COLD and auto-start on first call.

COLD servers **auto-enable** when called through `airis-exec`. Even disabled servers get discovered, enabled, started, and executed — all in one call. No manual config switching needed.

---

## Layer 4: Superpowers — Force "Think Before You Code"

The final piece.

Claude Code's biggest problem is **writing code before thinking**. Exactly like a human junior engineer. "Let me just get something working" → spaghetti code.

[Superpowers](https://github.com/anthropics/claude-code-plugins/tree/main/superpowers) is a plugin from Claude Code's official plugin marketplace (`/plugins` → search "superpowers"). It **enforces workflows**:

| Skill | Enforced Behavior |
|-------|-------------------|
| `brainstorming` | Design before coding. Compare 2-3 approaches |
| `writing-plans` | Plan before implementing. Specify files, changes, verification |
| `test-driven-development` | Write tests first. Then implement |
| `systematic-debugging` | Don't shotgun-fix. Hypothesize, verify, then fix |
| `verification-before-completion` | Before saying "done," actually run the tests |

### Before/After

**Before (no Superpowers)**:
```
Me: Fix this bug
Claude: [immediately edits code] → [build error] → [different fix] → [test fails] → [another fix] → 5 loops
```

**After (with Superpowers)**:
```
Me: Fix this bug
Claude: [systematic-debugging activates]
  1. Confirm reproduction steps
  2. Form 3 hypotheses
  3. Test most likely hypothesis
  4. Identify root cause
  5. Write test first
  6. Fix
  7. Verify tests pass
  8. Visual check in browser
```

Loop count dropped by **~70%**.

---

## The 4 Layers Working Together

Each layer is useful on its own, but the real power is the combination:

```
Layer 4: Superpowers  → Think before coding (workflow enforcement)
Layer 3: MCP Gateway  → Use correct information (official docs)
Layer 2: Hooks        → Physically prevent dangerous actions (guardrails)
Layer 1: CLAUDE.md    → Share rules and values (constitution)
```

Lower layers are "hard" constraints. Upper layers are "soft" constraints.

CLAUDE.md alone is just a polite request. Hooks stop dangerous actions but don't ensure correctness. Correct information without structure produces spaghetti. You need all four.

**All 4 layers together is what makes Claude Code behave like a senior engineer.**

---

## Getting Started

You don't need everything at once. Here's the order I'd recommend:

### Step 1: Write CLAUDE.md (30 minutes)

Start with your project's basic rules:
- Language preferences
- What NOT to do (environment-specific dangers)
- Definition of "done" (tests required, etc.)

### Step 2: Set Up Hooks (1 hour)

Highest ROI. Add PreToolUse hooks in `settings.json` to block dangerous commands.

### Step 3: Add MCP Gateway (half day)

Docker Compose up, connect via SSE. Start with just context7 (documentation lookup) — it's immediately valuable.

### Step 4: Install Superpowers (5 minutes)

In Claude Code, run `/plugins` → search "superpowers" → install. Immediate effect.

---

## Conclusion

Claude Code is a completely different tool depending on how you configure it.

Out of the box, it's a "capable but undisciplined junior engineer." With CLAUDE.md sharing values, Hooks physically preventing mistakes, MCP Gateway providing accurate information, and Superpowers enforcing structured thinking — it becomes something else entirely.

Since building this setup, I've been developing products at 5x my previous speed as a solo founder. Claude Code isn't a "tool." Trained properly, it's a teammate.

Every configuration shown in this article is running in my actual production environment. If you have questions, drop them in the comments.

---

## Try It Now

You don't need to build this setup from scratch. It's all open source.

### airis-mcp-gateway — 60+ AI Tools in One Command

```bash
git clone https://github.com/agiletec-inc/airis-mcp-gateway.git
cd airis-mcp-gateway && docker compose up -d
claude mcp add --scope user --transport sse airis-mcp-gateway http://localhost:9400/sse
```

Documentation lookup, web search, database operations, payments, infrastructure, browser automation — all through a single connection.

**GitHub**: [agiletec-inc/airis-mcp-gateway](https://github.com/agiletec-inc/airis-mcp-gateway)

### airis-monorepo — Auto-Generate Docker-First Dev Environments

Write a `manifest.toml`, and it generates your Dockerfile, docker-compose.yml, and CI/CD pipeline automatically. Same environment on every machine, every time. This is the CLI tool that makes the Docker-First philosophy from this article practical.

**GitHub**: [agiletec-inc/airis-monorepo](https://github.com/agiletec-inc/airis-monorepo)

---

### What's Next

This article covered the 4-layer overview. Detailed deep-dives on each layer are coming:

- **CLAUDE.md Design Patterns** — Rules that actually worked and why
- **airis-mcp-gateway Complete Guide** — From install to custom server integration
- **Hooks Cookbook** — Practical PreToolUse / SessionStart / Stop recipes
- **Superpowers in Practice** — Automating TDD, debugging, and planning workflows

Let me know in the comments which topic you want first.
