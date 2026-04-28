# MCPs Used by the Execution Layer

The Execution Layer of AlphaZero can search the open web and several social platforms while it runs. This is implemented through Model Context Protocol (MCP) servers configured against Claude Code; each MCP exposes a small set of tools that any subagent can call from inside a replication task. The result is that the Execution Layer is not a closed-world reasoner: even after a paper has been ingested and a plan has been drawn up, the agent can pull in fresh information from the web and from social platforms and weave it into the analysis.

## Servers at a glance

| Category    | MCP server      | Where it comes from                                  | Auth                        |
| ----------- | --------------- | ---------------------------------------------------- | --------------------------- |
| Sentiment   | `xai` (Grok)    | xAI official, accessed via the Grok API              | API key                     |
| Web         | `brave-search`  | Anthropic-curated, `@modelcontextprotocol/server-brave-search` | API key                     |
| Web         | `fetch`         | Anthropic-curated, `@modelcontextprotocol/server-fetch` | none                        |
| Social      | `rednote-mcp`   | Community, cookie-based login                        | one-time browser login      |
| Social      | `weixin-search` | Community, wraps Sogou's WeChat search endpoint      | none for search, cookie for full article body |
| Social      | `zhihu`         | Planned, no canonical community implementation as of 2026-04 | community-build TBD         |

The conventional Claude Code config locations are `~/.claude/.mcp.json` (global, all sessions) and `<project>/.mcp.json` (project-local). Servers may also arrive through the plugin system: a Claude Code plugin can ship its own MCP server bundled, in which case nothing needs to be added to `.mcp.json`. The `~/.claude/settings.json` field `enableAllProjectMcpServers: true` is what unlocks project-local servers, and `enabledMcpjsonServers` is the explicit allowlist for globally-installed ones.

## 1. xai (Grok)

xAI's Grok API can be exposed as an MCP server, which gives the orchestrator access to Grok models and, more importantly for replication work, to xAI's real-time X-search tooling. When a paper makes a claim about retail or institutional reaction to a market event, the agent can ask Grok to fetch and rank X posts from the relevant window without leaving the loop.

Sign up at <https://console.x.ai/> for an API key, then add to your MCP config:

```json
{
  "mcpServers": {
    "Grok": {
      "command": "npx",
      "args": ["-y", "@xai-org/mcp-server"],
      "env": { "XAI_API_KEY": "xai-..." }
    }
  }
}
```

The exact npm package name has been moving around, so confirm the current canonical name with `npm search "@xai" 2026` or via the xAI docs portal before pinning it. Smoke test: ask the agent to "search X for posts mentioning AAPL earnings on 2026-01-30 and rank them by engagement".

## 2. brave-search

`brave-search` proxies the Brave Search API. The free tier covers 2000 queries per month, which is comfortably above what a single replication task consumes. Brave is a good default because it returns clean, low-spam results and supports a `freshness` parameter that the agent can use when it needs results from a specific window.

Sign up at <https://api.search.brave.com/>, then:

```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": { "BRAVE_API_KEY": "BSA..." }
    }
  }
}
```

Smoke test: "Search the web for the Dugast Marta Riva 2026 paper on market depth and execution delays, find the SSRN abstract".

## 3. fetch

`fetch` is a small Anthropic-curated MCP that lets the agent retrieve and parse a URL. It complements `brave-search` neatly: brave returns titles and snippets, and fetch follows the link and pulls the body. This is the path the agent uses to read paper landing pages, GitHub READMEs, and supplementary tables that are not in the local PDF.

```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

No API key. Smoke test: "Fetch <https://arxiv.org/abs/2312.00752> and summarise the abstract".

## 4. rednote-mcp

`rednote-mcp` is a community-built MCP for Xiaohongshu / "rednote". The platform does not expose a public API, so the MCP authenticates by reusing a browser session cookie: the user runs `rednote-mcp login` once, completes the captcha in a launched browser, and the MCP stores the session cookie locally for future requests. From then on the agent can search posts, read comments, and pull engagement metadata.

```bash
npm install -g rednote-mcp     # confirm exact package name on the project's GitHub
rednote-mcp login              # one-time browser auth, stores ~/.rednote-cookie
```

```json
{
  "mcpServers": {
    "rednote-mcp": {
      "command": "rednote-mcp",
      "args": ["serve"]
    }
  }
}
```

Smoke test: "Search rednote for posts tagged 量化交易 in the last seven days, return top ten by engagement".

## 5. weixin-search

`weixin-search` is a community MCP that wraps Sogou's WeChat search endpoint. Search itself does not require auth (Sogou's WeChat index is public-readable); fetching full article bodies sometimes requires a cookie when the article is paywalled or visibility-restricted. Even unauthenticated, the search-only path is enough to discover relevant posts and titles.

```json
{
  "mcpServers": {
    "weixin-search": {
      "command": "npx",
      "args": ["-y", "weixin-search-mcp"]
    }
  }
}
```

Smoke test: "weixin_search for posts about 'NVDA 2026 财报'".

## 6. zhihu (planned)

As of 2026-04 there is no canonical packaged MCP for Zhihu. The shape would mirror `weixin-search` (wrap the public search endpoint) and `rednote-mcp` (cookie-based login when the request needs a logged-in session). A natural place to put a self-built one is `auto-quant-research/execution-layer/mcps/zhihu/`. Pull requests welcome.

## Combined loadout used in production

For AlphaZero, the project-local `.mcp.json` registers all five active servers, and the Claude Code allowlist in `~/.claude/settings.json` permits each individual tool name. A representative slice of `permissions.allow`:

```json
"mcp__Grok__search_x",
"mcp__Grok__chat",
"mcp__brave-search__search",
"mcp__fetch__fetch",
"mcp__rednote-mcp__search_notes",
"mcp__rednote-mcp__get_note_content",
"mcp__rednote-mcp__get_note_comments",
"mcp__weixin-search__weixin_search",
"mcp__weixin-search__weixin_search_all",
"mcp__weixin-search__get_weixin_article_content"
```

You can also enable everything under a server with a wildcard, for example `"mcp__Grok__*"`. The narrower per-tool form is preferred because it makes the allowlist self-documenting: a reviewer can see exactly which capabilities the agent is permitted to use.

## How the agent actually uses these during a replication task

During a paper replication, the orchestrator typically invokes the search MCPs in three places. First, during spec extraction, when the local paper PDF is missing a referenced supplementary table, the agent calls `fetch` against the journal landing page or the author's GitHub repo and parses the table out of the page. Second, during empirical validation, when a finding hinges on a real-world event, the agent uses `xai/Grok` to pull X posts from the relevant trading window and `rednote-mcp` or `weixin-search` to read retail-investor commentary in Chinese-speaking markets. Third, during methodology cross-check, the agent searches recent arXiv preprints and technical blogs through `brave-search` and follows the leads with `fetch`, looking for newer or alternative estimators of the same quantity that might tighten the replication.

The point of describing all five together is that none of them is special on its own. Web search alone would not get you sentiment from Chinese platforms; sentiment alone would not get you methodology cross-checks. The shape of the Execution Layer is that the agent has both a wide-angle lens (web search) and several narrow-angle ones (specific platforms with structured semantics), and it can cycle between them in a single replication.

## Last updated

2026-04-28.
