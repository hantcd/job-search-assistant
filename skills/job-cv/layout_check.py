#!/usr/bin/env python3
"""Layout check for a CV or cover letter PDF (built with pdfLaTeX), by script so nothing is missed.

Usage: python3 layout_check.py file.pdf [file.log] [--pages N]
  --pages  the page limit from the CV's style preset (default 1)

Checks: page limit; text extractable (so an ATS can read it); margins at least
0.4in; body text 10pt or larger and nothing under 8.5pt; content reaching the
bottom 15% of the page; no gap of more than about three lines; no bullet whose
last line holds only 1-2 words; no heading stranded in the bottom 10%; no
overfull lines in the LaTeX log; fonts embedded; and, on CVs over one page, no
earlier page ending well short of the bottom and no entry title left at the
bottom of a page with its bullets on the next (ideas from ai-job-search's
verify_layout.py, MIT, Mads Lorentzen).
Prints PASS/FAIL/WARN per check and exits 1 if any hard check fails.
If a check fails, fix the content, not the layout: cut or shorten the
lowest-value entry and recompile. Never shrink fonts or margins below these floors.
Needs PyMuPDF (pip install pymupdf).
"""
import re
import sys
try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:  # older installs
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF is missing: pip install pymupdf")


def page_lines(page):
    lines = []  # (y0, y1, x0, x1, text, size, bold)
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            lettered = [s for s in spans if re.search(r"[A-Za-z0-9]", s["text"])]
            x0, y0, x1, y1 = line["bbox"]
            text = "".join(s["text"] for s in spans).strip()
            size = min((s["size"] for s in lettered), default=99)  # bullet glyphs don't count
            bold = bool(lettered) and all((s["flags"] & 16) or "bold" in s["font"].lower() for s in lettered)
            lines.append((y0, y1, x0, x1, text, size, bold))
    return sorted(lines)


def check(pdf_path, log_path=None, max_pages=1):
    doc = fitz.open(pdf_path)
    results = []  # (name, ok, detail, hard)

    def add(name, ok, detail, hard=True):
        results.append((name, ok, detail, hard))

    add("pages", doc.page_count <= max_pages, f"{doc.page_count} page(s), limit {max_pages}")
    pages = [doc[i] for i in range(min(doc.page_count, max_pages))]
    W, H = pages[0].rect.width, pages[0].rect.height
    per_page = [page_lines(p) for p in pages]
    all_lines = [l for ls in per_page for l in ls]

    words = sum(len(p.get_text("words")) for p in pages)
    add("text extractable", words > 50, f"{words} words extracted")

    if all_lines:
        m_left = min(l[2] for l in all_lines); m_right = W - max(l[3] for l in all_lines)
        m_top = min(ls[0][0] for ls in per_page if ls); m_bottom = H - max(ls[-1][1] for ls in per_page if ls)
        m = min(m_left, m_right, m_top, m_bottom)
        add("margins", m >= 29, f"left {m_left:.0f}, right {m_right:.0f}, top {m_top:.0f}, bottom {m_bottom:.0f} pt (min 29)")
        last = per_page[-1] or all_lines
        fill = max(l[1] for l in last) / H
        add("page fill", fill >= 0.85, f"content ends at {fill:.0%} of the last page (want 85%+)", hard=False)
        sizes = [round(l[5], 1) for l in all_lines if l[5] < 99]
        smallest = min(sizes); body = max(set(sizes), key=sizes.count)
        add("font size", smallest >= 8.5 and body >= 9.9,
            f"body text {body}pt, smallest {smallest}pt (body 10pt+, nothing under 8.5pt)")

    big, widows, heads = [], [], []
    for page, lines in zip(pages, per_page):
        for i in range(len(lines) - 1):
            g = lines[i + 1][0] - lines[i][1]
            if g > 36:
                big.append((g, lines[i][4][:40]))
        wboxes = page.get_text("words")

        def words_in(l):
            return sum(1 for w in wboxes if l[0] - 1 <= (w[1] + w[3]) / 2 <= l[1] + 1
                       and l[2] - 1 <= (w[0] + w[2]) / 2 <= l[3] + 1)
        for i, l in enumerate(lines):
            prev = lines[i - 1] if i else None
            if prev and words_in(l) <= 2 and abs(l[0] - prev[1]) < 4 and l[2] > prev[2] + 5 \
                    and not l[4].startswith(("\u2022", "\u25e6")):
                widows.append(l[4])
        heads += [l for l in lines if l[5] >= 11.5 and l[0] > H * 0.9]
    add("no large gaps", not big, "none" if not big else "; ".join(f"{g:.0f}pt after '{t}'" for g, t in big), hard=False)
    add("no 1-2 word bullet endings", not widows, "none" if not widows else ", ".join(f"'{w}'" for w in widows), hard=False)
    add("no heading stranded at bottom", not heads, "none" if not heads else heads[0][4])

    if len(pages) > 1:
        short, orphans = [], []
        for n, lines in enumerate(per_page[:-1], 1):
            if lines and max(l[1] for l in lines) / H < 0.80:
                short.append("page %d ends at %d%%" % (n, 100 * max(l[1] for l in lines) / H))
            nxt = per_page[n] if n < len(per_page) else []
            if lines and nxt:
                first = nxt[0]
                bulleted = first[4].startswith(("\u2022", "\u25e6", "-", "\u2013")) or not first[6]
                # an entry's title block (a bold title, maybe an italic company/date line under it)
                for cand in lines[-2:]:
                    after = lines[lines.index(cand) + 1:]
                    if cand[6] and bulleted and len(cand[4].split()) <= 12 and \
                            not any(l[4].startswith(("\u2022", "\u25e6")) for l in after):
                        orphans.append("'%s' at the bottom of page %d, its details on page %d" % (cand[4][:50], n, n + 1))
                        break
        add("no early page break", not short, "none" if not short else "; ".join(short), hard=False)
        add("no orphaned entry title", not orphans, "none" if not orphans else "; ".join(orphans))

    if log_path:
        log = open(log_path, encoding="latin-1").read()
        over = re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)
        worst = max(map(float, over)) if over else 0
        add("no overfull lines", worst < 1.0, f"{len(over)} overfull box(es), worst {worst:.1f}pt")

    fonts = {f for p in pages for f in p.get_fonts()}
    add("fonts embedded", all(f[1] != "n/a" for f in fonts), f"{len(fonts)} font(s)")
    return results


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if not a.startswith("--")]
    max_pages = 1
    if "--pages" in argv:
        max_pages = int(argv[argv.index("--pages") + 1])
        args = [a for a in args if a != str(max_pages)]
    if not args:
        print(__doc__)
        return 2
    results = check(args[0], args[1] if len(args) > 1 else None, max_pages)
    bad = False
    for name, ok, detail, hard in results:
        tag = "PASS" if ok else ("FAIL" if hard else "WARN")
        bad |= (not ok and hard)
        print(f"{tag:4}  {name:30} {detail}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
