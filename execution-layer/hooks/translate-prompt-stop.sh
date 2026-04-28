#!/usr/bin/env bash
# Stop hook: translate user's Chinese prompt to English for language learning.
#
# Triggered after every Claude response. Reads last user prompt from transcript,
# filters (<=500 Chinese chars, >=30% Chinese, no code fence, deduped),
# calls OpenRouter deepseek/deepseek-chat:free, emits systemMessage.
#
# Design: ~/.claude/docs/plans/2026-04-18-prompt-translate-hook-design.md
# Plan:   ~/.claude/docs/plans/2026-04-18-prompt-translate-hook-implementation.md
# Tests:  ~/.claude/hooks/test_translate_prompt_stop.sh

set -uo pipefail

# CRITICAL: Force UTF-8 locale unconditionally. Claude Code may spawn hooks with
# LC_ALL=C or POSIX pre-set, and ${LC_ALL:-C.UTF-8} would NOT override those.
# Without UTF-8:
#   - wc -m counts bytes, not chars ("你" = 3 instead of 1)
#   - grep -P '[\x{4e00}-\x{9fff}]' matches 0 (Unicode range not parsed)
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Debug log — every invocation, even if skipped. Tail this to diagnose.
DEBUG_LOG="$HOME/.claude/hook-debug.log"
echo "$(date '+%F %T') translate-stop invoked (pid=$$)" >> "$DEBUG_LOG" 2>/dev/null

# Fail-safe env loading: Claude Code spawns hooks in non-interactive bash which
# does NOT source ~/.bashrc, so OPENROUTER_API_KEY won't be inherited unless the
# user exported it before launching Claude Code. Grep only the specific export
# line to avoid full ~/.bashrc side effects (prompt, functions, etc.).
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -f "$HOME/.bashrc" ]; then
    eval "$(grep '^export OPENROUTER_API_KEY=' "$HOME/.bashrc" 2>/dev/null)" || true
fi

# -----------------------------------------------------------------------------
# extract_last_user_prompt <transcript_path>
#   Read JSONL transcript, return content of LAST user message whose
#   .message.content is a plain string (skip tool_result messages).
# -----------------------------------------------------------------------------
extract_last_user_prompt() {
    local transcript="$1"
    [ -f "$transcript" ] || { echo ""; return 0; }

    tail -n 500 "$transcript" 2>/dev/null \
      | jq -r 'select(.type=="user" and (.message.content | type == "string")) | .message.content' 2>/dev/null \
      | tail -1
}

# -----------------------------------------------------------------------------
# should_translate <prompt>
#   Return 0 if prompt should be translated (<=500 chars, >=30% Chinese, no fence).
# -----------------------------------------------------------------------------
should_translate() {
    local prompt="$1"

    [ -z "$prompt" ] && return 1

    case "$prompt" in
        *'```'*) return 1 ;;
    esac

    local total
    total=$(printf '%s' "$prompt" | wc -m)
    [ "$total" -eq 0 ] && return 1
    [ "$total" -gt 500 ] && return 1

    local chinese
    chinese=$(printf '%s' "$prompt" | grep -oP '[\x{4e00}-\x{9fff}]' 2>/dev/null | wc -l)

    [ "$((chinese * 100))" -ge "$((total * 30))" ] || return 1

    return 0
}

# -----------------------------------------------------------------------------
# already_translated <prompt> <session_id>
#   Return 0 if prompt hash matches the one stored for this session.
# -----------------------------------------------------------------------------
already_translated() {
    local prompt="$1" sid="$2"
    local hash_file="/tmp/claude-last-translated-${sid}.hash"
    [ -f "$hash_file" ] || return 1

    local hash stored
    hash=$(printf '%s' "$prompt" | sha256sum | cut -d' ' -f1)
    stored=$(cat "$hash_file" 2>/dev/null)
    [ "$hash" = "$stored" ]
}

# -----------------------------------------------------------------------------
# mark_translated <prompt> <session_id>
#   Overwrite the per-session hash file with this prompt's hash.
# -----------------------------------------------------------------------------
mark_translated() {
    local prompt="$1" sid="$2"
    local hash_file="/tmp/claude-last-translated-${sid}.hash"
    printf '%s' "$prompt" | sha256sum | cut -d' ' -f1 > "$hash_file"
}

# -----------------------------------------------------------------------------
# call_translator <prompt>
#   Call OpenRouter DeepSeek V3 free tier, return translation or empty on any
#   failure (missing key, timeout, API error, empty response).
# -----------------------------------------------------------------------------
call_translator() {
    local prompt="$1"
    [ -z "${OPENROUTER_API_KEY:-}" ] && { echo ""; return 0; }

    local payload
    # Few-shot examples significantly raise Liquid 1.2B translation quality
    # (see 2026-04-18 benchmark: 0.7s, "Once upon a time" cultural idiom match).
    local sys_prompt='You translate Chinese to English. Output ONLY the translation, nothing else. Keep code, paths, identifiers verbatim.

Example 1:
Chinese: 今天天气很好
English: The weather is great today.

Example 2:
Chinese: 帮我修这个 bug
English: Help me fix this bug.

Example 3:
Chinese: 从前有座山
English: Once upon a time, there was a mountain.

Now translate:'

    payload=$(jq -n --arg p "$prompt" --arg sys "$sys_prompt" '{
        model: "liquid/lfm-2.5-1.2b-instruct:free",
        messages: [
            {role: "system", content: $sys},
            {role: "user", content: $p}
        ],
        max_tokens: 300,
        temperature: 0.1
    }' 2>/dev/null) || { echo ""; return 0; }

    local response
    response=$(curl -s -m 8 https://openrouter.ai/api/v1/chat/completions \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || { echo ""; return 0; }

    echo "$response" | jq -r '.choices[0].message.content // empty' 2>/dev/null
}

# -----------------------------------------------------------------------------
# emit_system_message <prompt> <translation>
#   Print compact JSON with bilingual side-by-side format so user can compare
#   original Chinese with English translation for language learning.
# -----------------------------------------------------------------------------
emit_system_message() {
    local prompt="$1" translation="$2"
    jq -nc --arg msg "🌐 Translation reference
CN $prompt
EN $translation" '{systemMessage: $msg}'
}

# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
_dlog() { echo "$(date '+%F %T') $1" >> "$DEBUG_LOG" 2>/dev/null; }

main() {
    local input
    input=$(cat)

    local session_id transcript_path
    session_id=$(echo "$input" | jq -r '.session_id // empty' 2>/dev/null)
    transcript_path=$(echo "$input" | jq -r '.transcript_path // empty' 2>/dev/null)

    [ -z "$session_id" ]          && { _dlog "exit: no session_id"; exit 0; }
    [ -z "$transcript_path" ]     && { _dlog "exit: no transcript_path"; exit 0; }
    [ ! -f "$transcript_path" ]   && { _dlog "exit: transcript file missing ($transcript_path)"; exit 0; }
    [ -z "${OPENROUTER_API_KEY:-}" ] && { _dlog "exit: OPENROUTER_API_KEY not set (bashrc fallback failed?)"; exit 0; }

    local prompt
    prompt=$(extract_last_user_prompt "$transcript_path")
    [ -z "$prompt" ] && { _dlog "exit: extract_last_user_prompt returned empty"; exit 0; }
    _dlog "extracted prompt (len=${#prompt}): ${prompt:0:80}"

    if ! should_translate "$prompt"; then
        local total chinese
        total=$(printf '%s' "$prompt" | wc -m)
        chinese=$(printf '%s' "$prompt" | grep -oP '[\x{4e00}-\x{9fff}]' 2>/dev/null | wc -l)
        _dlog "exit: should_translate=false (total=$total chinese=$chinese)"
        exit 0
    fi

    if already_translated "$prompt" "$session_id"; then
        _dlog "exit: already_translated for session $session_id"
        exit 0
    fi

    local translation
    translation=$(call_translator "$prompt")
    if [ -z "$translation" ]; then
        _dlog "exit: call_translator returned empty (API/timeout/parse error)"
        exit 0
    fi
    _dlog "got translation (len=${#translation}): ${translation:0:80}"

    mark_translated "$prompt" "$session_id"
    emit_system_message "$prompt" "$translation"
    _dlog "emitted systemMessage successfully"
}

# Only run main if executed directly (allows test file to source functions)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main
fi
