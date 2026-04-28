---
name: chmod-world
version: "1.0.0"
description: Set up a world-accessible shared folder on HPC Lustre where anyone (including cross-group) can read/write, and newly created files inherit permissive perms. Handles the common HPC reality that setfacl/cron/systemd-linger are locked down. Complements chmod-group (which only covers in-group sharing).
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# chmod-world

Make a shared folder rwx for everyone, and wherever possible ensure **newly created files/subdirectories** also automatically receive permissive permissions — given the HPC reality that setfacl / cron / systemd linger are commonly locked down by admins.

**Difference from `chmod-group`**: `chmod-group` is for in-group sharing and only touches the group bits; this skill is for **cross-group / external sharing**, touching the others bits + handling the ancestor traversal chain + new-file inheritance fallback.

## When to Use

- User requests "make folder X rwx for everyone / 777 / world-writable"
- Need to allow **users outside the group** to read/write shared data (non-group members)
- Requirement that "newly created files are also automatically 777" (inherit permissive perms)
- Typical trigger phrases: `chmod 777`, `world-writable`, `shared folder`, `anyone can access`, `let everyone read/write`

## The Three Layers You Must Think About

**L1 — Target folder perms**: The mode bits on the target folder itself
**L2 — Ancestor traversal chain**: Every directory from `/` to the target requires `x` to traverse
**L3 — New-file inheritance**: How permissions will be assigned to things created inside in the future — this layer is **not covered** by chmod itself

Missing any layer = task not complete.

## Process

### Step 0 — Confirm intent & scope

Ask the user (if unclear):

| Question | Why it matters |
|------|------------|
| Does "everyone" mean same group, or truly cross-group users? | Determines whether to touch the others bits on ancestors |
| Need rwx or r-x? | Read-only vs read-write differs by one `w` bit |
| Should newly created files also be 777? | Triggers the L3 fallback logic |

### Step 1 — Probe environment capabilities

Before making any changes, **must** probe 4 key capabilities to determine which paths are available:

```bash
# (A) Is setfacl available? (Can POSIX default ACL do auto-inheritance?)
which setfacl getfacl 2>&1
find /usr /bin /sbin /opt -name setfacl 2>/dev/null | head -3

# (B) Does the Lustre mount forbid xattr? (even if setfacl is installed it may be unusable)
mount | grep -E 'lustre|gpfs' | head -2
# Look for "nouser_xattr" — if present, POSIX ACL is essentially unavailable at user level

# (C) cron / at — are periodic tasks available?
which crontab at 2>&1
systemctl is-active cron crond atd 2>&1

# (D) systemd --user linger — can persistent timers run?
loginctl show-user $(whoami) 2>&1 | grep -E 'Linger|State'
```

**Expected common result (most HPC login nodes)**: setfacl not installed, `nouser_xattr` mount, cron not installed, linger=no and enable-linger blocked by polkit. Accept this reality and proceed with the fallback route.

### Step 2 — Fix L1 (target folder)

```bash
TARGET=<path>
chmod 2777 "$TARGET"     # setgid + rwxrwxrwx
```

**Why `2777` instead of `0777`**: Preserves the setgid bit, so new files automatically inherit the parent directory's group (usually the shared research group). Even if the creator belongs to a different group, new files join the shared group so team members can naturally access them. `chmod 0777` **clears** setgid, losing this benefit.

### Step 3 — Check L2 (ancestor traversal)

Run a permission chain diagnostic from `/` to TARGET:

```bash
IFS='/' read -ra PARTS <<< "$TARGET"
path=""
for p in "${PARTS[@]:1}"; do
    path="$path/$p"
    perm=$(stat -c '%a %A %U:%G' "$path" 2>/dev/null)
    echo "  $perm  $path"
done
```

**Interpretation**: For an "others" user (neither owner nor group member) to reach TARGET, every layer's **others bits must include `x`** (4→r, 2→w, 1→x; `x` alone = 1, 5, or 7). Any single layer missing `x` for others **blocks all cross-group users**.

**Key judgment calls**:
- All ancestors have others≥`x` → L2 passes, truly accessible by everyone
- An ancestor has no `x` for others but `x` for group → **only shared group members** can access; cross-group users are blocked
- An ancestor has no `x` for others and cannot be changed → tell the user this is a hard wall requiring admin intervention

**Do not unilaterally change ancestor directory permissions** — ancestor directories are typically owned by others (or admin), and touching them can cause unintended consequences. Report to the user and let them decide.

### Step 4 — Handle L3 (new-file inheritance)

Branch based on Step 1 probe results:

#### Path A: setfacl available + mount supports user_xattr (ideal)

```bash
setfacl -d -m u::rwx,g::rwx,o::rwx,m::rwx "$TARGET"
getfacl "$TARGET"   # verify that the default section has user/group/other/mask = rwx
```

Anything newly created automatically receives a `rwxrwxrwx` access ACL. Done.

#### Path B: setfacl unavailable or mount has `nouser_xattr` (typical HPC)

**Give up on automatic inheritance** and use the fallback:

1. Write a `.fix_perms.sh` script inside TARGET that anyone can run at any time

```bash
cat > "$TARGET/.fix_perms.sh" <<'EOF'
#!/bin/bash
# Recursively reset permissions. Run this after new files are added so they
# become world-accessible. This exists because setfacl/cron/linger are not
# available on this system — "auto-777-inheritance" has to be manual.
set -u
TARGET=__TARGET__
find "$TARGET" -type d -exec chmod 2777 {} + 2>/dev/null
find "$TARGET" -type f -exec chmod 666  {} + 2>/dev/null
echo "chmod done at $(date -Iseconds) on $TARGET"
EOF
sed -i "s|__TARGET__|$TARGET|" "$TARGET/.fix_perms.sh"
chmod 777 "$TARGET/.fix_perms.sh"
```

2. Suggest that users (in their own shell) set `umask 002` or `umask 000`:
   - `umask 002` → new files get 664 (group-writable, others read-only)
   - `umask 000` → new files get 666 (world-writable)

3. Explicitly tell the user: without running `.fix_perms.sh`, new file permissions depend on the **creator's umask**, likely 644 / 664, so others can read but not write.

#### Never do the following

- **Do not** use `sudo` or attempt to bypass permission restrictions
- **Do not** silently enable `loginctl enable-linger` or deploy a background daemon for persistence — the permission restrictions are intentional and will be caught by the classifier
- **Do not** `chmod -R` ancestor directories — this affects things outside scope and may break others' isolation
- **Do not** run `inotifywait` for live chmod: on Lustre, inotify only sees events that occur on the local client node; changes made on other compute/login nodes are invisible

### Step 5 — Verify

```bash
# L1: target perms
ls -ld "$TARGET"                     # expected: drwxrwsrwx (2777)

# L2: ancestor chain (don't skip)
# Re-run the Step 3 loop to confirm each layer is traversable

# L3: create a test file to check inheritance
touch "$TARGET/_probe" && ls -l "$TARGET/_probe" && rm "$TARGET/_probe"
```

## Key Insights

### Lustre `nouser_xattr` silently kills ACLs

ACLs are stored in filesystem xattrs. Lustre admins commonly add the `nouser_xattr` mount option to reduce MDT RPCs. When this is set, even with `setfacl` installed, `setfacl -d` may silently have no effect or fail outright. **Always probe mount options in Step 1** — checking `which setfacl` alone is not sufficient.

### `chmod 777` destroys setgid inheritance

`2777` vs `0777` differs by only one setgid bit, but that bit is **critical for shared access**. setgid makes new files automatically inherit the parent directory's group, providing a baseline of "shared group members can always access" for free. `0777` clears that baseline — new files revert to the creator's own default group, narrowing access. Always use `2777` by default.

### Directory traversal is an AND relationship, not OR

`ls /a/b/c/d/target` requires that every level — `/a`, `/a/b`, `/a/b/c`, `/a/b/c/d` — has `x` for the accessing user. A single missing `x` breaks the entire chain. Therefore "target itself is 777" **does not mean** "everyone can access target" — the full chain from `/` to target must be checked.

### "auto-inherit 777" cannot be fully automatic on restricted HPC

When setfacl / cron / linger / inotify are all unavailable, there is no truly zero-maintenance automatic inheritance solution. The honest approach is to **acknowledge this** and provide a manual fallback (`.fix_perms.sh`), rather than building a fragile automation that will be blocked by administrators.

### Do not cross admin boundaries

Ancestor directory permissions, mount options, and system daemon enablement are within the admin domain. Crossing that boundary will: (a) be blocked by the security classifier, (b) affect other users, (c) violate the user trust boundary. When hitting a hard wall, report it to the user rather than acting unilaterally.

## Verification Checklist

- [ ] L1: `stat -c '%a' $TARGET` returns `2777`
- [ ] L2: ancestor chain has been run once; confirmed who can/cannot traverse
- [ ] L3: inheritance method verified (default ACL set **or** `.fix_perms.sh` in place)
- [ ] User informed that "new file permissions depend on the creator's umask"
- [ ] If there is a hard ancestor wall, explicitly tell the user that admin intervention is needed or they must accept "in-group access only"

## Related Skills

- **chmod-group**: for in-group sharing, does not touch others bits; the L2 ancestor analysis in this skill also applies to chmod-group
- **fix-git-lustre-io**: Lustre-related performance / metadata traps

## Version History

- **v1.0.0** (2026-04-20): Initial version. Distilled from the session setting up the `best_performed_models/` world-shared folder: three-layer mental model (L1/L2/L3) + HPC environment capability probe flow + fallback pattern.
