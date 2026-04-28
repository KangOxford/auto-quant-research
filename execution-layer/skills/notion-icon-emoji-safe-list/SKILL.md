---
name: notion-icon-emoji-safe-list
description: Quick reference for which emoji are accepted as Notion page icon. Notion API rejects some emoji classes with HTTP 400 — this skill lists safe vs unsafe emoji and provides defensive fallback pattern. Trigger on "notion page icon", "POST /v1/pages icon", "Notion 400 emoji", "notion API reject icon", or before bulk-creating Notion pages.
version: 1.0.0
allowed-tools: Read, Edit
alwaysApply: false
default-language: zh-CN
---

# Notion Icon Emoji Safe List

## When to Use

Anytime you set `"icon": {"type": "emoji", "emoji": "<X>"}` in `POST /v1/pages` or `PATCH /v1/pages/{id}`.

**Especially** when bulk-creating pages with letter/number/flag-style visual identifiers — Notion is picky about which Unicode classes it accepts.

## The Problem

Notion API silently classifies emoji acceptability. Some emoji that render fine in Notion's UI as **inline text** are **rejected as page icons** with HTTP 400.

Without this list, you discover this only when an agent crashes mid-bulk-create.

## Safe vs Unsafe (verified 2026-04 with Notion API v2022-06-28)

### ✅ SAFE — picture emoji (objects / symbols / animals)

```
🐍 🐉 📊 📈 📐 📏 ⚡ 🔬 🔥 💾 🌙 🎯 🎓 🎛️ 🎚️
🍰 📦 📚 🔡 🔢 🔄 🔧 🔍 🔗 🌐 🌊 ♻️ 🧠 🧰 🤖
🎬 🪝 ⚙️ ⏱️ ⏰ ⏪ 🚀 0️⃣ 📝 🎤 📄 🐞 🚫 ⚖️
```

These are all single-codepoint or properly-formed VS-16 sequences.

### ❌ UNSAFE — regional indicators (country flag base)

```
🇦 🇧 🇨 🇩 🇪 🇫 🇬 🇭 🇮 🇯 🇰 🇱 🇲 🇳 🇴 🇵 🇶 🇷 🇸 🇹 🇺 🇻 🇼 🇽 🇾 🇿
```

These are **regional indicator** symbols (U+1F1E6 - U+1F1FF). When used singly, Notion rejects them. (Two combined make country flags, but those also seem inconsistent — avoid the whole class.)

### ⚠️ INCONSISTENT — squared/enclosed letters

```
🅰️ 🅱️ ⚠️  partially worked in 2026-04-27 test (A/B accepted, D 🅳 rejected)
🅾️ 🅿️ — untested but likely same family
```

Don't rely on these. The variant selector behavior is fragile.

## Defensive Pattern

When you don't know if an emoji is safe, use this Python pattern:

```python
SAFE_FALLBACKS = {
    "🇦": "🅰️", "🇧": "🅱️",  # try squared first if available
    # but better: pick a thematic picture emoji
    "G": "🎛️", "H": "📊", "I": "📏",
    "J": "🌙", "K": "⚡", "L": "📝",
    "N": "🎯", "O": "🎓", "P": "🔡",
    "Q": "📈", "R": "🐍", "S": "💾",
    "D": "🐞",  # since 🅳 is unreliable
}

def create_with_icon_fallback(parent_id, title, icon, fallback_icon=None):
    body = {"parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": icon},
            "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
            "children": []}
    try:
        return api("POST", "/pages", body)
    except urllib.error.HTTPError as e:
        if e.code != 400 or not fallback_icon:
            raise
        body["icon"]["emoji"] = fallback_icon
        return api("POST", "/pages", body)
```

## Choosing an Icon

Default rule: **pick a picture emoji that conveys the topic**, not a letter/number decoration.

| Wrong choice | Correct choice |
|---|---|
| 🇰 (regional indicator for K) | ⚡ (theme: CUDA fast) |
| 🅷 (squared H) | 📊 (theme: scaling chart) |
| 🇷 | 🐍 (Mamba snake) |

The icon's job is **visual recognition**, not encoding the letter. Picture emoji do this better than typographic decorations anyway.

## Verification

After creating a page, the title shows in Notion sidebar with the emoji prepended. If the emoji shows as "?" or doesn't render, you got the wrong class — even if the API didn't 400.

```bash
# Visual check via API: GET page properties
curl -s "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $TOKEN" -H "Notion-Version: 2022-06-28" \
  | jq '.icon'
# Expect: {"type": "emoji", "emoji": "🐍"}
```

## Real-world Reference

Encoded from the 2026-04-27 LOBS5 auto-wiki bulk rebuild:
- Letters G/I/J/K/L/N/O/P/Q/R/S originally used regional indicators 🇬🇮🇯🇰🇱🇳🇴🇵🇶🇷🇸 → all rejected.
- Letter H used 🇭 → rejected; agent self-fixed to 📊.
- Letter D used 🅳 → rejected; agent self-fixed to 🐞.
- Letters A/B used 🅰️/🅱️ → succeeded (variant selector form), but unreliable for D.
- Standard picture emoji throughout the rest succeeded 100%.

## Anti-patterns

- ❌ Using regional indicators "for letter visual identity" — they're flags, not letters
- ❌ Encoding letters via squared/enclosed Unicode — fragile across emoji DBs
- ❌ Discovering which emoji work by trial-and-error in production bulk pipeline (use this list)
- ❌ Skipping the icon entirely (lose visual recognition in sidebar)
