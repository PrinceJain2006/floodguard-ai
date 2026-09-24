# -*- coding: utf-8 -*-
"""
Replace all class="fg-card*" div attributes with equivalent inline style= attributes.
This ensures the card wrappers survive Streamlit's HTML sanitizer regardless of
whether it strips class= attributes.
"""
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# CSS class → inline style equivalents (from apply_global_css in ui_utils.py)
INLINE = {
    "fg-card":         "background:#131620;border:1px solid #1e2440;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem",
    "fg-card-blue":    "background:#080f1e;border:1px solid #1e3a5f;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem",
    "fg-card-danger":  "background:#150b0b;border:1px solid #7f1d1d;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem",
    "fg-card-warn":    "background:#141000;border:1px solid #78350f;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem",
    "fg-card-success": "background:#071310;border:1px solid #14532d;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.75rem",
}

files = sorted(Path("pages").glob("*.py"))
total = 0

for fpath in files:
    src = fpath.read_text(encoding="utf-8", errors="replace")
    new_src = src

    for cls, inline_style in INLINE.items():
        # Pattern A: class="fg-card..." style="extra..."
        # Merge: keep inline_style as base, append extra styles
        def make_repl(base):
            def repl(m):
                extra = m.group(1).strip().rstrip(";")
                combined = (base + ";" + extra) if extra else base
                return 'style="{}"'.format(combined)
            return repl

        pat_with_style = re.compile(
            r'class="' + re.escape(cls) + r'"\s+style="([^"]*?)"',
        )
        new_src = pat_with_style.sub(make_repl(inline_style), new_src)

        # Pattern B: class="fg-card..." with NO style= following
        pat_no_style = re.compile(
            r'class="' + re.escape(cls) + r'"(?!\s+style=)',
        )
        new_src = pat_no_style.sub('style="{}"'.format(inline_style), new_src)

    if new_src != src:
        fpath.write_text(new_src, encoding="utf-8")
        n_before = src.count('class="fg-card')
        n_after  = new_src.count('class="fg-card')
        replaced = n_before - n_after
        total += replaced
        print("FIXED {}: replaced {} fg-card class= reference(s)".format(fpath.name, replaced))

if total == 0:
    print("Nothing to fix - no remaining fg-card class= references found")
else:
    print("Total replacements: {}".format(total))
