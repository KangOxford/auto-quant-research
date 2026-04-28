#!/usr/bin/env bash
# Unit tests for translate-prompt-stop.sh
#
# Run: bash ~/.claude/hooks/test_translate_prompt_stop.sh

set -u

# Source the hook script. The BASH_SOURCE guard prevents main() from running.
source "$(dirname "${BASH_SOURCE[0]}")/translate-prompt-stop.sh"

PASS=0
FAIL=0

assert_eq() {
    local expected="$1" actual="$2" label="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label"
        echo "    expected: $(printf '%q' "$expected")"
        echo "    actual:   $(printf '%q' "$actual")"
        FAIL=$((FAIL+1))
    fi
}

assert_true() {
    local cmd="$1" label="$2"
    if eval "$cmd"; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label (expected true)"
        FAIL=$((FAIL+1))
    fi
}

assert_false() {
    local cmd="$1" label="$2"
    if ! eval "$cmd"; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label (expected false)"
        FAIL=$((FAIL+1))
    fi
}

echo "=== translate-prompt-stop.sh tests ==="

# -----------------------------------------------------------------------------
echo ""
echo "--- extract_last_user_prompt ---"

# Test 1: simple text user prompt
TMP=$(mktemp)
cat > "$TMP" << 'EOF'
{"type":"user","message":{"role":"user","content":"帮我修bug"},"timestamp":"2026-04-18T10:00:00Z"}
{"type":"assistant","message":{"role":"assistant","content":"OK"},"timestamp":"2026-04-18T10:00:05Z"}
{"type":"user","message":{"role":"user","content":"另一个问题"},"timestamp":"2026-04-18T10:01:00Z"}
EOF
assert_eq "另一个问题" "$(extract_last_user_prompt "$TMP")" "returns LAST user prompt"
rm "$TMP"

# Test 2: skip tool_result (content is array, not string)
TMP=$(mktemp)
cat > "$TMP" << 'EOF'
{"type":"user","message":{"role":"user","content":"看下这个"},"timestamp":"2026-04-18T10:00:00Z"}
{"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"..."}]},"timestamp":"2026-04-18T10:00:05Z"}
EOF
assert_eq "看下这个" "$(extract_last_user_prompt "$TMP")" "skips tool_result messages"
rm "$TMP"

# Test 3: empty transcript
TMP=$(mktemp); echo "" > "$TMP"
assert_eq "" "$(extract_last_user_prompt "$TMP")" "empty transcript returns empty"
rm "$TMP"

# Test 4: missing file returns empty
assert_eq "" "$(extract_last_user_prompt /nonexistent)" "missing file returns empty"

# -----------------------------------------------------------------------------
echo ""
echo "--- should_translate ---"

assert_true  'should_translate "帮我修这个 bug"' "Chinese with English terms"
assert_false 'should_translate "fix this bug please"' "pure English"
# Too long: generate a 600-char Chinese string
LONG=$(printf '测试%.0s' {1..301})  # 301 repeats of "测试" = 602 chars
assert_false "should_translate \"\$LONG\"" "too long (>500 chars)"
assert_false 'should_translate "帮我看这段代码 \`\`\`python
print(1)
\`\`\`"' "contains code fence"
assert_false 'should_translate ""' "empty string"
assert_true  'should_translate "这是中文"' "pure short Chinese"
# 5 Chinese + many English → <30% Chinese → reject
assert_false 'should_translate "你好 hello world foo bar baz something"' "below 30% Chinese"

# -----------------------------------------------------------------------------
echo ""
echo "--- dedup (already_translated / mark_translated) ---"

TEST_SID="test-session-$$"
HASH_FILE="/tmp/claude-last-translated-${TEST_SID}.hash"
rm -f "$HASH_FILE"

assert_false "already_translated 'hello' '$TEST_SID'" "no hash file → not translated yet"
mark_translated "hello" "$TEST_SID"
assert_true  "already_translated 'hello' '$TEST_SID'" "same prompt after mark → translated"
assert_false "already_translated 'hello world' '$TEST_SID'" "different prompt → not translated"
mark_translated "hello world" "$TEST_SID"
assert_true  "already_translated 'hello world' '$TEST_SID'" "new prompt marked → now translated"
assert_false "already_translated 'hello' '$TEST_SID'" "old prompt now stale (single slot)"

rm -f "$HASH_FILE"

# -----------------------------------------------------------------------------
echo ""
echo "--- emit_system_message ---"

output=$(emit_system_message "Hello, world")
# Verify it's valid JSON and contains both our emoji and the translation
if echo "$output" | jq . > /dev/null 2>&1; then
    msg=$(echo "$output" | jq -r '.systemMessage')
    if echo "$msg" | grep -q "🌐 Translation reference" && echo "$msg" | grep -q "Hello, world"; then
        echo "  PASS: emits valid JSON with emoji + translation"
        PASS=$((PASS+1))
    else
        echo "  FAIL: JSON valid but content wrong: $msg"
        FAIL=$((FAIL+1))
    fi
else
    echo "  FAIL: output invalid JSON: $output"
    FAIL=$((FAIL+1))
fi

# Edge: translation with quotes/newlines
output=$(emit_system_message 'He said "hi"
and bye')
if echo "$output" | jq . > /dev/null 2>&1; then
    echo "  PASS: output is valid JSON with special chars"
    PASS=$((PASS+1))
else
    echo "  FAIL: output invalid JSON with special chars: $output"
    FAIL=$((FAIL+1))
fi

# -----------------------------------------------------------------------------
echo ""
echo "--- call_translator (live API) ---"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    echo "  SKIP: OPENROUTER_API_KEY not set (live API tests need key)"
else
    result=$(call_translator "你好，世界")
    if [ -n "$result" ]; then
        if echo "$result" | grep -qiE 'hello|hi|world'; then
            echo "  PASS: 你好世界 → contains hello/world: $result"
            PASS=$((PASS+1))
        else
            echo "  FAIL: translation missing expected words: $result"
            FAIL=$((FAIL+1))
        fi
    else
        echo "  FAIL: call_translator returned empty"
        FAIL=$((FAIL+1))
    fi

    # Timeout behavior: bad key → should return empty in <8s
    OPENROUTER_API_KEY_BAK="$OPENROUTER_API_KEY"
    export OPENROUTER_API_KEY="invalid-key"
    start=$(date +%s)
    bad_result=$(call_translator "你好")
    end=$(date +%s)
    assert_eq "" "$bad_result" "bad key returns empty"
    elapsed=$((end - start))
    if [ $elapsed -lt 8 ]; then
        echo "  PASS: failed in ${elapsed}s (<8s)"
        PASS=$((PASS+1))
    else
        echo "  FAIL: took ${elapsed}s (timeout not working)"
        FAIL=$((FAIL+1))
    fi
    export OPENROUTER_API_KEY="$OPENROUTER_API_KEY_BAK"
fi

# -----------------------------------------------------------------------------
echo ""
echo "Total: $((PASS+FAIL)) | Pass: $PASS | Fail: $FAIL"
exit $FAIL
