#!/usr/bin/env bash
# E2E smoke test for translate-prompt-stop.sh main() pipeline.
# Mocks call_translator to avoid real API dependency.
#
# Run: bash ~/.claude/hooks/e2e_smoke_translate.sh

set -u

HOOK="$HOME/.claude/hooks/translate-prompt-stop.sh"
PASS=0
FAIL=0

report() {
    local label="$1" result="$2"
    if [ "$result" = "0" ]; then
        echo "  PASS: $label"
        PASS=$((PASS+1))
    else
        echo "  FAIL: $label"
        FAIL=$((FAIL+1))
    fi
}

# -----------------------------------------------------------------------------
# Helper: run a mocked hook with given input JSON and transcript content.
# The mock overrides call_translator to return a fixed string, simulating API.
# -----------------------------------------------------------------------------
run_mocked_hook() {
    local input_json="$1" transcript_content="$2" mock_translation="$3"

    local transcript
    transcript=$(mktemp)
    printf '%s' "$transcript_content" > "$transcript"

    local sid
    sid=$(echo "$input_json" | jq -r '.session_id')
    local hash_file="/tmp/claude-last-translated-${sid}.hash"
    # Don't pre-clean — caller can set up dedup state first

    local full_input
    full_input=$(echo "$input_json" | jq --arg p "$transcript" '.transcript_path = $p')

    # Create a wrapper that sources the hook, overrides call_translator, runs main
    local output
    output=$(bash -c "
        source '$HOOK'
        export OPENROUTER_API_KEY='fake-key-for-mock'
        call_translator() { echo '$mock_translation'; }
        main
    " <<< "$full_input" 2>&1)

    local exit_code=$?
    echo "---INPUT--- $full_input"
    echo "---OUTPUT--- $output"
    echo "---EXIT--- $exit_code"
    rm -f "$transcript"

    # Return output via global var (bash can't return strings cleanly)
    LAST_OUTPUT="$output"
    LAST_EXIT="$exit_code"
}

echo "=== E2E smoke tests ==="

# -----------------------------------------------------------------------------
echo ""
echo "--- Scenario 1: Chinese short prompt → expect systemMessage output ---"

SID="e2e-s1-$$"
rm -f "/tmp/claude-last-translated-${SID}.hash"

TRANSCRIPT='{"type":"user","message":{"role":"user","content":"帮我设置一个翻译 hook"},"timestamp":"2026-04-18T10:00:00Z"}'
INPUT_JSON="{\"session_id\":\"$SID\"}"
MOCK_ENGLISH="Help me set up a translation hook"

run_mocked_hook "$INPUT_JSON" "$TRANSCRIPT" "$MOCK_ENGLISH"

# Expect output: valid JSON with systemMessage containing the English translation
if echo "$LAST_OUTPUT" | tail -1 | jq . > /dev/null 2>&1; then
    MSG=$(echo "$LAST_OUTPUT" | tail -1 | jq -r '.systemMessage // empty')
    if echo "$MSG" | grep -q "$MOCK_ENGLISH"; then
        report "S1 emits systemMessage with translation" 0
    else
        report "S1 systemMessage content wrong (got: $MSG)" 1
    fi
else
    report "S1 output is not valid JSON" 1
fi

# Cleanup
rm -f "/tmp/claude-last-translated-${SID}.hash"

# -----------------------------------------------------------------------------
echo ""
echo "--- Scenario 2: English prompt → expect NO output (filter rejects) ---"

SID="e2e-s2-$$"
rm -f "/tmp/claude-last-translated-${SID}.hash"

TRANSCRIPT='{"type":"user","message":{"role":"user","content":"fix this bug please"},"timestamp":"2026-04-18T10:00:00Z"}'
INPUT_JSON="{\"session_id\":\"$SID\"}"

run_mocked_hook "$INPUT_JSON" "$TRANSCRIPT" "UNEXPECTED"

# Expect empty output after filtering the debug lines
REAL_OUTPUT=$(echo "$LAST_OUTPUT" | grep -v '^---' || true)
if [ -z "$REAL_OUTPUT" ]; then
    report "S2 English prompt correctly skipped" 0
else
    report "S2 produced unexpected output: $REAL_OUTPUT" 1
fi

rm -f "/tmp/claude-last-translated-${SID}.hash"

# -----------------------------------------------------------------------------
echo ""
echo "--- Scenario 3: Dedup — same prompt twice → second skipped ---"

SID="e2e-s3-$$"
rm -f "/tmp/claude-last-translated-${SID}.hash"

TRANSCRIPT='{"type":"user","message":{"role":"user","content":"你好世界"},"timestamp":"2026-04-18T10:00:00Z"}'
INPUT_JSON="{\"session_id\":\"$SID\"}"

# First run — should translate
run_mocked_hook "$INPUT_JSON" "$TRANSCRIPT" "Hello world"
FIRST_OUTPUT=$(echo "$LAST_OUTPUT" | tail -1)

# Second run — should be deduped (empty output)
run_mocked_hook "$INPUT_JSON" "$TRANSCRIPT" "Hello world"
SECOND_REAL=$(echo "$LAST_OUTPUT" | grep -v '^---' || true)

if echo "$FIRST_OUTPUT" | jq . > /dev/null 2>&1 && [ -z "$SECOND_REAL" ]; then
    report "S3 first run translates, second run deduped" 0
else
    report "S3 dedup failed. First: $FIRST_OUTPUT | Second real: $SECOND_REAL" 1
fi

rm -f "/tmp/claude-last-translated-${SID}.hash"

# -----------------------------------------------------------------------------
echo ""
echo "--- Scenario 4: Code block in prompt → expect NO output ---"

SID="e2e-s4-$$"
rm -f "/tmp/claude-last-translated-${SID}.hash"

TRANSCRIPT='{"type":"user","message":{"role":"user","content":"帮我看代码 ```print(1)```"},"timestamp":"2026-04-18T10:00:00Z"}'
INPUT_JSON="{\"session_id\":\"$SID\"}"

run_mocked_hook "$INPUT_JSON" "$TRANSCRIPT" "UNEXPECTED"
REAL_OUTPUT=$(echo "$LAST_OUTPUT" | grep -v '^---' || true)

if [ -z "$REAL_OUTPUT" ]; then
    report "S4 code-fence prompt correctly skipped" 0
else
    report "S4 produced unexpected output: $REAL_OUTPUT" 1
fi

rm -f "/tmp/claude-last-translated-${SID}.hash"

# -----------------------------------------------------------------------------
echo ""
echo "--- Scenario 5: Missing OPENROUTER_API_KEY → expect NO output ---"

SID="e2e-s5-$$"
rm -f "/tmp/claude-last-translated-${SID}.hash"

TRANSCRIPT='{"type":"user","message":{"role":"user","content":"这是中文"},"timestamp":"2026-04-18T10:00:00Z"}'
TMP_TRANSCRIPT=$(mktemp)
printf '%s' "$TRANSCRIPT" > "$TMP_TRANSCRIPT"

# Explicitly unset key
INPUT_JSON="{\"session_id\":\"$SID\",\"transcript_path\":\"$TMP_TRANSCRIPT\"}"
OUTPUT=$(bash -c "unset OPENROUTER_API_KEY; bash '$HOOK'" <<< "$INPUT_JSON" 2>&1)
EXIT=$?
rm -f "$TMP_TRANSCRIPT" "/tmp/claude-last-translated-${SID}.hash"

if [ -z "$OUTPUT" ] && [ "$EXIT" = "0" ]; then
    report "S5 missing key → silent skip + exit 0" 0
else
    report "S5 unexpected behavior: OUTPUT=$OUTPUT EXIT=$EXIT" 1
fi

# -----------------------------------------------------------------------------
echo ""
echo "E2E Total: $((PASS+FAIL)) | Pass: $PASS | Fail: $FAIL"
exit $FAIL
