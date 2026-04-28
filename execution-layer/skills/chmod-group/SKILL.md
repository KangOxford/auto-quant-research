---
name: chmod-group
version: "1.0.0"
description: Manage directory group permissions for shared access. Two modes - recursive (files+dirs) and path-only (directory traversal). Useful for sharing checkpoints, data directories with team members.
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Glob
---

# chmod-group

Bulk-manage directory group permissions to allow team members to access shared directories.

## Use Cases

- Share a checkpoints directory with team members for reading
- Grant other users access to a specific path (e.g., `~/project/data/results`)
- Principle of least privilege: only open the access paths that are necessary

## Two Modes

### Mode 1: Recursive
Add group read permissions to an entire directory tree:
- **Directories**: `g+rx` (readable + executable, can enter and list)
- **Files**: `g+r,g-x` (readable but not executable)

**Use case**: Share entire directory contents for team read access

```bash
# Example: share the checkpoints directory
chmod-group recursive /path/to/checkpoints
```

### Mode 2: Path-only (traversal)
Add only execute permission to the specified parent directories, without read permission:
- **Specified directories**: `g+x` (can traverse but cannot list)
- **Subdirectories/files**: not modified

**Use case**: Allow access to a deep directory without exposing intermediate path contents

```bash
# Example: allow access to ~/AlphaTrade/LOBS5/checkpoints
# without letting group users see other contents of AlphaTrade and LOBS5
chmod-group path-only ~/AlphaTrade ~/AlphaTrade/LOBS5
```

## Parameters

| Parameter | Description | Example |
|------|------|------|
| `recursive <dir>` | Recursively modify the directory and all its contents | `recursive /data/checkpoints` |
| `path-only <dir1> [dir2...]` | Add traversal permission to the specified directories only | `path-only ~/project ~/project/data` |

## Permission Reference

### Permission symbol meanings

| Symbol | Octal | Group capability |
|------|------|----------------|
| `drwxr-sr-x` | 2755 | Can list and enter |
| `drwxr-s---` | 2750 | Can list and enter; others have no access |
| `drwx--s---` | 2710 | Can traverse only; cannot list |
| `-rw-r--r--` | 644 | Can read file |

### The setgid bit (s)

- **Lowercase s**: setgid + execute permission present
- **Uppercase S**: setgid present + **no** execute permission (needs fixing!)

**Effect of setgid**: Newly created files automatically inherit the directory's group

## Complete Examples

### Scenario: Share checkpoints with the team

**Requirements**:
- Team needs to read the contents of `~/AlphaTrade/LOBS5/checkpoints/`
- Do not want to expose other contents of `AlphaTrade` and `LOBS5`

**Solution**:
```bash
# Step 1: add traversal permission to parent directories
chmod-group path-only ~/AlphaTrade ~/AlphaTrade/LOBS5

# Step 2: recursively add read permission to checkpoints
chmod-group recursive ~/AlphaTrade/LOBS5/checkpoints
```

**Result**:
```
~/AlphaTrade              drwx--s---  traversal only
  └─ LOBS5                drwx--s---  traversal only
      └─ checkpoints      drwxr-s---  ✅ readable and listable
          ├─ model1/      drwxr-sr-x  ✅ accessible
          └─ weights.pkl  -rw-r--r--  ✅ readable
```

### Scenario: Fully share a directory

**Requirements**: Share the entire `~/shared_data` directory

**Solution**:
```bash
chmod-group recursive ~/shared_data
```

**Result**: All subdirectories and files are readable by the group

## Implementation Details

### Recursive mode
```bash
# Directories: add rx permission
find <dir> -type d -exec chmod g+rx {} +

# Files: add r permission, remove x
find <dir> -type f -exec chmod g+r,g-x {} +
```

### Path-only (traversal) mode
```bash
# Add only x permission to specified directories
chmod g+x <dir1> <dir2> ...
```

## Verify Permissions

After modifying, verify:
```bash
# Check numeric permissions
stat -c "%a %A %n" <path>

# Check accessibility
ls -la <path>

# Count directories missing execute permission
find <path> -type d ! -perm -g=x | wc -l
```

## Notes

1. **Only modifies group permissions** — does not affect owner or others
2. **Preserves the setgid bit** — ensures new files inherit the correct group
3. **Principle of least privilege**: only open the access permissions that are necessary
4. **Verify group membership**: ensure the user is in the correct group (`groups` command)

## FAQ

### Q: Why does `drwxr-s---` appear but the user still cannot access?

A: Check:
1. Whether the user is in the correct group (`groups`)
2. Whether parent directories have execute permission (the entire path needs `x`)
3. Whether the `s` is uppercase `S` (no execute permission)

### Q: Difference between uppercase S and lowercase s?

A:
- `s` = setgid **+** execute permission ✅
- `S` = setgid **but no** execute permission ❌ (needs fixing)

### Q: How to revoke permissions?

A:
```bash
# Remove all group permissions
chmod -R g-rwx <path>

# Remove only execute permission
chmod g-x <path>
```

## Troubleshooting

### Permission Denied Error

**Symptom**: `ls: cannot access 'path': Permission denied`

**Diagnostic steps**:
1. Check permissions along the full path:
   ```bash
   namei -l /full/path/to/directory
   ```

2. Find permission issues:
   ```bash
   # Find directories missing group execute permission
   find /path -type d ! -perm -g=x
   ```

3. Fix parent directory permissions:
   ```bash
   chmod g+x /parent/dirs
   ```

## Version History

- **v1.0.0** (2026-02-04): Initial version
  - Recursive permission mode
  - Path-only traversal mode
  - Permission verification functionality
