from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

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

CYRILLIC_MAP = {
    "А": "A",
    "Б": "B",
    "В": "V",
    "Г": "G",
    "Д": "D",
    "Е": "E",
    "Ё": "E",
    "Ж": "Zh",
    "З": "Z",
    "И": "I",
    "Й": "I",
    "К": "K",
    "Л": "L",
    "М": "M",
    "Н": "N",
    "О": "O",
    "П": "P",
    "Р": "R",
    "С": "S",
    "Т": "T",
    "У": "U",
    "Ф": "F",
    "Х": "Kh",
    "Ц": "Ts",
    "Ч": "Ch",
    "Ш": "Sh",
    "Щ": "Shch",
    "Ъ": "",
    "Ы": "Y",
    "Ь": "",
    "Э": "E",
    "Ю": "Yu",
    "Я": "Ya",
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def render_resume_latex(
    resume_path: Path, template_path: Path, output_path: Path
) -> None:
    resume = load_json(resume_path)
    template = template_path.read_text(encoding="utf-8")
    rendered = apply_template(template, resume)
    output_path.write_text(rendered, encoding="utf-8")


def apply_template(template: str, resume: dict[str, Any]) -> str:
    basics = resume.get("basics", {})
    name = latex_escape(basics.get("name", ""))
    contact_line = build_contact_line(basics)
    education_section = build_education_section(resume.get("education", []))
    experience_section = build_experience_section(resume.get("work", []))
    project_section = build_project_section(resume.get("projects", []))
    skills_block = build_skills_block(resume.get("skills", []))

    replacements = {
        "{{NAME}}": name,
        "{{CONTACT_LINE}}": contact_line,
        "{{EDUCATION_SECTION}}": education_section,
        "{{EXPERIENCE_SECTION}}": experience_section,
        "{{PROJECT_SECTION}}": project_section,
        "{{SKILLS_BLOCK}}": skills_block,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


def build_contact_line(basics: dict[str, Any]) -> str:
    parts = []
    phone = (basics.get("phone") or "").strip()
    email = (basics.get("email") or "").strip()
    profiles = basics.get("profiles") or []
    linkedin = find_profile(profiles, "LinkedIn")
    github = find_profile(profiles, "GitHub")

    if phone:
        parts.append(latex_escape(phone))
    if email:
        email_text = latex_escape(email)
        parts.append(rf"\href{{mailto:{email_text}}}{{\underline{{{email_text}}}}}")
    if linkedin:
        parts.append(build_profile_link(linkedin))
    if github:
        parts.append(build_profile_link(github))

    return r" $|$ ".join(parts)


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


def build_education_section(education: list[dict[str, Any]]) -> str:
    entries = build_education_entries(education)
    if not entries:
        return ""
    return (
        "\\section{Education}\n"
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
        items = []
        summary = (entry.get("summary") or "").strip()
        if summary:
            items.append(summary)
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


def build_experience_section(work: list[dict[str, Any]]) -> str:
    entries = build_experience_entries(work)
    if not entries:
        return ""
    return (
        "\\section{Experience}\n"
        "  \\resumeSubHeadingListStart\n"
        f"    {entries}\n"
        "  \\resumeSubHeadingListEnd\n"
    )


def build_project_entries(projects: list[dict[str, Any]]) -> str:
    lines = []
    for entry in projects:
        name = latex_escape(entry.get("name", ""))
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
        return r"\textbf{Skills}{: }"
    return rf"\textbf{{Skills}}{{: {names}}}"


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


def latex_escape(value: str) -> str:
    if not value:
        return ""
    value = to_ascii(value)
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
    value = to_ascii(value)
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


def to_ascii(value: str) -> str:
    if not value:
        return ""
    value = "".join(CYRILLIC_MAP.get(ch, ch) for ch in value)
    return value.encode("ascii", "ignore").decode("ascii")


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
    for profile in profiles:
        if (profile.get("network") or "").lower() == network.lower():
            return profile
    return None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render resume.json into a LaTeX template."
    )
    parser.add_argument("resume", type=Path, help="Path to resume.json")
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
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    render_resume_latex(args.resume, args.template, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
