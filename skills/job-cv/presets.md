# Style presets

Presets change only these details: the font, section order, profile line,
page limit and the small additions below. Claude suggests one per role family
from its industry; the person approves it in Chat 2 (MASTER_PLAN.md).

- **TECH** (software, engineering, data, product): Jake's Resume as is; the
  default font, or a clean sans (Fira Sans or Source Sans if installed,
  otherwise Helvetica via `helvet`). One page.
- **CONSERVATIVE** (finance, consulting, law, healthcare, government):
  education first; Charter or Times (`mathptmx`); a Leadership & Activities
  section; slightly more white space. One page.
- **GENERAL** (Irish and UK business, sales, marketing, operations): a 3-4
  line profile under the name; interests or volunteering where they add
  evidence; Charter or Helvetica; two pages with 5+ years' experience only if
  the plan allows.
- **CREATIVE** (design, content, media): portfolio link in the first line;
  one accent colour; a clean sans; still one column. One page.
- **ACADEMIC** (research, lecturing): a separate multi-page CV with
  publications and grants; Palatino (`mathpazo`) or Charter.

Every preset opens with a one-line headline under the name (target title and
one proof point) unless the plan says otherwise. If a font package is
missing, use the preset's fallback: Charter, Times, Helvetica and Palatino
ship with standard LaTeX and extract cleanly. The cover letter uses the same
font and header as the CV.

Font lines for the preamble (tested with pdfLaTeX):

```latex
\usepackage{charter}                      % Charter
\usepackage{mathptmx}                     % Times
\usepackage[scaled]{helvet}\renewcommand{\familydefault}{\sfdefault}   % Helvetica
\usepackage{mathpazo}                     % Palatino
```

Ligatures (fi, fl) and small caps can break text extraction in some parsers;
`\input{glyphtounicode}` and `\pdfgentounicode=1` keep them readable. Run the
layout and parse checks (job-cv, step 5) after any font change.
