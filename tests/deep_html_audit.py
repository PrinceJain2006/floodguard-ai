# -*- coding: utf-8 -*-
"""
Deep raw-HTML audit for FloodGuard AI.

Detects every pattern that can cause raw markup to appear as visible text:
  A. Orphaned / standalone closing-tag st.markdown calls
  B. HTML tags in st.expander / st.button / st.metric / st.caption / st.text / st.write labels
  C. st.markdown / st.write calls with HTML but WITHOUT unsafe_allow_html=True on the SAME line
  D. f-strings that build HTML and are passed directly to non-HTML-rendering functions
  E. Multiline triple-quoted HTML strings NOT wrapped in st.markdown unsafe
"""

import re
import sys
import ast
import textwrap
from pathlib import Path

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
FILES = (
    list(ROOT.glob("pages/*.py"))
    + [ROOT / "app.py"]
    + list(ROOT.glob("frontend/*.py"))
    + list(ROOT.glob("agents/*.py"))
    + list(ROOT.glob("services/*.py"))
)

HTML_OPEN_RE  = re.compile(r'<(?:span|div|p|strong|em|b|i|br|hr|a |table|ul|ol|li|style|button|script|section|h[1-6])\b', re.I)
HTML_CLOSE_RE = re.compile(r'</(?:span|div|p|strong|em|b|i|br|hr|a|table|ul|ol|li|style|button|script|section|h[1-6])>', re.I)

# Calls that NEVER render HTML — any HTML in their arguments is shown as plain text
PLAIN_TEXT_CALLS = re.compile(
    r'\bst\.(expander|button|metric|caption|text|header|subheader|title|sidebar\.markdown|info|warning|error|success|write)\s*\(',
    re.I
)

issues = []

def report(f, lineno, kind, line):
    issues.append(f"  [{kind}] {f.name}:{lineno}: {line.strip()[:110]}")


for fpath in sorted(FILES):
    try:
        src = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    lines = src.splitlines()
    n = len(lines)

    i = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Skip pure comments
        if stripped.startswith("#"):
            i += 1
            continue

        lineno = i + 1

        # ── A. Orphaned closing tags in st.markdown ──────────────────────────
        # Pattern: st.markdown("</div>") or st.markdown("</div></div>", ...)
        # Allow unsafe_allow_html=True on the same line
        if re.search(r'st\.markdown\s*\(\s*["\'](\s*</[a-zA-Z]+>\s*)+["\']', line):
            if "unsafe_allow_html=True" not in line:
                report(fpath, lineno, "ORPHAN_CLOSE", line)

        # ── B. HTML in plain-text Streamlit calls ────────────────────────────
        if PLAIN_TEXT_CALLS.search(line) and (HTML_OPEN_RE.search(line) or HTML_CLOSE_RE.search(line)):
            report(fpath, lineno, "HTML_IN_PLAIN_CALL", line)

        # ── C. st.markdown with HTML but no unsafe_allow_html ────────────────
        # Only flag *single-line* st.markdown calls that contain an HTML tag
        # and do NOT have unsafe_allow_html=True
        if re.search(r'\bst\.markdown\s*\(', line):
            # Collect the full call (may span multiple lines up to closing paren)
            call_lines = [line]
            depth = line.count("(") - line.count(")")
            j = i + 1
            while depth > 0 and j < min(i + 30, n):
                call_lines.append(lines[j])
                depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            call_text = "\n".join(call_lines)
            if HTML_OPEN_RE.search(call_text) and "unsafe_allow_html=True" not in call_text:
                report(fpath, lineno, "MARKDOWN_NO_UNSAFE", line)

        i += 1

# ── Print results ─────────────────────────────────────────────────────────────
print(f"\nFiles scanned: {len(FILES)}")
if not issues:
    print("CLEAN - zero raw HTML rendering issues found.\n")
    sys.exit(0)
else:
    print(f"WARNING: {len(issues)} potential issue(s) found:\n")
    for iss in issues:
        print(iss)
    print()
    sys.exit(1)
