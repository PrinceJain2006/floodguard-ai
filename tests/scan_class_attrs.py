# -*- coding: utf-8 -*-
"""
Scan for class= attributes on HTML block/inline elements inside st.markdown calls.
Streamlit's sanitizer strips class= on arbitrary elements, causing:
  - div/span wrappers to be dropped if class= is the only attribute
  - or cards to lose styling if class= is the sole identifier

Reports every HTML element using class= (not style=) in rendered HTML strings.
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

# Match any HTML element with class= but NOT part of a CSS rule or Python comment
# Focus on elements that appear inside st.markdown HTML strings
CLASS_ATTR_RE = re.compile(
    r'<(?:div|span|section|article|aside|header|footer|main|nav|p)\b[^>]*\bclass="([^"]+)"',
    re.IGNORECASE,
)

issues = []

for fpath in sorted(FILES):
    src = fpath.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip CSS rule lines (inside <style> blocks) and Python comments
        if stripped.startswith("#") or stripped.startswith(".") or stripped.startswith("/*"):
            continue
        # Skip lines that are clearly CSS selectors
        if re.match(r'^\.[a-zA-Z][\w-]*\s*\{', stripped):
            continue
        m = CLASS_ATTR_RE.search(line)
        if m:
            cls = m.group(1)
            # Skip Streamlit's own data-testid and built-in widget classes
            if cls.startswith("st") or "stApp" in cls or "stButton" in cls:
                continue
            issues.append(
                "  [CLASS=] {name}:{lineno}  class=\"{cls}\"  ...{ctx}".format(
                    name=fpath.name, lineno=lineno, cls=cls,
                    ctx=stripped[:80]
                )
            )

print("Files scanned: {}".format(len(FILES)))
if not issues:
    print("CLEAN - no class= attributes on block elements in rendered HTML.")
    sys.exit(0)
else:
    print("FOUND {} class= attribute(s) that may be stripped by sanitizer:\n".format(len(issues)))
    for iss in issues:
        print(iss)
    sys.exit(1)
