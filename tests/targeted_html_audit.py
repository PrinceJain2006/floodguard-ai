# -*- coding: utf-8 -*-
"""
Targeted audit — finds only the two patterns that actually cause
visible raw HTML in Streamlit:

  A. Orphaned closing-tag st.markdown calls:
       st.markdown("</div></div>")  or  st.markdown('</div>')
       (with or without unsafe_allow_html -- closing tags alone are useless
        and indicate a split-HTML bug)

  B. HTML tags inside calls that NEVER render HTML:
       st.expander(f"...{some_span_html}...")
       st.button("<b>click</b>")
       etc.
"""
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
FILES = (
    list(ROOT.glob("pages/*.py"))
    + [ROOT / "app.py"]
    + list(ROOT.glob("frontend/*.py"))
)

HTML_TAG_RE = re.compile(
    r"</?(?:span|div|p|strong|em|b|i|br|hr|a|table|ul|ol|li|style|button|script|section|h[1-6])\b",
    re.IGNORECASE,
)

# Matches st.markdown("</...>") — only closing tags, nothing else meaningful
ORPHAN_CLOSE_RE = re.compile(
    r'st\.markdown\s*\(\s*["\'](\s*</[a-zA-Z0-9]+>\s*)+["\']',
    re.IGNORECASE,
)

# Plain-text Streamlit calls that cannot render HTML
PLAIN_TEXT_FN_RE = re.compile(
    r'\bst\.(expander|button|metric|caption|text|header|subheader|title)\s*\(',
    re.IGNORECASE,
)

issues = []

for fpath in sorted(FILES):
    try:
        src = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    lines = src.splitlines()

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # A: orphaned closing tags in st.markdown
        if ORPHAN_CLOSE_RE.search(line):
            issues.append(f"  [ORPHAN]       {fpath.name}:{lineno}  {stripped[:110]}")

        # B: HTML in plain-text calls (single-line only — multi-line needs separate check)
        if PLAIN_TEXT_FN_RE.search(line) and HTML_TAG_RE.search(line):
            issues.append(f"  [PLAIN_HTML]   {fpath.name}:{lineno}  {stripped[:110]}")

print(f"Files scanned: {len(FILES)}")
if not issues:
    print("CLEAN - zero orphaned-tag or plain-text-HTML issues found.")
    sys.exit(0)
else:
    print(f"ISSUES FOUND: {len(issues)}")
    for iss in issues:
        print(iss)
    sys.exit(1)
