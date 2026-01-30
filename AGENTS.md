# AGENTS

This repo is a CLI pipeline for turning a LinkedIn PDF into JSON Resume, Europass XML, and LaTeX/PDF. If you need to tweak the output for your own resume, here is a quick guide to where to make changes and how to validate them.

## Where to change things
- LinkedIn PDF parsing: `linkedin_resume_parser/parser.py`
- Post-processing/merging extra data: `linkedin_resume_parser/cli.py`
  - Merges `personal_info.json`, `Skills.csv`, `Certifications.csv`, `Projects.csv`.
- Europass export mapping: `linkedin_resume_parser/europass.py`
- LaTeX rendering and layout logic: `linkedin_resume_parser/latex.py`
  - Controls section layout, headings, and text formatting.
- LaTeX templates: `template.tex` and `template_basic.tex`

## Typical customization workflow
1. Run the pipeline on your LinkedIn PDF:
   - `.\linkedin-to-latex-pdf.ps1 -LinkedInPdf path\to\LinkedIn_Profile.pdf`
2. Inspect the generated `*_resume.json` to find missing/misclassified fields.
3. Update the relevant Python mapping or LaTeX renderer.
4. Re-run the pipeline and verify the PDF output.

## Common tweaks
- Missing personal details: add to `personal_info.json` or extend `merge_personal_info` in `linkedin_resume_parser/cli.py`.
- Section ordering or labels: edit `apply_template` and builders in `linkedin_resume_parser/latex.py`.
- Template styling and spacing: edit `template.tex` or `template_basic.tex`.

## Debug tips
- Check `*_resume.json` first; it is the single source of truth for later steps.
- If LaTeX fails, inspect the `*.pdflatex.log` next to the output PDF.
- If something looks wrong in the PDF but `resume.json` is correct, the issue is likely in `latex.py` or the template.
- You can convert PDF pages to images to inspect what the parser sees, for example:
  - `pdftoppm -f 1 -l 1 -singlefile -png -scale-to-x 1400 -scale-to-y -1 "LinkedIn_Profile.pdf" "page1"`

## Suggested command shortcuts
- Parse only:
  - `python -m linkedin_resume_parser.cli path\to\LinkedIn_Profile.pdf -o resume.json`
- Europass only:
  - `python -m linkedin_resume_parser.europass -m personal_info.json -c europass_config.json -o europass.xml`
- LaTeX only:
  - `python -m linkedin_resume_parser.latex -t template.tex -o resume.tex`
