# LinkedIn PDF → JSON Resume / Europass / LaTeX

Keep a single source of truth for your resume and export it from a LinkedIn PDF into JSON Resume, Europass XML, and a clean SWE LaTeX/PDF CV.
No LLM required. Built via OpenAI Codex.

## What this tool can do
- Parse a LinkedIn profile PDF into JSON Resume (`resume.json`) using the open schema: https://jsonresume.org
- JSON Resume can be converted into many community themes; explore options at https://jsonresume.org/themes and the CLI at https://github.com/jsonresume/resume-cli.
- Merge extra personal details from `personal_info.json` (e.g., phone, birth date, nationality) where LinkedIn lacks data.
- Export JSON Resume to Europass Candidate XML (`europass.xml`) for import into the Europass editor: https://europass.europa.eu/en
- Render JSON Resume into Jake's LaTeX resume template (`resume.tex`) and compile a PDF (`resume.pdf`).

## Disclaimer
LinkedIn PDF parsing is best-effort and may miss or misclassify fields. Always review the generated `resume.json`, `europass.xml`, and `resume.pdf` before using them. If you want to tailor the output to your resume style or data, use AI in this repo to adjust the underlying Python code. Use malformed `resume.json` output and any missing fields to pinpoint what needs fixing.

## Background
I keep my LinkedIn profile up to date and wanted a single source of truth that could generate multiple formats: Europass, and a clean PDF using Jake's popular SWE resume template.

## Requirements
- Python 3.11+
- `pdflatex` (MiKTeX or TeX Live) for LaTeX/PDF output

## Installation
```bash
pip install -r requirements.txt
```

## Usage
LinkedIn export: open the profile, click `More` → `Save to PDF`.

Quick start (full pipeline):
```powershell
.\linkedin-to-latex-pdf.ps1 -LinkedInPdf path\to\LinkedIn_Profile.pdf
```
Outputs are named from the input PDF (e.g., `LinkedIn_Profile_resume.json`, `LinkedIn_Profile_europass.xml`, `LinkedIn_Profile_SWE.pdf`).

Individual steps:
Parse a LinkedIn PDF into `resume.json`:
```bash
python -m linkedin_resume_parser.cli path\to\LinkedIn_Profile.pdf -o resume.json
```

Export `resume.json` to Europass Candidate XML:
```bash
python -m linkedin_resume_parser.europass resume.json -m personal_info.json -c europass_config.json -o europass.xml
```

Render `resume.json` to LaTeX and PDF (requires MiKTeX or TeX Live for `pdflatex`):
```powershell
.\json-to-latex-pdf.ps1 -Resume resume.json -Template template.tex -TexOut resume.tex
```

## Files
- `*_resume.json`: JSON Resume output from the LinkedIn parser.
- `personal_info.json`: Personal metadata not exported from LinkedIn (e.g., birth date, nationality).
- `europass_config.json`: Europass technical configuration (schemes, rendering, section order, ESCO URI).
- `*_europass.xml`: Europass Candidate XML output.
- `*_SWE.tex`: LaTeX output from the resume renderer.
- `*_SWE.pdf`: PDF output from `pdflatex`.

## TODO
- [ ] Upload repo to github (verify .gitignore in the process)
- [ ] Amend Jake's format itself with the help of AI (to include skipped sections like bio or summary), but do it only after pushing the frist version
