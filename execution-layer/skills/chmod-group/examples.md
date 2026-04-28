# chmod-group Usage Examples

## Quick Start

### Scenario 1: Share a checkpoints directory

**Requirements**: Allow team members to read checkpoint contents without exposing other directories

```bash
# Method 1: using scripts
bash ~/.claude/skills/chmod-group/scripts/chmod-path-only.sh \
    ~/AlphaTrade \
    ~/AlphaTrade/LOBS5

bash ~/.claude/skills/chmod-group/scripts/chmod-recursive.sh \
    ~/AlphaTrade/LOBS5/checkpoints

# Method 2: direct commands
chmod g+x ~/AlphaTrade ~/AlphaTrade/LOBS5
find ~/AlphaTrade/LOBS5/checkpoints -type d -exec chmod g+rx {} +
find ~/AlphaTrade/LOBS5/checkpoints -type f -exec chmod g+r,g-x {} +
```

**Verify results**:
```bash
stat -c "%a %A %n" \
    ~/AlphaTrade \
    ~/AlphaTrade/LOBS5 \
    ~/AlphaTrade/LOBS5/checkpoints
```

Expected output:
```
2710 drwx--s--- ~/AlphaTrade              ← traversal only
2710 drwx--s--- ~/AlphaTrade/LOBS5        ← traversal only
2750 drwxr-s--- ~/AlphaTrade/LOBS5/checkpoints  ← readable and listable
```

---

### Scenario 2: Fully share a directory

**Requirements**: Share the entire `shared_data` directory with group members

```bash
# Using the script
bash ~/.claude/skills/chmod-group/scripts/chmod-recursive.sh ~/shared_data

# Or direct commands
find ~/shared_data -type d -exec chmod g+rx {} +
find ~/shared_data -type f -exec chmod g+r,g-x {} +
```

---

### Scenario 3: Fix a permission issue

**Problem**: Directory shows `drwx--S---` (uppercase S); group cannot access

**Cause**: setgid is set but execute permission is missing

**Fix**:
```bash
# Add execute permission for group
chmod g+x /path/to/directory

# Verify the fix
stat -c "%a %A" /path/to/directory
# Should show: 2710 drwx--s--- (lowercase s)
```

---

## Permission Reference Table

### Directory permissions

| Octal | Symbol | Owner | Group | Others | Description |
|------|------|-------|-------|--------|------|
| 2700 | `drwx--S---` | rwx | --S | --- | Group cannot access (uppercase S) |
| 2710 | `drwx--s---` | rwx | --s | --- | Group can traverse only |
| 2750 | `drwxr-s---` | rwx | r-s | --- | Group can read and enter |
| 2755 | `drwxr-sr-x` | rwx | r-s | r-x | Everyone can read and enter |

### File permissions

| Octal | Symbol | Owner | Group | Others | Description |
|------|------|-------|-------|--------|------|
| 600 | `-rw-------` | rw- | --- | --- | Group cannot read |
| 640 | `-rw-r-----` | rw- | r-- | --- | Group can read |
| 644 | `-rw-r--r--` | rw- | r-- | r-- | Everyone can read |

---

## Common Command Reference

### Check permissions
```bash
# View permissions for a single file/directory
stat -c "%a %A %n" /path/to/file

# View directory tree permissions
ls -la /path/to/directory

# View permissions along the full path
namei -l /full/path/to/directory
```

### Find permission issues
```bash
# Find directories missing group execute permission
find /path -type d ! -perm -g=x

# Find directories with uppercase S (needs fixing)
find /path -type d -perm -2000 ! -perm -g=x

# Count permission distribution
find /path -type f -exec stat -c "%a" {} \; | sort | uniq -c
```

### Bulk fix
```bash
# Add group rx to all directories
find /path -type d -exec chmod g+rx {} +

# Add group r to all files
find /path -type f -exec chmod g+r {} +

# Remove group x from all files
find /path -type f -exec chmod g-x {} +
```

---

## Test Verification

### Testing as the owner
```bash
# Modify permissions
bash ~/.claude/skills/chmod-group/scripts/chmod-recursive.sh ~/test_dir

# Verify
ls -la ~/test_dir
```

### Testing as a group member
```bash
# Switch to another group user (if possible)
sudo -u other_user bash

# Test access
cd ~/original_user/test_dir    # should succeed
ls ~/original_user/test_dir     # should succeed
cat ~/original_user/test_dir/file.txt  # should succeed
```

### Verify traversal permission
```bash
# Set traversal permission
bash ~/.claude/skills/chmod-group/scripts/chmod-path-only.sh ~/parent

# Test as group user
cd ~/original_user/parent/child/target  # ✅ should succeed
ls ~/original_user/parent                # ❌ should fail (Permission denied)
```

---

## Troubleshooting

### Problem: Permission denied

**Checklist**:
1. ✓ Is the user in the correct group?
   ```bash
   groups  # list current user's groups
   ```

2. ✓ Does the entire path have execute permission?
   ```bash
   namei -l /full/path
   ```

3. ✓ Is the `s` uppercase S (no execute permission)?
   ```bash
   ls -ld /path  # check whether it shows S instead of s
   ```

### Problem: Still unable to access after modifying permissions

**Possible causes**:
1. Parent directory missing execute permission
   ```bash
   # Check and fix
   chmod g+x /parent/directory
   ```

2. SELinux or ACL restriction
   ```bash
   # Check SELinux
   ls -Z /path

   # Check ACL
   getfacl /path
   ```

3. User is not in the group
   ```bash
   # View the file's group
   ls -l /path

   # View the user's groups
   groups username
   ```

---

## Best Practices

### 1. Principle of least privilege
- Only add permissions to paths that require it
- Use path-only mode to protect intermediate paths
- Do not grant execute permission on files (unless necessary)

### 2. Verification steps
```bash
# Before modification
stat -c "%a %A %n" /path

# Modify
chmod ...

# Verify after modification
stat -c "%a %A %n" /path

# Functional test
sudo -u test_user ls /path
```

### 3. Be careful with bulk operations
```bash
# Test on a small scope first
find /path -maxdepth 1 -type d -exec chmod g+rx {} +

# Expand scope only after confirming correct
find /path -type d -exec chmod g+rx {} +
```

### 4. Preserve the setgid bit
```bash
# Good - preserves setgid
chmod g+rx /path

# Bad - may lose setgid
chmod 755 /path  # clears the setgid bit
```

---

## Advanced Techniques

### Modify only specific subdirectories
```bash
# Only modify directories named "checkpoints"
find /path -type d -name "checkpoints" -exec chmod g+rx {} +

# Exclude certain directories
find /path -type d ! -path "*/private/*" -exec chmod g+rx {} +
```

### Modify by file extension
```bash
# Add read permission only to .txt files
find /path -type f -name "*.txt" -exec chmod g+r {} +

# Add execute permission only to .sh files
find /path -type f -name "*.sh" -exec chmod g+rx {} +
```

### Restore default permissions
```bash
# Directories: 755 (rwxr-xr-x)
find /path -type d -exec chmod 755 {} +

# Files: 644 (rw-r--r--)
find /path -type f -exec chmod 644 {} +
```
