"""
Final definitive audit: find st.markdown calls with HTML that are missing unsafe_allow_html.
"""
import pathlib
import re
import sys

root = pathlib.Path(__file__).parent.parent

HTML_TAG = re.compile(
    r'<(?:div|span|p|br|hr|strong|em|b|i|section|table|thead|tbody|tr|td|th|ul|ol|li|button|a\s)[^>]*>'
)

issues = []
files_checked = 0

for pyfile in sorted(root.rglob("*.py")):
    if ".venv" in str(pyfile) or "__pycache__" in str(pyfile):
        continue
    files_checked += 1
    src = pyfile.read_text(encoding="utf-8", errors="ignore")
    lines = src.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        # Only match lines that contain st.markdown(
        if not re.search(r'st\.markdown\s*\(', line):
            i += 1
            continue

        start_line = i

        # Check if this is a SINGLE-LINE complete call  e.g.  st.markdown("---")
        # Count parens on just this line after st.markdown(
        match_pos = re.search(r'st\.markdown\s*\(', line).end()
        line_after = line[match_pos - 1:]  # includes the opening paren
        depth = 0
        for ch in line_after:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
        if depth <= 0:
            # Single-line call — collect only this line
            block = line
            has_html = bool(HTML_TAG.search(block))
            has_unsafe = "unsafe_allow_html=True" in block
            if has_html and not has_unsafe:
                rel = pyfile.relative_to(root)
                issues.append((str(rel), start_line + 1, block.strip()[:120]))
            i += 1
            continue

        # Multi-line call — collect until depth returns to 0
        call_lines = [line]
        depth_total = depth  # remaining depth after first line
        j = i + 1
        while j < min(i + 200, len(lines)) and depth_total > 0:
            l = lines[j]
            call_lines.append(l)
            for ch in l:
                if ch == '(':
                    depth_total += 1
                elif ch == ')':
                    depth_total -= 1
            j += 1

        block = "\n".join(call_lines)
        has_html = bool(HTML_TAG.search(block))
        has_unsafe = "unsafe_allow_html=True" in block

        if has_html and not has_unsafe:
            rel = pyfile.relative_to(root)
            issues.append((str(rel), start_line + 1, call_lines[0].strip()[:80]))

        i = j

print(f"Files checked: {files_checked}")
if issues:
    print(f"\nGENUINE ISSUES ({len(issues)}) — st.markdown with HTML but no unsafe_allow_html=True:")
    for fpath, lineno, snippet in issues:
        print(f"  {fpath}:{lineno}  →  {snippet}")
    sys.exit(1)
else:
    print("ALL CLEAR — every st.markdown with HTML tags has unsafe_allow_html=True")
