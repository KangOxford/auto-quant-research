---
name: gdrive-download
description: Download files/folders from Google Drive using rclone (preferred) or gdown. Handles shared folders, 50+ file limits, and rate limiting.
version: 1.0.0
allowed-tools: Bash
alwaysApply: false
---

# Google Drive Download

## When to Use

- User shares a Google Drive link (folder or file) to download
- Need to pull shared data/results/checkpoints from collaborators
- Any `drive.google.com` URL in conversation

## Process

### 1. Prefer rclone over gdown

**rclone** is the reliable path. gdown breaks on folders with 50+ files (Google API pagination limit) and gets rate-limited quickly.

```bash
RCLONE=/projects/s5e/quant/.local/bin/rclone
```

### 2. Identify the folder/file name on Drive

For a shared link like `https://drive.google.com/drive/folders/<ID>`, you need the folder name as it appears in Google Drive (not the ID). Ask the user if unclear.

### 3. Download

**Shared-with-me folder** (most common case with collaborators):
```bash
$RCLONE copy --drive-shared-with-me "gdrive:<FolderName>" /local/destination --progress
```

**Own Drive folder:**
```bash
$RCLONE copy "gdrive:<FolderName>" /local/destination --progress
```

**Single file by ID** (fallback if folder name unknown):
```bash
# Extract file ID from URL, use gdown for single files
python3 -m gdown "https://drive.google.com/uc?id=<FILE_ID>" -O /local/destination/filename
```

### 4. Verify download
```bash
find /local/destination -type f | wc -l
du -sh /local/destination
```

## Key Insights

1. **gdown fails at scale**: 50-file folder limit (Google Drive API), frequent rate limiting (`FileURLRetrievalError`), and `--remaining-ok` only partially helps
2. **rclone uses OAuth tokens**: bypasses rate limits that hit unauthenticated gdown requests. Configured remote: `gdrive:`
3. **`--drive-shared-with-me`**: required for folders shared by others (e.g., collaborator Anik's results). Without this flag, rclone only searches your own Drive
4. **Folder name, not ID**: rclone uses the human-readable folder name, not the Google Drive folder ID from the URL. The folder name is usually visible in the Drive UI or can be found with `$RCLONE lsd --drive-shared-with-me gdrive:`
5. **Default destination**: `/projects/s5e/quant/<project_name>/` -- keep downloaded data outside git repos

## Fallback: gdown (small folders only)

For folders with <50 files or single files, gdown still works:
```bash
python3 -m gdown --folder "https://drive.google.com/drive/folders/<ID>"
```

## Verification

- File count matches expected (check Drive UI)
- `du -sh` shows reasonable size
- Key files present (CSVs, .pt checkpoints, .py source)
