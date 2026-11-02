"""Shared text helpers for keywords.py and truth_check.py (standard library; PyMuPDF only for PDFs)."""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# Terms that are also ordinary words, nationalities or very short: matched case-sensitively,
# and only ever a warning in the truth check, never a failure.
AMBIGUOUS = {"R", "Go", "Word", "Spring", "Sage", "Swift", "Rust", "Node", "React", "Oracle", "lean",
             "tax", "audit", "validation", "Workday", "AI", "UI", "UX", "AP", "AR", "QA", "QC", "ML", "JS",
             "TS", "Git", "Irish", "French", "German", "Spanish", "Italian", "Polish", "Chinese", "Japanese",
             "Arabic", "Portuguese", "Scrum", "Agile", "ERP", "CAD", "PLC", "SEM", "B2B", "B2C"}


def load_terms(path=None):
    with open(path or os.path.join(HERE, "terms.json"), encoding="utf-8") as fh:
        return [t for t in json.load(fh)["terms"]]


def read_text(path):
    """Plain text from .md/.txt/.tex/.pdf."""
    if path.lower().endswith(".pdf"):
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(path)
        return "\n".join(p.get_text() for p in doc)
    text = open(path, encoding="utf-8").read()
    if path.lower().endswith(".tex"):
        text = tex_to_text(text)
    return text


def tex_to_text(s):
    i = s.find("\\begin{document}")
    if i >= 0:
        s = s[i:]  # the content, not the preamble
    s = re.sub(r"(?m)(?<!\\)%.*$", "", s)  # comments, not \%
    s = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})?", " ", s)
    s = re.sub(r"-?\d*\.?\d+(?:pt|in|em|cm|mm|ex)\b", " ", s)
    s = s.replace("\\%", "%").replace("\\&", "&").replace("\\$", "$").replace("\\#", "#").replace("\\_", "_")
    s = re.sub(r"\\(?:href)\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", s)
    s = s.replace("{", " ").replace("}", " ").replace("$|$", " | ").replace("~", " ")
    return re.sub(r"[ \t]+", " ", s)


def term_regex(word):
    esc = re.escape(word)
    flags = 0 if (word in AMBIGUOUS or len(word) <= 3) else re.I
    return re.compile(r"(?<![\w+#.])" + esc + r"(?![\w+#])", flags)


def find_terms(text, terms):
    """Return {canonical: wording_found} for every term in text."""
    found = {}
    for group in terms:
        hits = [w for w in group if term_regex(w).search(text)]
        if hits:
            found[group[0]] = max(hits, key=len)  # 'MS Excel' beats 'Excel' inside it
    return found


NUM_RE = re.compile(r"(?<![\w.])(?:[€$£]\s?)?\d[\d,]*(?:\.\d+)?\s?(?:%|per ?cent|percent|k|K|m|M|bn|x|×)?(?![\w])")


def numbers(text):
    """Normalised numbers: '€1,200' -> '1200', '38 per cent' -> '38%', '4M' -> '4m'. Dates stay as years/day numbers."""
    out = set()
    for m in NUM_RE.finditer(text):
        raw = m.group(0)
        n = re.sub(r"[€$£,\s]", "", raw)
        n = re.sub(r"(per ?cent|percent)$", "%", n, flags=re.I)
        n = n.replace("×", "x")
        n = re.sub(r"([kmKM])$", lambda x: x.group(1).lower(), n)
        if re.fullmatch(r"\d", n):  # single digits are mostly list markers and ordinals; still compared
            pass
        out.add(n)
    return out


def number_core(n):
    return re.sub(r"[%xkm]|bn$", "", n)
