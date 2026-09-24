"""
Repository-wide raw HTML rendering audit.
Checks for three specific problem patterns:
  1. Orphaned closing tags: st.markdown('</div>') or st.markdown('</div></div>')
  2. HTML in st.expander() labels
  3. HTML in st.button() labels
"""
import re
import glob
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Pattern 1: st.markdown with *only* closing tags — orphaned HTML
ORPHAN_RE = re.compile(
    r'st\.markdown\s*\(\s*["\'](\s*</[a-zA-Z]+>\s*)+["\']',
    re.IGNORECASE,
)

# Pattern 2: st.expander label contains an HTML open-tag
EXPANDER_HTML_RE = re.compile(
    r'st\.expander\s*\([^)]*<[a-zA-Z]',
    re.IGNORECASE,
)

# Pattern 3: st.button label contains an HTML open-tag
BUTTON_HTML_RE = re.compile(
    r'st\.button\s*\([^)]*<[a-zA-Z]',
    re.IGNORECASE,
)

files = sorted(
    glob.glob("pages/*.py")
    + ["app.py"]
    + glob.glob("frontend/*.py")
)

issues = []

for f in files:
    with open(f, encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if ORPHAN_RE.search(line):
            issues.append(f"ORPHAN    {f}:{lineno}: {stripped[:120]}")
        if EXPANDER_HTML_RE.search(line):
            issues.append(f"EXPANDER  {f}:{lineno}: {stripped[:120]}")
        if BUTTON_HTML_RE.search(line):
            issues.append(f"BUTTON    {f}:{lineno}: {stripped[:120]}")

if issues:
    print(f"FOUND {len(issues)} real raw-HTML rendering issue(s):")
    for i in issues:
        print(" ", i)
    sys.exit(1)
else:
    print("CLEAN - zero orphaned closing tags, no HTML in expander/button labels")
    sys.exit(0)
