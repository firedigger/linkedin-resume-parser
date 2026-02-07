from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from unidecode import unidecode

MONTHS = {
    "01": "Jan.",
    "02": "Feb.",
    "03": "Mar.",
    "04": "Apr.",
    "05": "May",
    "06": "Jun.",
    "07": "Jul.",
    "08": "Aug.",
    "09": "Sep.",
    "10": "Oct.",
    "11": "Nov.",
    "12": "Dec.",
}

_LATINIZE = False


def render_resume_latex(
    resume_path: Path,
    template_path: Path,
    output_path: Path,
    basic_mode: bool = False,
    latinize: bool = False,
    font_name: str | None = None,
    theme: str = "light",
) -> None:
    resume = load_json(resume_path)
    global _LATINIZE
    _LATINIZE = latinize
    unicode_enabled = (not latinize) and contains_non_ascii(resume)
    template = template_path.read_text(encoding="utf-8")
    rendered = apply_template(
        template,
        resume,
        basic_mode=basic_mode,
        unicode_enabled=unicode_enabled,
        font_name=font_name,
        theme=theme,
    )
    output_path.write_text(rendered, encoding="utf-8")


def apply_template(
    template: str,
    resume: dict[str, Any],
    basic_mode: bool = False,
    unicode_enabled: bool = False,
    font_name: str | None = None,
    theme: str = "light",
) -> str:
    basics = resume.get("basics", {})
    name = latex_escape(basics.get("name", ""))
    contact_line = build_contact_line(basics, include_location=not basic_mode)
    education_section = build_education_section(
        resume.get("education", []), include_years=not basic_mode
    )
    work_entries = resume.get("work", [])
    experience_section = build_experience_section(
        work_entries, include_years=not basic_mode
    )
    project_section = build_project_section(resume.get("projects", []))
    skills_list = build_skills_block(resume.get("skills", []))
    skills_section = build_skills_section(resume.get("skills", []))
    label_line = "" if basic_mode else build_label_line(basics)
    summary_section = "" if basic_mode else build_summary_section(basics)
    certifications_section = "" if basic_mode else build_certifications_section(
        resume.get("certificates", [])
    )
    languages_section = "" if basic_mode else build_languages_section(resume.get("languages", []))
    if unicode_enabled:
        if font_name:
            font_setup = f"\\\\usepackage{{fontspec}}\\n\\\\setmainfont{{{font_name}}}"
        else:
            font_setup = (
                "\\usepackage{fontspec}\n"
                "\\IfFontExistsTF{TeX Gyre Termes}{\\setmainfont{TeX Gyre Termes}}{\n"
                "  \\IfFontExistsTF{Times New Roman}{\\setmainfont{Times New Roman}}{\n"
                "    \\IfFontExistsTF{Libertinus Serif}{\\setmainfont{Libertinus Serif}}{\n"
                "      \\IfFontExistsTF{Latin Modern Roman}{\\setmainfont{Latin Modern Roman}}{\n"
                "        \\setmainfont{Times New Roman}\n"
                "      }\n"
                "    }\n"
                "  }\n"
                "}\n"
            )
        pdftex_setup = ""
    else:
        font_setup = "\\usepackage[T1]{fontenc}\n\\usepackage{lmodern}"
        pdftex_setup = "\\input{glyphtounicode}\n\\pdfgentounicode=1"

    theme_colors, theme_setup = build_theme(theme)

    replacements = {
        "{{NAME}}": name,
        "{{LABEL_LINE}}": label_line,
        "{{CONTACT_LINE}}": contact_line,
        "{{SUMMARY_SECTION}}": summary_section,
        "{{EDUCATION_SECTION}}": education_section,
        "{{EXPERIENCE_SECTION}}": experience_section,
        "{{PROJECT_SECTION}}": project_section,
        "{{SKILLS_SECTION}}": skills_section,
        "{{SKILLS_BLOCK}}": skills_list,
        "{{CERTIFICATIONS_SECTION}}": certifications_section,
        "{{LANGUAGES_SECTION}}": languages_section,
        "{{FONT_SETUP}}": font_setup,
        "{{PDFTEX_SETUP}}": pdftex_setup,
        "{{THEME_COLORS}}": theme_colors,
        "{{THEME_SETUP}}": theme_setup,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def build_contact_line(basics: dict[str, Any], include_location: bool = True) -> str:
    parts = []
    link_parts = []
    phone = (basics.get("phone") or "").strip()
    email = (basics.get("email") or "").strip()
    location = build_location(basics.get("location") or {}) if include_location else ""
    profiles = basics.get("profiles") or []
    linkedin = find_profile(profiles, "LinkedIn")
    github = find_profile(profiles, "GitHub")

    if location:
        parts.append(latex_escape(location))
    if phone:
        parts.append(latex_escape(phone))
    if email:
        email_text = latex_escape(email)
        parts.append(rf"\href{{mailto:{email_text}}}{{\underline{{{email_text}}}}}")
    if linkedin:
        link_parts.append(build_profile_link(linkedin))
    if github:
        link_parts.append(build_profile_link(github))

    if link_parts:
        parts.extend(link_parts)

    if len(parts) <= 4 or not link_parts:
        return r" $|$ ".join(parts)

    primary = parts[:-len(link_parts)]
    secondary = link_parts
    return r" $|$ ".join(primary) + r" \\" + "\n" + r" $|$ ".join(secondary)


def build_profile_link(profile: dict[str, Any]) -> str:
    url = (profile.get("url") or "").strip()
    label = (profile.get("label") or "").strip()
    if not label:
        label = strip_scheme(url)
    if not url:
        return latex_escape(label)
    label_text = latex_escape(label)
    url_text = latex_escape_url(normalize_url(url))
    return rf"\href{{{url_text}}}{{\underline{{{label_text}}}}}"


def build_location(location: dict[str, Any]) -> str:
    address = (location.get("address") or "").strip()
    if address:
        return address
    parts = []
    for key in ("city", "region", "countryCode"):
        value = (location.get(key) or "").strip()
        if value:
            parts.append(value)
    return ", ".join(parts)


def build_label_line(basics: dict[str, Any]) -> str:
    label = (basics.get("label") or "").strip()
    if not label:
        return ""
    label_text = latex_escape(label)
    return rf"\small \textit{{{label_text}}} \\ \vspace{{1pt}}"


def build_summary_section(basics: dict[str, Any]) -> str:
    summary = (basics.get("summary") or "").strip()
    if not summary:
        return ""
    summary_text = latex_escape(summary)
    return "\\section{Summary}\n  \\small{" + summary_text + "}\n"


def build_education_entries(education: list[dict[str, Any]]) -> str:
    lines = []
    for entry in education:
        institution = latex_escape(entry.get("institution", ""))
        location = latex_escape(entry.get("location", ""))
        degree = latex_escape(build_degree_line(entry))
        dates = latex_escape(format_date_range(entry.get("startDate"), entry.get("endDate")))
        lines.append(
            r"\resumeSubheading"
            f"\n      {{{institution}}}{{{location}}}\n"
            f"      {{{degree}}}{{{dates}}}"
        )
    return "\n    ".join(lines)


def build_education_section(
    education: list[dict[str, Any]], include_years: bool = True
) -> str:
    entries = build_education_entries(education)
    if not entries:
        return ""
    title = "Education"
    if include_years:
        years = calculate_education_years(education)
        if years:
            title = f"Education ({years} years)"
    return (
        f"\\section{{{title}}}\n"
        "  \\resumeSubHeadingListStart\n"
        f"    {entries}\n"
        "  \\resumeSubHeadingListEnd\n"
    )


def build_degree_line(entry: dict[str, Any]) -> str:
    study_type = (entry.get("studyType") or "").strip()
    area = (entry.get("area") or "").strip()
    if study_type and area:
        return f"{study_type} in {area}"
    return study_type or area


def build_experience_entries(work: list[dict[str, Any]]) -> str:
    lines = []
    for entry in work:
        company = latex_escape(entry.get("name", ""))
        role = latex_escape(entry.get("position", ""))
        location = latex_escape(entry.get("location", ""))
        dates = latex_escape(format_date_range(entry.get("startDate"), entry.get("endDate")))
        lines.append(
            r"\resumeSubheading"
            f"\n      {{{company}}}{{{dates}}}\n"
            f"      {{{role}}}{{{location}}}"
        )
        summary = (entry.get("summary") or "").strip()
        if summary:
            lines.append(f"      \\small{{{latex_escape(summary)}}}")
        items = []
        for highlight in entry.get("highlights") or []:
            if highlight:
                items.append(highlight)
        if items:
            lines.append("      \\resumeItemListStart")
            for item in items:
                lines.append(f"        \\resumeItem{{{latex_escape(item)}}}")
            lines.append("      \\resumeItemListEnd")
        lines.append("")
    return "\n    ".join(lines).rstrip()


def build_experience_section(
    work: list[dict[str, Any]], include_years: bool = True
) -> str:
    entries = build_experience_entries(work)
    if not entries:
        return ""
    title = "Experience"
    if include_years:
        years = calculate_years_experience(work)
        if years:
            title = f"Experience ({years} years)"
    return (
        f"\\section{{{title}}}\n"
        "  \\resumeSubHeadingListStart\n"
        f"    {entries}\n"
        "  \\resumeSubHeadingListEnd\n"
    )


def build_project_entries(projects: list[dict[str, Any]]) -> str:
    lines = []
    for entry in projects:
        name_raw = (entry.get("name") or "").strip()
        if not name_raw:
            continue
        url = (entry.get("url") or "").strip()
        name = latex_escape(name_raw)
        if url:
            url_text = latex_escape_url(normalize_url(url))
            name = rf"\href{{{url_text}}}{{\underline{{{name}}}}}"
        description = latex_escape(entry.get("description", ""))
        date_range = latex_escape(format_date_range(entry.get("startDate"), entry.get("endDate")))
        header = r"\resumeProjectHeading" f"\n          {{\\textbf{{{name}}}}}{{{date_range}}}"
        lines.append(header)
        if description:
            lines.append("          \\resumeItemListStart")
            lines.append(f"            \\resumeItem{{{description}}}")
            lines.append("          \\resumeItemListEnd")
    return "\n      ".join(lines)


def build_project_section(projects: list[dict[str, Any]]) -> str:
    entries = build_project_entries(projects)
    if not entries:
        return ""
    return (
        "\\section{Projects}\n"
        "    \\resumeSubHeadingListStart\n"
        f"      {entries}\n"
        "    \\resumeSubHeadingListEnd\n"
    )


def build_skills_list(skills: list[dict[str, Any]]) -> str:
    names = []
    for entry in skills:
        name = (entry.get("name") or "").strip()
        if name:
            names.append(latex_escape(name))
    return ", ".join(names)


def build_skills_block(skills: list[dict[str, Any]]) -> str:
    names = build_skills_list(skills)
    if not names:
        return ""
    return names


def build_skills_section(skills: list[dict[str, Any]]) -> str:
    names = build_skills_block(skills)
    if not names:
        return ""
    return (
        "\\section{Technical Skills}\n"
        " \\begin{itemize}[leftmargin=0.15in, label={}]\n"
        f"    \\small{{\\item{{\n     {names}\n    }}}}\n"
        " \\end{itemize}\n"
    )


def build_certification_lines(certificates: list[dict[str, Any]]) -> list[str]:
    lines = []
    for entry in certificates:
        name_raw = (entry.get("name") or "").strip()
        if not name_raw:
            continue
        issuer = (entry.get("issuer") or "").strip()
        date_text = format_date(entry.get("date")) if entry.get("date") else ""
        url = (entry.get("url") or "").strip()
        meta_parts = []
        if issuer:
            meta_parts.append(latex_escape(issuer))
        if date_text:
            meta_parts.append(latex_escape(date_text))
        name_text = latex_escape(name_raw)
        if url:
            url_text = latex_escape_url(normalize_url(url))
            name_text = rf"\href{{{url_text}}}{{\underline{{{name_text}}}}}"
        if meta_parts:
            lines.append(f"{name_text} ({', '.join(meta_parts)})")
        else:
            lines.append(name_text)
    return lines


def build_certifications_section(certificates: list[dict[str, Any]]) -> str:
    lines = build_certification_lines(certificates)
    if not lines:
        return ""
    items = "\n".join(f"    \\resumeItem{{{line}}}" for line in lines)
    return (
        "\\section{Certifications}\n"
        "  \\resumeItemListStart\n"
        f"{items}\n"
        "  \\resumeItemListEnd\n"
    )


def build_languages_section(languages: list[dict[str, Any]]) -> str:
    lines = []
    for entry in languages:
        language = (entry.get("language") or "").strip()
        if not language:
            continue
        fluency = (entry.get("fluency") or "").strip()
        language_text = latex_escape(language)
        if fluency:
            lines.append(f"{language_text} --- {latex_escape(fluency)}")
        else:
            lines.append(language_text)
    if not lines:
        return ""
    items = "\n".join(f"    \\resumeItem{{{line}}}" for line in lines)
    return (
        "\\section{Languages}\n"
        "  \\resumeItemListStart\n"
        f"{items}\n"
        "  \\resumeItemListEnd\n"
    )


def format_date_range(start: str | None, end: str | None) -> str:
    start_text = format_date(start)
    end_text = format_date(end) if end else "Present"
    if start_text and end_text:
        return f"{start_text} -- {end_text}"
    return start_text or end_text


def format_date(value: str | None) -> str:
    if not value:
        return ""
    parts = value.split("-")
    year = parts[0]
    if len(parts) == 1:
        return year
    month = MONTHS.get(parts[1], parts[1])
    return f"{month} {year}"


def calculate_years_experience(work: list[dict[str, Any]]) -> int:
    total_months = 0
    today = datetime.today()
    for entry in work:
        start = parse_year_month(entry.get("startDate"))
        end_raw = entry.get("endDate")
        if end_raw:
            end = parse_year_month(end_raw) or today
        else:
            end = today
        if not start or not end:
            continue
        if end < start:
            continue
        total_months += (end.year - start.year) * 12 + (end.month - start.month)
    if total_months <= 0:
        return 0
    return max(1, total_months // 12)


def calculate_education_years(education: list[dict[str, Any]]) -> int:
    start_dates = []
    end_dates = []
    for entry in education:
        start = parse_year_month(entry.get("startDate"))
        end_raw = entry.get("endDate")
        end = parse_year_month(end_raw) if end_raw else None
        if start:
            start_dates.append(start)
        if end:
            end_dates.append(end)
        elif start:
            end_dates.append(start)
    if not start_dates or not end_dates:
        return 0
    start = min(start_dates)
    end = max(end_dates)
    if end < start:
        return 0
    total_months = (end.year - start.year) * 12 + (end.month - start.month)
    if total_months <= 0:
        return 0
    return max(1, total_months // 12)


def parse_year_month(value: str | None) -> datetime | None:
    if not value:
        return None
    parts = value.split("-")
    if not parts[0].isdigit():
        return None
    year = int(parts[0])
    month = 1
    if len(parts) > 1 and parts[1].isdigit():
        month = max(1, min(12, int(parts[1])))
    return datetime(year, month, 1)


def latex_escape(value: str) -> str:
    if not value:
        return ""
    if _LATINIZE:
        value = latinize_text(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = value
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def latex_escape_url(value: str) -> str:
    if not value:
        return ""
    if _LATINIZE:
        value = latinize_text(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        " ": r"\%20",
    }
    escaped = value
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def latinize_text(value: str) -> str:
    if not value:
        return ""
    return unidecode(value)


def contains_non_ascii(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return any(ord(ch) > 127 for ch in value)
    if isinstance(value, dict):
        return any(
            contains_non_ascii(key) or contains_non_ascii(val)
            for key, val in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_non_ascii(item) for item in value)
    return False


def normalize_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def strip_scheme(value: str) -> str:
    if value.startswith("http://"):
        return value[len("http://") :]
    if value.startswith("https://"):
        return value[len("https://") :]
    return value


def find_profile(profiles: list[dict[str, Any]], network: str) -> dict[str, Any] | None:
    matches = []
    for profile in profiles:
        if (profile.get("network") or "").lower() == network.lower():
            if (profile.get("url") or "").strip():
                return profile
            matches.append(profile)
    if matches:
        return matches[0]
    return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_theme(theme: str) -> tuple[str, str]:
    if theme == "light":
        colors = (
            "\\definecolor{ResumeBg}{HTML}{FFFFFF}\n"
            "\\definecolor{ResumeText}{HTML}{111111}\n"
            "\\definecolor{ResumeRule}{HTML}{111111}\n"
            "\\definecolor{ResumeLink}{HTML}{005A9C}\n"
        )
    else:
        colors = (
            "\\definecolor{ResumeBg}{HTML}{0F1115}\n"
            "\\definecolor{ResumeText}{HTML}{E6E6E6}\n"
            "\\definecolor{ResumeRule}{HTML}{9AA4B2}\n"
            "\\definecolor{ResumeLink}{HTML}{6FB1FF}\n"
        )
    setup = (
        "\\pagecolor{ResumeBg}\n"
        "\\color{ResumeText}\n"
        "\\hypersetup{colorlinks=true, urlcolor=ResumeLink, linkcolor=ResumeLink}\n"
    )
    return colors, setup


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render resume.json into a LaTeX template."
    )
    parser.add_argument(
        "resume",
        type=Path,
        nargs="?",
        default=Path("resume.json"),
        help="Path to resume.json",
    )
    parser.add_argument(
        "-t",
        "--template",
        type=Path,
        default=Path("template.tex"),
        help="Path to LaTeX template file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("resume.tex"),
        help="Output LaTeX file path",
    )
    parser.add_argument(
        "--basic",
        action="store_true",
        help="Render only the original template sections.",
    )
    parser.add_argument(
        "--latinize",
        action="store_true",
        help="Transliterate non-ASCII text to ASCII for pdflatex.",
    )
    parser.add_argument(
        "--font",
        help="Font name for Unicode output (used with xelatex/lualatex).",
    )
    parser.add_argument(
        "--dark",
        action="store_true",
        help="Use dark theme output (default is light).",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    template_path = args.template
    if args.basic and template_path == Path("template.tex"):
        basic_template = Path("template_basic.tex")
        if basic_template.exists():
            template_path = basic_template
    theme = "dark" if args.dark else "light"
    if args.basic:
        theme = "light"
    render_resume_latex(
        args.resume,
        template_path,
        args.output,
        basic_mode=args.basic,
        latinize=args.latinize,
        font_name=args.font,
        theme=theme,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
