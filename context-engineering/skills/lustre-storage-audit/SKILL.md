---
name: lustre-storage-audit
description: Audit Lustre project quota usage when approaching or exceeding cap. Avoids the four du landmines (symlink skip, perm-denied silent skip, audit-job killed by quota exceeded, xargs timeout drops biggest dir) by sbatching parallel du with off-quota output and cross-checking with `lfs quota -u`. Use when /lus quota approaches limit or has hit cap, when planning storage cleanup, or when du results don't match lfs quota total.
version: 1.0.0
allowed-tools: Bash, Write, Read
alwaysApply: false
---

# Lustre Storage Audit

## When to Use

- `lfs quota -p <pid> /lus/...` shows usage ≥ 90% of limit
- Quota star `200.2T*` indicates over-cap, writes are failing with `Disk quota exceeded`
- du-based estimates of subdirs do not sum to `lfs quota` total (gap > 5%)
- User asks "where is the storage going" / "find the biggest consumers" / "what is eating the 200T quota"
- Planning cleanup before sbatch big training data write

**Skip** if quota usage < 70% (audit cost > info value), or if the quota target is small (<100 GB, just `du -sh` it).

## The Four Landmines (why naive `du -sh /<dir>/*` is wrong)

A naive `du -sh /lus/lfs1aip2/projects/s5e/*` will **silently** undercount in four ways. All four hit on the same audit unless you avoid them:

| # | Landmine | Symptom | Fix |
|---|---|---|---|
| 1 | Symlink not followed | Top-level symlink (e.g. `s5e/public -> projects/public/s5e/`) skipped → 60+ TB invisible | `du -L` OR audit symlink target as a separate root. Default `du` policy is "no follow". |
| 2 | Perm-denied subdirs silently skipped | Owner-only `mode 2700` dir (e.g. `mbeukman/tmpdir/`, `eltayeb/singularity/user/...`) returns "Permission denied" but `2>/dev/null` swallows it. Project quota counts those bytes; du does not. | Cross-check with `lfs quota -u <user>` (authoritative, ignores perms). Mark dirs with stat mode `27..` as "owner-only, du underestimate". |
| 3 | Audit job killed by `Disk quota exceeded` mid-run | `tee` output to /lus/... fails when quota hits cap, exit 1, partial result lost | Write audit output to **off-quota path** (`/local/$USER/`, stdout-only, or `/tmp`). Or use `--quiet` and capture exit code. |
| 4 | `xargs -P` + `timeout` truncates biggest dir | Naive `timeout 1700 du -sb $d` on the largest dir gets killed at 1700s → entire dir's size never written, but loop reports "TOTAL audited: N dirs" without flagging the miss | Use `timeout 3600s` for known big dirs, OR audit big dirs in their own sbatch job, OR detect missing entries by counting `find` targets vs files in TMPD. |

## Process

### Step 0 — Quick triage (no sbatch needed)

```bash
# Quota current state. The `*` after used = over limit.
lfs quota -h -p $(lfs project -d /lus/lfs1aip2/projects/<your-project> 2>/dev/null | awk '{print $1}') /lus/lfs1aip2

# Per-user (authoritative, perm-blind). Use this as ground truth.
lfs quota -h -u <username> /lus/lfs1aip2
```

If quota is 100% (`*`), warn user before any further audit (the audit job itself can fail).

### Step 1 — Enumerate roots

Project quota aggregates by **project ID**, not by path. Find every directory tree counted under that ID:

```bash
# Confirm project ID
lfs project -d /lus/lfs1aip2/projects/<dir1>      # → e.g. 1483801312
lfs project -d /lus/lfs1aip2/projects/public/<dir1>  # → same ID? then both audit roots

# Find all symlinks pointing into the same project area (these are the hidden roots)
find /lus/lfs1aip2/projects/<dir1> -maxdepth 2 -type l -ls
```

Make a list of ROOTS that all map to the same project ID. Each is a separate audit root. **Do not assume one path covers it all.**

### Step 2 — sbatch parallel du with off-quota output

Output goes to `/local/$USER/` (node-local) or stdout. Do not write into the quota-target Lustre area:

```bash
#!/bin/bash
#SBATCH --job-name=storage-audit
#SBATCH --nodes=1 --gres=gpu:1 --cpus-per-task=64 --time=00:45:00
#SBATCH --output=/lus/<small-safe-area>/audit_%j.out  # stdout, OK because small

ROOTS=(/lus/lfs1aip2/projects/<dir1> /lus/lfs1aip2/projects/public/<dir1>)
TMPD=$(mktemp -d -p /local/$USER)  # off-quota
TARGETS=()
for R in "${ROOTS[@]}"; do
  while IFS= read -r d; do TARGETS+=("$d"); done \
    < <(find "$R" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
done

du_one() {
  local d="$1"
  local fn=$(echo "$d" | tr '/' '_')
  timeout 3600 du -sb "$d" 2>/dev/null > "${TMPD}/${fn}.txt"
}
export -f du_one
export TMPD

printf '%s\n' "${TARGETS[@]}" | xargs -P16 -I{} bash -c 'du_one "$@"' _ {}

# Critical: detect MISSING entries (landmine #4)
N_FOUND=$(ls "${TMPD}"/*.txt 2>/dev/null | wc -l)
N_EXPECTED=${#TARGETS[@]}
if [ "$N_FOUND" -lt "$N_EXPECTED" ]; then
  echo "WARNING: $N_FOUND/$N_EXPECTED dirs reported. Missing dirs:"
  for d in "${TARGETS[@]}"; do
    fn=$(echo "$d" | tr '/' '_')
    [ ! -f "${TMPD}/${fn}.txt" ] && echo "  MISSING: $d"
  done
fi

cat "${TMPD}"/*.txt | sort -k1 -rn | awk '{
  if ($1 >= 1099511627776) printf "%10.2f TB  %s\n", $1/1099511627776, $2
  else if ($1 >= 1073741824) printf "%10.2f GB  %s\n", $1/1073741824, $2
  else printf "%10.2f MB  %s\n", $1/1048576, $2
}'
```

Use `--time=00:45:00` not 00:30:00 if any root is > 30 TB. Lustre du on multi-TB dirs is metadata-bound, slower than estimated.

### Step 3 — Cross-check vs lfs quota

```bash
# Sum your du output
DU_TOTAL=$(awk '{s+=$1} END {print s}' "${TMPD}"/*.txt)
DU_TB=$(awk -v t="$DU_TOTAL" 'BEGIN { printf "%.2f", t/1099511627776 }')

# Compare to authoritative
QUOTA_TB=$(lfs quota -p <pid> /lus/lfs1aip2 | awk '/lfs1aip2/{print $2}' | sed 's/T.*//')
echo "du sum: $DU_TB TB | quota: $QUOTA_TB TB | gap: $(echo "$QUOTA_TB - $DU_TB" | bc) TB"
```

If gap > 5%, find where:

```bash
# 1. Were any roots missed? Re-check find vs symlinks.
# 2. Are there owner-only subdirs you can't see?
find <ROOT> -mindepth 2 -maxdepth 4 -type d -perm /200 ! -readable 2>&1 \
  | head -20

# 3. For each user with own data in the project, sum their per-user quota
for U in $(getent passwd | grep brics.s5e | cut -d: -f1); do
  Q=$(lfs quota -h -u "$U" /lus/lfs1aip2 2>/dev/null | awk 'NR>2 && /lfs1aip2/{print $2}')
  [ -n "$Q" ] && printf '%-20s %s\n' "$U" "$Q"
done | sort -k2 -hr
```

The per-user breakdown often pinpoints which user's hidden tree explains the gap.

### Step 4 — Categorize cleanup candidates

Build a table sorted by `(size × deletability)`:

| Category | Action |
|---|---|
| Owned by you, alt format / older preproc | Direct delete |
| Owned by you, raw pipeline / scratch | mtime > 90 day → delete |
| Owned by you, production training data | Per-element pruning (e.g. ticker subset) |
| Owned by another user in shared group | DO NOT TOUCH. Coordinate via Slack / email. |
| Active-write dir (mtime < 1 day) | DO NOT TOUCH. Job is using it. |

## Key Insights

### Why this skill matters

Without these checks, naive `du -sh /lus/...` returned 75 TB on a 199 TB quota — 124 TB invisible. After applying landmine fixes, recovered the full picture. Skipping cross-check = wrong recommendations + wasted cleanup effort on small consumers.

### Landmine #1 (symlink) is the most common miss

When the quota project spans both `/projects/<group>/` and `/projects/public/<group>/`, the public side is invariably reached only via a symlink in the private side. `du -sh /private/` will skip it.

Detection: `find /lus/lfs1aip2/projects/<group> -maxdepth 2 -type l -ls` lists symlinks. Audit each link target as a separate root.

### Landmine #2 (perm 2700) is invisible without lfs quota -u

Owner-only mode hides multi-TB tmpdir/cache from anyone but the owner. Project quota still counts them. `lfs quota -u <owner>` returns the true total for that user including their hidden subdirs.

If you can't query other users' quota (locked down), you can only bound their usage from below using du visible portion + note the perm-denied subdirs as "≥ X TB, hidden subdirs exist".

### Landmine #3 (quota-exceeded job suicide) is brutal at cap

When project is at 100% quota, even tee writes for the audit's own log fail. The job exits 1, partial result lost. Always:
- Output to `/local/$USER/` or stdout (off-quota)
- Or stream to a path on a different filesystem (e.g. /home if it's not Lustre)
- For very-near-cap audits, run with `--time=00:45:00`+ so the killed-by-quota exit happens AFTER initial du writes, not before

### Landmine #4 (xargs+timeout drops biggest) is silent

`xargs -P16 -I{} bash -c 'timeout 1700 du -sb {} > $TMPD/...'` runs in parallel. If the biggest dir hits timeout, that one TMPD file never gets written. The aggregate script then says "TOTAL audited: N dirs" but missed the largest.

Detection: count `len(TARGETS)` vs `ls $TMPD/*.txt | wc -l`. If short, list the missing.

### `lfs quota -u` per-user is the only authoritative truth

du is a *bottom-up file traversal*, perm-bound. lfs quota is a *top-down accounting*, kernel-tracked, perm-blind. When they disagree, lfs quota wins.

## Verification

After audit completes:

1. `du_total ≈ quota_used` (gap < 5% of quota)
2. Every visible audit ROOT shows ≥ 1 result file in TMPD (no silent drops)
3. Per-user lfs quota sums roughly match du-by-owner sums (use `stat -c "%U %s" find ...` or owner-grouped audit)
4. Any user with quota > visible du has hidden dirs noted in the report

If verification fails, do not push cleanup recommendations until the gap is explained.

## Related skills / files

- `chmod-group`, `chmod-world` for fixing perms post-cleanup
- `fix-git-lustre-io` for git-specific Lustre slowness (different topic)
- Memory `feedback_login_node_io_storm_diagnosis.md` for cases where the audit *itself* triggers a metadata storm (run from compute node only)
