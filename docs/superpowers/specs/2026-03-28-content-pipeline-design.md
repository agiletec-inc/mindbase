# MindBase Content Pipeline Design

## Context

MindBase has 2 years of AI conversation data (Claude Code, ChatGPT, Cursor, etc.) sitting in its database. The goal is to turn this into a branding engine: automatically generate high-quality blog articles from conversation data and publish them across multiple platforms in multiple languages, driving visibility and customer acquisition for agiletec.

The first content theme is "Claude Code mastery" — tips for reducing loops/mistakes, MCP Gateway, Superpowers plugin, Playwright CLI, Hooks/Rules/CLAUDE.md configuration. Articles follow a failure-first storytelling format: what was tried, what failed, what finally worked.

## Architecture Overview

```
Daily cron
  |
  v
Scanner (conversation analysis, topic extraction, scoring)
  |
  v
Generator (article drafts in JA + EN via LLM)
  |
  v
LLM Reviewer (quality, fact-check, tone, kazuki-voice)
  |
  +-- pass --> Publisher (auto-publish to all platforms)
  |                |
  |                v
  |            Slack (daily completion report with links)
  |
  +-- fail --> Slack ("this one needs human review")
```

### Phases

- **Startup**: LLM review -> all articles sent to Slack for kazuki to skim -> approve
- **Stable**: LLM review pass -> auto-publish. Only failures go to Slack for human review

### Backfill

Initial run processes 2 years of conversation history to build a large article idea backlog. Daily cron then processes new conversations as delta.

## Modules

| Module | Responsibility | Location |
|--------|---------------|----------|
| **scanner** | Analyze conversations, extract article ideas, score them | `apps/pipeline` |
| **generator** | idea -> outline -> JA/EN draft via LLM | `apps/pipeline` |
| **reviewer** | LLM quality gate (quality, fact-check, tone, voice) | `apps/pipeline` |
| **publisher** | Orchestrate publishing to all platforms | `apps/pipeline` |
| **slack** | Notifications, approval management | `apps/pipeline` |
| **adapters** | Platform-specific API abstraction | `libs/adapters` |

## Pipeline Detail

### Scanner

1. Fetch recent conversations from MindBase DB (or full history for backfill)
2. Semantic analysis to extract topics and potential article angles
3. Score each idea:
   - Novelty (dedup against past articles)
   - Technical depth
   - Story potential (failure -> resolution arc)
4. Select top candidates, save to `article_ideas` table

### Generator

1. Take selected idea, generate article outline
2. Generate Japanese article body (failure-first storytelling, includes code/config examples)
3. Generate English version (not translation -- rewrite for English audience, adjust cultural context)
4. Save drafts to `article_drafts` table with status `pending`

### LLM Reviewer

1. Quality check (coherence, readability, value to reader)
2. Fact check (code examples actually work, config is accurate)
3. Tone check (matches kazuki's voice, not generic AI tone)
4. Pass/fail decision with comments
5. Update draft status to `approved` or `needs_review`

### Publisher

1. Publish to corporate site first (canonical source)
2. Publish to each platform with canonical URL pointing to corporate
3. Record all URLs in `article_publications` table
4. Send Slack completion report

## Data Model

```sql
-- Article ideas (scanner output)
article_ideas (
  id UUID PK,
  conversation_ids UUID[],        -- source conversations
  topic TEXT,
  angle TEXT,                     -- e.g. 'failure-story', 'tips', 'deep-dive'
  score FLOAT,
  status TEXT CHECK (status IN ('candidate', 'selected', 'used', 'rejected')),
  created_at TIMESTAMPTZ
)

-- Article drafts (generator output)
article_drafts (
  id UUID PK,
  idea_id UUID FK -> article_ideas,
  language TEXT CHECK (language IN ('ja', 'en')),
  title TEXT,
  body TEXT,                      -- Markdown
  review_status TEXT CHECK (review_status IN ('pending', 'approved', 'rejected', 'needs_review')),
  review_comment TEXT,
  created_at TIMESTAMPTZ
)

-- Publication records (publisher output)
article_publications (
  id UUID PK,
  draft_id UUID FK -> article_drafts,
  platform TEXT,                  -- 'corporate', 'qiita', 'zenn', 'note', 'devto', 'hashnode'
  canonical_url TEXT,
  published_url TEXT,
  status TEXT CHECK (status IN ('published', 'failed', 'unpublished')),
  published_at TIMESTAMPTZ
)
```

Relationships:
- 1 idea -> 2 drafts (JA + EN)
- 1 draft -> N publications (JA draft -> corporate/qiita/zenn/note, EN draft -> corporate/devto/hashnode)
- conversation_ids traces back to source material (useful for future book compilation)

## Platform Adapters

| Adapter | Language | Method | Canonical URL |
|---------|----------|--------|---------------|
| **corporate** | ja/en | Git push -> Next.js build (ISR/SSG) | This IS the canonical |
| **qiita** | ja | REST API v2 | corporate JA URL |
| **zenn** | ja | GitHub repo push | Footer link (no canonical support) |
| **note** | ja | Playwright headless browser | Footer link (no API) |
| **devto** | en | Forem REST API (`canonical_url` field) | corporate EN URL |
| **hashnode** | en | GraphQL API (`originalArticleURL`) | corporate EN URL |
| **x** | ja/en | X API v2 (`twitter-api-v2`) Free tier | Link to corporate |
| **instagram-feed** | ja/en | Instagram Graph API | Link to corporate |
| **instagram-stories** | ja/en | Ayrshare API ($29/month) | N/A (visual only) |

### SNS Adapters (X + Instagram)

Two posting modes for SNS adapters:
1. **Article promotion** — "New article published" + excerpt + URL to corporate site. Auto-generated when a blog article is published.
2. **Standalone post** — Independent SNS content (text + image). Can be triggered manually or generated from conversation insights.

### X (Twitter) Adapter

- Library: `twitter-api-v2` (TypeScript native)
- Auth: OAuth 1.0a (Free tier: 1,500 tweets/month, $0)
- Supports: text, text + image (via media upload v1.1), link cards (automatic from URL)
- Rate limit: 200 requests/15min per user

### Instagram Feed Adapter

- Method: Instagram Graph API direct (`POST /{ig-user-id}/media` → `POST /{ig-user-id}/media_publish`)
- Requirements: Instagram Business Account + Facebook Page + App Review
- Supports: single image, carousel, reels
- Constraint: image must be hosted at public URL (upload to corporate site or R2 first)
- Rate limit: 25 posts/24h
- Cost: $0

### Instagram Stories Adapter

- Method: Ayrshare API (official Instagram partner)
- Cost: ~$29/month
- Supports: image stories, video stories
- Simple REST API: `POST /api/post` with `isStory: true`

### note.com Special Handling

note has no public API. Publish via Playwright headless browser automation. Fallback to manual if automation breaks.

### Zenn Special Handling

Zenn uses GitHub integration only (no API). Push Markdown to a dedicated Zenn repository. Canonical URL not supported by Zenn; include original link in article footer.

## Tech Stack

- All TypeScript (no Python in pipeline containers)
- LLM: Claude API (Anthropic SDK) for generation and review
- DB: Existing PostgreSQL + pgvector
- Slack: `@slack/web-api`
- X: `twitter-api-v2`
- Instagram: Graph API direct + Ayrshare API (Stories)
- Playwright: note.com adapter only
- Single multi-stage Dockerfile
- Docker Compose service: `pipeline`

## SEO Strategy

- Corporate site is canonical source for all articles
- Same content across platforms is fine with canonical URLs set correctly
- Multi-language content is NOT duplicate (Google treats different languages as separate)
- hreflang tags on corporate site to cross-reference JA/EN versions

## Content Strategy

- **Theme**: Claude Code mastery, AI-assisted development
- **Tone**: Failure-first storytelling. "I tried X, it broke because Y, finally Z worked"
- **Audience JA**: Engineers (Qiita/Zenn), business/non-tech (note), general (X/Instagram)
- **Audience EN**: Global dev community (dev.to/Hashnode), general (X/Instagram)
- **SNS strategy**: Article promotions + standalone insights. X for tech audience, Instagram for broader reach
- **Future**: Article metadata (theme, timeline, tags) enables automatic book chapter proposal

## Verification Plan

1. **Scanner**: Run against existing conversation data, verify topic extraction quality
2. **Generator**: Feed 1 idea manually, verify JA/EN article output quality
3. **Reviewer**: Pass generated articles through LLM review, verify pass/fail accuracy
4. **Adapters**: Test publish to each platform in draft mode
5. **E2E**: Full cron -> scan -> generate -> review -> publish -> Slack notification flow
6. **Backfill**: Run full history scan, verify idea dedup and volume

## Pre-Implementation: Manual First Article

Before building any of this pipeline, manually write and publish 1 article using Claude Code conversation. This validates:
- Article tone and structure
- Reader reception
- Platform publishing flow (manual)

Only proceed to pipeline implementation after the first article is published and evaluated.
