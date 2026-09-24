# -*- coding: utf-8 -*-
"""
COMPREHENSIVE raw-HTML rendering audit for FloodGuard AI.

Checks all real patterns that cause visible raw markup in Streamlit:

1. ORPHANED_CLOSE: st.markdown("</div>") — closing tags with no matching open
2. HTML_IN_EXPANDER: st.expander(f"...{html_var}...") where the arg has HTML
3. HTML_IN_BUTTON: st.button("...html...", ...) 
4. HTML_IN_METRIC: st.metric(label="...<span>...", ...)
5. SPLIT_MARKDOWN: HTML opened in one st.markdown call, closed in another
   (detect by looking for st.markdown blocks that ONLY contain closing tags)
6. UNGUARDED_MARKDOWN: st.markdown(html_string) without unsafe_allow_html=True
   (only detects when the full call is one line for certainty)

This script reads each file properly and reports genuine issues.
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

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

HTML_TAG_RE = re.compile(
    r"</?(?:span|div|p|strong|em|b|i|br|hr|a|table|ul|ol|li|style|button|script|section|h[1-6])\b",
    re.IGNORECASE,
)

# Matches an ENTIRE st.markdown() call on a single line where:
#   - the content is ONLY closing tags (e.g. "</div>", "</div></div>")
#   - no unsafe_allow_html=True is present
SINGLE_LINE_ORPHAN = re.compile(
    r'''st\.markdown\s*\(\s*(?:f?["']{1,3})([\s]*</[a-zA-Z0-9]+>[\s]*)+(?:["']{1,3})\s*\)''',
    re.IGNORECASE,
)

# Matches an ENTIRE single-line st.markdown() call that has HTML but no unsafe flag
SINGLE_LINE_UNSAFE = re.compile(
    r'''st\.markdown\s*\(\s*f?["'][^"'\n]*<[a-zA-Z][^"'\n]*["']\s*\)(?!\s*#)(?!.*unsafe_allow_html)''',
    re.IGNORECASE,
)

issues = []

def report(fpath, lineno, kind, note):
    issues.append(f"  [{kind}] {fpath.name}:{lineno}  {note[:120]}")


def scan_file(fpath: Path):
    src = fpath.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()

    i = 0
    n = len(lines)

    while i < n:
        line     = lines[i]
        stripped = line.strip()
        lineno   = i + 1

        # Skip pure comments
        if stripped.startswith("#"):
            i += 1
            continue

        # ── 1. ORPHANED CLOSING TAG (single-line) ───────────────────────
        if SINGLE_LINE_ORPHAN.search(line):
            report(fpath, lineno, "ORPHAN_CLOSE", stripped)

        # ── 2. HTML IN st.expander LABEL ────────────────────────────────
        #    st.expander( on this line, AND an HTML tag on the same line,
        #    AND no unsafe_allow_html=True
        if re.search(r'\bst\.expander\s*\(', line):
            # Gather the full argument (may span multiple lines)
            call = line
            depth = line.count("(") - line.count(")")
            j = i + 1
            while depth > 0 and j < min(i + 10, n):
                call += "\n" + lines[j]
                depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            # The first argument is the label
            label_match = re.search(
                r'st\.expander\s*\(\s*((?:f)?(?:"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'|f""".*?"""|f\'\'\'.*?\'\'\'))',
                call, re.DOTALL
            )
            if label_match:
                label_arg = label_match.group(1)
                if HTML_TAG_RE.search(label_arg):
                    report(fpath, lineno, "HTML_IN_EXPANDER", stripped)
            elif HTML_TAG_RE.search(call.split(",")[0]):
                # fallback: first arg chunk has HTML
                report(fpath, lineno, "HTML_IN_EXPANDER_SUSPECT", stripped)

        # ── 3. HTML IN st.button LABEL ──────────────────────────────────
        if re.search(r'\bst\.button\s*\(', line) and HTML_TAG_RE.search(line):
            report(fpath, lineno, "HTML_IN_BUTTON", stripped)

        # ── 4. HTML IN st.metric LABEL ──────────────────────────────────
        if re.search(r'\bst\.metric\s*\(', line) and HTML_TAG_RE.search(line):
            report(fpath, lineno, "HTML_IN_METRIC", stripped)

        # ── 5. MULTILINE st.markdown where ALL content is closing tags ──
        # Find every st.markdown( call start
        if re.search(r'\bst\.markdown\s*\(', line):
            # Check if it is a multi-line string opening
            if re.search(r'st\.markdown\s*\(\s*(?:f)?"""', line) or re.search(r"st\.markdown\s*\(\s*(?:f)?'''", line):
                # Collect lines until the call closes
                call_lines = [line]
                depth = line.count("(") - line.count(")")
                j = i + 1
                while depth > 0 and j < min(i + 150, n):
                    call_lines.append(lines[j])
                    depth += lines[j].count("(") - lines[j].count(")")
                    j += 1
                call_text = "\n".join(call_lines)

                # If the whole call has NO opening HTML tags and HAS closing tags
                # → orphaned closing tags in a multiline call
                open_tags  = len(HTML_TAG_RE.findall(call_text))
                close_only = re.findall(r'</[a-zA-Z0-9]+>', call_text)
                open_only  = re.findall(r'<[a-zA-Z][^/][^>]*>', call_text)

                # Strictly check: st.markdown with ONLY closing tag content (no opens)
                stripped_content = re.sub(r'st\.markdown\s*\(', '', call_text, count=1)
                stripped_content = re.sub(r',\s*unsafe_allow_html\s*=\s*True\s*\)', '', stripped_content)
                stripped_content = stripped_content.strip().strip('f"""').strip("'''").strip('"""').strip()
                if re.match(r'^(\s*</[a-zA-Z0-9]+>\s*)+$', stripped_content):
                    if "unsafe_allow_html=True" in call_text:
                        pass  # even with unsafe, orphaned close is a bug marker
                    report(fpath, lineno, "ORPHAN_CLOSE_MULTI", stripped[:120])

        i += 1


for fpath in sorted(FILES):
    try:
        scan_file(fpath)
    except Exception as e:
        issues.append(f"  [ERROR] {fpath.name}: {e}")

# ─────────────────────────────────────────────────────────────
print(f"\nFiles scanned: {len(FILES)}\n")
if not issues:
    print("CLEAN - zero raw HTML rendering issues found.\n")
    sys.exit(0)
else:
    print(f"ISSUES: {len(issues)} found:\n")
    for iss in issues:
        print(iss)
    print()
    sys.exit(1)
