---
name: pdf-text-extraction-fallback
description: Use when Claude Code's Read tool fails on a .pdf file with "pdftoppm is not installed" (poppler-utils missing, typical on locked-down HPC or ARM systems). Extracts PDF text via Python pymupdf to a sibling .txt file, then Read the .txt. Triggers on errors mentioning pdftoppm, poppler-utils, or "PDF page rendering"; or when user asks to read a PDF on a machine without apt sudo.
version: 1.0.0
allowed-tools: Bash, Read
alwaysApply: false
---

# PDF Text Extraction Fallback

## When to Use

Trigger on any of:
- Read tool errors on `.pdf` with message `pdftoppm is not installed`
- Environment where `apt-get install poppler-utils` is not available (HPC login node without sudo, ARM without poppler wheel)
- User explicitly asks to read a PDF and Read tool fails

Skip if:
- Read tool works directly (poppler-utils already installed)
- PDF is scanned images only (pymupdf text extraction returns empty; would need OCR, out of scope)

## Why This Exists

Claude Code's `Read` tool renders PDFs to images via `pdftoppm` (poppler-utils) so the multimodal model can read them. On locked-down HPC without poppler and without sudo, Read fails. The tool's error message suggests `brew install poppler` or `apt-get install poppler-utils`, but does NOT mention the Python fallback that usually **is** available.

The workaround: convert PDF text to a `.txt` with `pymupdf` (a pip-installable PyPI package, no system deps), then Read the `.txt`.

## Process

### Step 1: Check pymupdf availability

```bash
python3 -c "import pymupdf; print('pymupdf', pymupdf.__version__)"
```

If not installed and you have pip access (user's site-packages or conda base):

```bash
pip install --user pymupdf
```

### Step 2: Extract PDF to sibling .txt

Replace `$PDF` with the absolute PDF path:

```bash
python3 -c "
import pymupdf, pathlib
pdf_path = '$PDF'
txt_path = pathlib.Path(pdf_path).with_suffix('.txt')
doc = pymupdf.open(pdf_path)
with open(txt_path, 'w') as f:
    for i, page in enumerate(doc):
        f.write(f'\n\n===== PAGE {i+1} =====\n\n')
        f.write(page.get_text())
print(f'OK: {doc.page_count} pages → {txt_path}')
"
```

**Rationale for page markers**: Including `===== PAGE N =====` lets you:
- Read offset/limit by page later
- Grep to locate specific sections (e.g. `grep -n "===== PAGE" file.txt` to build a ToC)

### Step 3: Read the .txt

Use Read tool with `offset` and `limit` for large PDFs (> 100 pages). For ≤ 100 pages, read sequentially in chunks.

## Key Insights

- **Read tool's error points at the wrong fix**: `apt-get install poppler-utils` fails on HPC without sudo. `pip install pymupdf` works in userspace.
- **Do NOT use pypdf/pdfplumber** unless you've verified their text-extraction quality on your specific PDF. `pymupdf` is consistently the best text extractor for academic PDFs (column handling, ligatures, math symbols).
- **Sibling .txt is the right location**: same directory as the PDF, so Read on the txt feels natural and the cache stays with the source.
- **Page markers are cheap and save time**: grep for them to build a quick table of contents without re-parsing the PDF.
- **43 pages ≈ 140KB text**: one pymupdf pass is ~1 second. Do not over-engineer with streaming.

## Verification

After running Step 2, the sibling `.txt` should exist and be readable:

```bash
ls -la "${PDF%.pdf}.txt"
head -20 "${PDF%.pdf}.txt"
```

If the txt is empty or only contains `===== PAGE N =====` markers with no content in between, the PDF is likely image-only (scanned). Report this to the user; OCR is a separate workflow.

## Integration with Read

Once `.txt` exists, use Read with normal offset/limit:

```
Read(file_path="/path/to/paper.txt", offset=0, limit=200)
```

For very large PDFs (> 500 pages), split extraction into chunks by page range:

```python
for start in range(0, doc.page_count, 100):
    # write .part_{start:04d}.txt
    ...
```
