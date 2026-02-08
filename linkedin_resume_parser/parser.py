from __future__ import annotations

import dataclasses
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from statistics import median
from typing import Iterable

import pdfplumber


@dataclasses.dataclass(frozen=True)
class Line:
    text: str
    top: float
    bottom: float
    x0: float
    x1: float
    page: int


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
    "янв": 1,
    "января": 1,
    "фев": 2,
    "февраля": 2,
    "мар": 3,
    "марта": 3,
    "апр": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июн": 6,
    "июня": 6,
    "июл": 7,
    "июля": 7,
    "авг": 8,
    "августа": 8,
    "сен": 9,
    "сентября": 9,
    "окт": 10,
    "октября": 10,
    "ноя": 11,
    "ноября": 11,
    "дек": 12,
    "декабря": 12,
}

SECTION_ALIASES = {
    "about": [
        "about",
        "summary",
        "profile",
        "acerca de",
        "sobre",
        "à propos",
        "profil",
        "обо мне",
        "о себе",
        "общее",
        "общие сведения",
        "сводка",
        "профиль",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "experiencia",
        "experiencia laboral",
        "expérience",
        "ervaring",
        "berufserfahrung",
        "erfahrung",
        "experiência",
        "опыт",
        "опыт работы",
    ],
    "education": [
        "education",
        "educación",
        "formation",
        "ausbildung",
        "educacao",
        "educação",
        "istruzione",
        "образование",
    ],
    "skills": [
        "skills",
        "top skills",
        "kompetenzen",
        "kenntnisse",
        "compétences",
        "habilidades",
        "competenze",
        "competências",
        "навыки",
        "основные навыки",
        "ключевые навыки",
    ],
    "certifications": [
        "licenses & certifications",
        "licenses and certifications",
        "certifications",
        "certificazioni",
        "certificados",
        "certificats",
        "zertifikate",
        "сертификаты",
        "сертификации",
        "лицензии и сертификаты",
    ],
    "projects": [
        "projects",
        "projets",
        "proyectos",
        "projekte",
        "проекты",
    ],
    "volunteer": [
        "volunteer",
        "volunteering",
        "volontariat",
        "voluntariado",
        "волонтерство",
        "волонтерская деятельность",
    ],
    "languages": [
        "languages",
        "sprachkenntnisse",
        "langues",
        "idiomas",
        "lingue",
        "idiomas",
        "языки",
    ],
    "interests": [
        "interests",
        "hobbies",
        "centres d'interet",
        "interessi",
        "interesses",
        "aficiones",
        "интересы",
        "увлечения",
        "хобби",
    ],
}

HEADING_LOOKUP = {
    alias: key for key, aliases in SECTION_ALIASES.items() for alias in aliases
}

EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
URL_RE = re.compile(
    r"https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+|gitlab\.com/\S+",
    re.I,
)
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}"
)
PAGE_RE = re.compile(r"^page\s+\d+\s+(?:of|/)\s*\d+$", re.I)
DURATION_RE = re.compile(
    r"\b\d+\s+(?:year|years|yr|yrs|month|months|mo|mos)\b", re.I
)

DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:\w{3,9}\s+)?\d{4})\s*(?:-|\u2013|\u2014|to)\s*"
    r"(?P<end>(?:\w{3,9}\s+)?\d{4}|present|current|today)",
    re.I,
)
SINGLE_DATE_RE = re.compile(r"(?:\w{3,9}\s+)?\d{4}", re.I)


def parse_pdf(path: str) -> dict:
    lines = extract_lines(path)
    sections = split_sections(lines)
    all_text = "\n".join(line.text for line in lines)
    basics = parse_basics(lines, all_text, sections.get("about", []))
    work = parse_experience(sections.get("experience", []))
    education = parse_education(sections.get("education", []))
    skills = parse_skills(sections.get("skills", []))
    certificates = parse_certifications(sections.get("certifications", []))
    projects = parse_projects(sections.get("projects", []))
    volunteer = parse_volunteer(sections.get("volunteer", []))
    languages = parse_languages(sections.get("languages", []))
    interests = parse_interests(sections.get("interests", []))
    hobbies_marker = find_hobbies_marker(lines)
    add_interests_label_to_summary(basics, interests, hobbies_marker)

    resume = {
        "basics": basics,
        "work": work,
        "education": education,
        "skills": skills,
        "certificates": certificates,
        "projects": projects,
        "volunteer": volunteer,
        "languages": languages,
        "interests": interests,
    }
    return resume


def find_hobbies_marker(lines: list[Line]) -> str:
    split = detect_column_split(lines)
    if split is None:
        return ""
    hobbies_lines = [line for line in lines if "hobbies:" in line.text.lower()]
    if not hobbies_lines:
        return ""
    best_text = ""
    best_gap = None
    for hobby_line in hobbies_lines:
        hobby_is_left = hobby_line.x0 <= split
        candidates = [
            line
            for line in lines
            if line.page == hobby_line.page
            and (line.x0 <= split) != hobby_is_left
            and line.top >= hobby_line.top
        ]
        for line in candidates:
            text = line.text.strip()
            if not text or "hobbies" in text.lower():
                continue
            gap = line.top - hobby_line.top
            if best_gap is None or gap < best_gap:
                best_gap = gap
                best_text = text
    return best_text


def add_interests_label_to_summary(
    basics: dict, interests: list[dict], hobbies_marker: str = ""
) -> None:
    summary = (basics.get("summary") or "").strip()
    if not summary:
        return
    if re.search(r"\bhobbies\b", summary, re.I):
        return
    if not interests and not hobbies_marker:
        return

    names = [item.get("name", "").strip() for item in interests if item.get("name")]
    if names:
        interests_text = ", ".join(names)
        match = re.search(re.escape(interests_text), summary, re.I)
        if match:
            summary = summary[: match.start()] + "Hobbies: " + summary[match.start() :]
        else:
            separator = " " if summary and not summary.endswith((".", "!", "?", ":")) else " "
            summary = summary.rstrip() + separator + f"Hobbies: {interests_text}"
        basics["summary"] = summary.strip()
        return

    if hobbies_marker:
        match = re.search(re.escape(hobbies_marker), summary, re.I)
        if match:
            summary = summary[: match.start()] + "Hobbies: " + summary[match.start() :]
    basics["summary"] = summary.strip()


def extract_lines(path: str) -> list[Line]:
    lines: list[Line] = []
    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
            if not words:
                continue
            words = sorted(words, key=lambda w: (w["top"], w["x0"]))
            current_words: list[dict] = []
            current_top: float | None = None
            gap_threshold = max(30.0, page.width * 0.08)
            for word in words:
                word_top = word["top"]
                if current_top is None:
                    current_top = word_top
                    current_words.append(word)
                    continue
                if abs(word_top - current_top) <= 2.5:
                    current_words.append(word)
                else:
                    lines.extend(split_line_words(current_words, page_index, gap_threshold))
                    current_words = [word]
                    current_top = word_top
            if current_words:
                lines.extend(split_line_words(current_words, page_index, gap_threshold))
    return lines


def split_line_words(
    words: list[dict], page_index: int, gap_threshold: float
) -> list[Line]:
    words = sorted(words, key=lambda w: w["x0"])
    segments: list[list[dict]] = []
    current: list[dict] = []
    last_x1: float | None = None
    for word in words:
        if last_x1 is None:
            current = [word]
            last_x1 = word["x1"]
            continue
        if word["x0"] - last_x1 > gap_threshold:
            segments.append(current)
            current = [word]
        else:
            current.append(word)
        last_x1 = word["x1"]
    if current:
        segments.append(current)

    return [words_to_line(segment, page_index) for segment in segments]


def words_to_line(words: list[dict], page_index: int) -> Line:
    words = sorted(words, key=lambda w: w["x0"])
    text = " ".join(word["text"] for word in words).strip()
    top = min(word["top"] for word in words)
    bottom = max(word["bottom"] for word in words)
    x0 = min(word["x0"] for word in words)
    x1 = max(word["x1"] for word in words)
    return Line(text=text, top=top, bottom=bottom, x0=x0, x1=x1, page=page_index)


def split_sections(lines: list[Line]) -> dict[str, list[Line]]:
    sections: dict[str, list[Line]] = defaultdict(list)
    split = detect_column_split(lines)
    current_section: dict[str, str | None] = {"left": None, "right": None}
    for line in lines:
        if is_page_header(line.text):
            continue
        column = "right" if split and line.x0 > split else "left"
        normalized = normalize_heading(line.text)
        section = HEADING_LOOKUP.get(normalized)
        if section and looks_like_heading(line.text):
            current_section[column] = section
            continue
        active = current_section[column]
        if active:
            sections[active].append(line)
    return sections


def detect_column_split(lines: list[Line]) -> float | None:
    if len(lines) < 40:
        return None
    x0s = sorted(line.x0 for line in lines)
    gaps = [(x0s[i + 1] - x0s[i], i) for i in range(len(x0s) - 1)]
    gap, idx = max(gaps, default=(0.0, 0))
    if gap < 80:
        return None
    return (x0s[idx] + x0s[idx + 1]) / 2


def normalize_heading(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s&]+", " ", text.lower())
    return " ".join(text.split())


def looks_like_heading(text: str) -> bool:
    if len(text) > 60:
        return False
    if any(char.isdigit() for char in text):
        return False
    words = text.strip().split()
    return 1 <= len(words) <= 5


def parse_basics(lines: list[Line], all_text: str, about_lines: list[Line]) -> dict:
    name, label = pick_name_label(lines)
    location = find_location(lines[:12])
    email = EMAIL_RE.search(all_text)
    phone = find_phone(lines)
    urls = URL_RE.findall(all_text)
    profiles = build_profiles(urls, lines)
    summary = " ".join(line.text for line in about_lines if not is_noise_line(line.text)).strip()
    basics = {
        "name": name,
        "label": label,
        "email": email.group(0) if email else "",
        "phone": phone or "",
        "location": {"address": location} if location else {},
        "profiles": profiles,
        "summary": summary,
    }
    return basics


def pick_name_label(lines: list[Line]) -> tuple[str, str]:
    name = ""
    label = ""
    for line in lines[:12]:
        text = line.text.strip()
        if is_noise_line(text):
            continue
        if EMAIL_RE.search(text) or URL_RE.search(text) or PHONE_RE.search(text):
            continue
        if not name:
            name = clean_contact_name(text)
            continue
        if not label and not is_location_text(text):
            label = text
            break
    return name, label


def clean_contact_name(text: str) -> str:
    lowered = text.lower()
    if lowered.startswith("contact "):
        return text[len("contact ") :].strip()
    return text


def find_location(lines: list[Line]) -> str:
    for line in lines:
        text = line.text.strip()
        if is_location_text(text) and not EMAIL_RE.search(text):
            return text
        if " area" in text.lower():
            return text
    return ""


LOCATION_KEYWORDS = {
    "area",
    "region",
    "province",
    "state",
    "metropolitan",
    "область",
    "край",
    "регион",
    "агломерация",
    "район",
    "республика",
}


def is_location_text(text: str) -> bool:
    lowered = text.lower()
    if "," in text and len(text) <= 60:
        return True
    return len(text) <= 60 and any(keyword in lowered for keyword in LOCATION_KEYWORDS)


def find_phone(lines: list[Line]) -> str:
    for line in lines:
        text = line.text.strip()
        lowered = text.lower()
        if "linkedin" in lowered or "github" in lowered or URL_RE.search(text):
            continue
        match = PHONE_RE.search(text)
        if not match:
            continue
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < 7:
            continue
        return match.group(0)
    return ""


def build_profiles(urls: Iterable[str], lines: list[Line]) -> list[dict]:
    profiles = []
    extra = extract_linkedin_from_lines(lines)
    collected = [url.rstrip(").,") for url in urls]
    if extra:
        collected.append(extra)
    has_full_linkedin = any(
        "linkedin.com/in/" in url.lower() and not url.rstrip("/").endswith("-")
        for url in collected
    )
    seen = set()
    for url in collected:
        clean = url
        lower = clean.lower()
        if "linkedin.com/in/" in lower and has_full_linkedin:
            if clean.rstrip("/").endswith("-"):
                continue
            if lower.endswith("/in") or lower.endswith("/in/"):
                continue
        network = ""
        if "linkedin.com" in lower:
            network = "LinkedIn"
        elif "github.com" in lower:
            network = "GitHub"
        elif "twitter.com" in lower:
            network = "Twitter"
        key = f"{network.lower()}::{clean.rstrip('/').lower()}"
        if key in seen:
            continue
        seen.add(key)
        profiles.append({"network": network or "Website", "url": clean})
    return profiles


def extract_linkedin_from_lines(lines: list[Line]) -> str:
    for line in lines:
        match = re.search(r"(\S+)\s*\(LinkedIn\)", line.text, re.I)
        if match:
            handle = match.group(1).strip()
            if handle and "linkedin.com" not in handle.lower():
                return f"https://www.linkedin.com/in/{handle}"
    return ""


def parse_experience(lines: list[Line]) -> list[dict]:
    texts = [
        line.text.strip()
        for line in lines
        if line.text.strip() and not is_page_header(line.text)
    ]
    entries: list[dict] = []
    header_buffer: list[str] = []
    current_entry: dict | None = None
    content_lines: list[str] = []
    last_company = ""
    i = 0
    while i < len(texts):
        text = texts[i]
        if DATE_RANGE_RE.search(text):
            if current_entry:
                finalize_work_entry(current_entry, content_lines)
                entries.append(current_entry)
            header = clean_header_lines(header_buffer)
            header_buffer = []
            company, position = parse_company_position(header, last_company)
            start_date, end_date = parse_date_range(text)
            current_entry = {
                "name": company,
                "position": position,
                "location": "",
                "startDate": start_date,
                "endDate": end_date,
                "summary": "",
                "highlights": [],
            }
            if company:
                last_company = company
            content_lines = []
            i += 1
            continue
        if is_duration_line(text) and header_buffer:
            header_buffer.append(text)
            i += 1
            continue
        if looks_like_header_start(texts, i):
            header_buffer.append(text)
            i += 1
            continue
        if current_entry:
            content_lines.append(text)
        else:
            header_buffer.append(text)
        i += 1
    if current_entry:
        finalize_work_entry(current_entry, content_lines)
        entries.append(current_entry)
    return [entry for entry in entries if entry.get("name") or entry.get("position")]


def parse_education(lines: list[Line]) -> list[dict]:
    blocks = split_education_blocks(lines)
    entries = []
    for block in blocks:
        entry = parse_education_block(block)
        if entry:
            entries.append(entry)
    return entries


def parse_certifications(lines: list[Line]) -> list[dict]:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts)
    if not texts:
        return []
    entries = []
    current_name = ""
    for text in texts:
        cleaned = cleanup_cert_text(text)
        if not cleaned:
            continue
        if is_cert_continuation_line(cleaned, current_name) and current_name:
            current_name = f"{current_name} {cleaned}".strip()
            continue
        if current_name:
            entries.append({"name": current_name, "issuer": "", "date": ""})
        current_name = cleaned
    if current_name:
        entries.append({"name": current_name, "issuer": "", "date": ""})
    return entries


def parse_projects(lines: list[Line]) -> list[dict]:
    return [entry for entry in parse_blocks(lines, parse_project_block) if entry]


def parse_volunteer(lines: list[Line]) -> list[dict]:
    return [entry for entry in parse_blocks(lines, parse_volunteer_block) if entry]


def parse_blocks(lines: list[Line], parser) -> list[dict]:
    blocks = split_blocks(lines)
    entries = []
    for block in blocks:
        entry = parser(block)
        if entry:
            entries.append(entry)
    return entries


def split_blocks(lines: list[Line]) -> list[list[Line]]:
    if not lines:
        return []
    heights = [line.bottom - line.top for line in lines if line.bottom > line.top]
    gap_threshold = (median(heights) if heights else 10.0) * 1.8
    blocks: list[list[Line]] = []
    current: list[Line] = [lines[0]]
    last_bottom = lines[0].bottom
    for line in lines[1:]:
        if line.top - last_bottom > gap_threshold:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
        last_bottom = line.bottom
    blocks.append(current)
    merged: list[list[Line]] = []
    for block in blocks:
        if merged and is_continuation_block(block):
            merged[-1].extend(block)
        else:
            merged.append(block)
    return merged


def split_experience_blocks(lines: list[Line]) -> list[list[Line]]:
    cleaned = [line for line in lines if not is_page_header(line.text)]
    blocks: list[list[Line]] = []
    current: list[Line] = []
    last_company: Line | None = None
    for idx, line in enumerate(cleaned):
        if is_entry_start(cleaned, idx):
            if current:
                blocks.append(current)
                current = []
            if is_position_only_start(cleaned, idx) and last_company:
                current.append(last_company)
        current.append(line)
        if is_company_line(cleaned, idx):
            last_company = line
    if current:
        blocks.append(current)
    return blocks


def split_education_blocks(lines: list[Line]) -> list[list[Line]]:
    cleaned = [line for line in lines if not is_page_header(line.text)]
    blocks: list[list[Line]] = []
    i = 0
    while i < len(cleaned):
        text = cleaned[i].text.strip()
        if not text:
            i += 1
            continue
        block = [cleaned[i]]
        if i + 1 < len(cleaned):
            next_text = cleaned[i + 1].text.strip()
            if looks_like_degree_line(next_text):
                degree_line = cleaned[i + 1]
                if i + 2 < len(cleaned) and is_trailing_year_line(cleaned[i + 2].text):
                    merged = f"{degree_line.text} {cleaned[i + 2].text}".strip()
                    degree_line = dataclasses.replace(degree_line, text=merged)
                    block.append(degree_line)
                    i += 2
                else:
                    block.append(degree_line)
                    i += 1
        blocks.append(block)
        i += 1
    return blocks


def is_continuation_block(block: list[Line]) -> bool:
    texts = [line.text.strip() for line in block if line.text.strip()]
    if not texts:
        return False
    first = texts[0].lower()
    if first.startswith("achievements"):
        return True
    if first.startswith(("-", "\u2022", "\u2013")):
        return True
    if is_page_header(texts[0]):
        return True
    has_date = any(DATE_RANGE_RE.search(text) for text in texts)
    if not has_date and any(is_duration_line(text) for text in texts):
        return True
    return False


def parse_work_block(lines: list[Line]) -> dict | None:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts, drop_duration=True, drop_employment=True)
    if not texts:
        return None
    date_line = find_date_line(texts)
    start_date, end_date = parse_date_range(date_line) if date_line else ("", "")
    date_index = texts.index(date_line) if date_line in texts else -1
    before_date = texts[:date_index] if date_index >= 0 else texts
    after_date = texts[date_index + 1 :] if date_index >= 0 else []
    before_date = [t for t in before_date if not is_duration_line(t)]
    company = ""
    position = ""
    if len(before_date) >= 2:
        company = before_date[0]
        position = before_date[1]
    elif len(before_date) == 1:
        position = before_date[0]
    content_lines = after_date if after_date else texts[2:]
    location = find_location_from_block(content_lines)
    content_lines = [t for t in content_lines if t != location]
    highlights, summary = split_highlights(content_lines)
    return {
        "name": company,
        "position": position,
        "location": location,
        "startDate": start_date,
        "endDate": end_date,
        "summary": summary,
        "highlights": highlights,
    }


def finalize_work_entry(entry: dict, content_lines: list[str]) -> None:
    location = find_location_from_block(content_lines)
    content_lines = [t for t in content_lines if t != location]
    highlights, summary = split_highlights(content_lines)
    entry["location"] = location
    entry["summary"] = summary
    entry["highlights"] = highlights


def parse_education_block(lines: list[Line]) -> dict | None:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts)
    if not texts:
        return None
    date_line = find_date_line(texts)
    start_date, end_date = parse_date_range(date_line) if date_line else ("", "")
    cleaned = list(texts)
    if date_line and not looks_like_degree_line(date_line):
        cleaned = [t for t in texts if t != date_line]
    institution = cleaned[0] if cleaned else ""
    degree_line = cleaned[1] if len(cleaned) > 1 else ""
    study_type, area = parse_degree(degree_line)
    return {
        "institution": institution,
        "studyType": study_type,
        "area": area,
        "startDate": start_date,
        "endDate": end_date,
    }


def parse_cert_block(lines: list[Line]) -> dict | None:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts)
    if not texts:
        return None
    date_line = find_date_line(texts)
    start_date, end_date = parse_date_range(date_line) if date_line else ("", "")
    cleaned = [t for t in texts if t != date_line]
    name = cleaned[0] if cleaned else ""
    if "Hobbies:" in name:
        name = name.split("Hobbies:")[0].strip()
    issuer = cleaned[1] if len(cleaned) > 1 else ""
    return {
        "name": name,
        "issuer": issuer,
        "date": start_date or end_date,
    }
def cleanup_cert_text(text: str) -> str:
    cleaned = text.strip()
    if "Hobbies:" in cleaned:
        cleaned = cleaned.split("Hobbies:")[0].strip()
    return cleaned


def is_cert_continuation_line(text: str, current_name: str) -> bool:
    lowered = text.lower()
    if lowered.startswith("(") or lowered.startswith("-"):
        return True
    if current_name and "specialization" in lowered:
        return True
    return False


def parse_project_block(lines: list[Line]) -> dict | None:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts)
    if not texts:
        return None
    name = texts[0]
    description = " ".join(texts[1:]).strip()
    return {"name": name, "description": description}


def parse_volunteer_block(lines: list[Line]) -> dict | None:
    texts = [line.text for line in lines if line.text.strip()]
    texts = filter_block_texts(texts, drop_duration=True, drop_employment=True)
    if not texts:
        return None
    date_line = find_date_line(texts)
    start_date, end_date = parse_date_range(date_line) if date_line else ("", "")
    cleaned = [t for t in texts if t != date_line]
    position, organization = split_title_company(cleaned)
    summary = " ".join(cleaned[2:]).strip() if len(cleaned) > 2 else ""
    return {
        "organization": organization,
        "position": position,
        "startDate": start_date,
        "endDate": end_date,
        "summary": summary,
    }


def parse_skills(lines: list[Line]) -> list[dict]:
    text = " ".join(line.text for line in lines).strip()
    if not text:
        return []
    delimiters = r"[\u2022\u00b7,;|]"
    if re.search(delimiters, text):
        parts = re.split(delimiters, text)
        return normalize_skill_parts(parts)
    parts = []
    for line in lines:
        line_text = line.text.strip()
        if not line_text:
            continue
        tokens = line_text.split()
        if len(tokens) >= 3 and all(is_title_token(token) for token in tokens):
            parts.extend(tokens)
        else:
            parts.append(line_text)
    return normalize_skill_parts(parts)


def normalize_skill_parts(parts: list[str]) -> list[dict]:
    seen = set()
    skills = []
    for part in parts:
        name = part.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append({"name": name})
    return skills


def parse_languages(lines: list[Line]) -> list[dict]:
    items = []
    for line in lines:
        text = line.text.strip()
        if not text or is_noise_line(text):
            continue
        match = re.match(r"^(.+?)\s*\(([^)]+)\)$", text)
        if match:
            items.append({"language": match.group(1).strip(), "fluency": match.group(2).strip()})
        else:
            items.append({"language": text})
    return items


def parse_interests(lines: list[Line]) -> list[dict]:
    text = " ".join(line.text for line in lines if not is_noise_line(line.text))
    parts = re.split(r"[•\u2022\u00b7,;|]", text)
    items = []
    for part in parts:
        name = part.strip()
        if name:
            items.append({"name": name})
    return items


def find_date_line(texts: list[str]) -> str:
    for text in texts:
        if DATE_RANGE_RE.search(text) or SINGLE_DATE_RE.search(text):
            return text
    return ""


def parse_date_range(text: str) -> tuple[str, str]:
    if not text:
        return "", ""
    match = DATE_RANGE_RE.search(text)
    if match:
        return normalize_date(match.group("start")), normalize_date(match.group("end"))
    match = SINGLE_DATE_RE.search(text)
    if match:
        return normalize_date(match.group(0)), ""
    return "", ""


def normalize_date(value: str) -> str:
    value = value.strip().lower()
    if value in {"present", "current", "today", "настоящее время", "настоящий момент"}:
        return ""
    parts = value.split()
    if len(parts) == 1:
        year = parts[0]
        return year if year.isdigit() else ""
    month = MONTHS.get(parts[0][:3], 0)
    year = parts[1] if len(parts) > 1 else ""
    if month and year.isdigit():
        return f"{year}-{month:02d}"
    return year if year.isdigit() else ""


def split_title_company(texts: list[str]) -> tuple[str, str]:
    if not texts:
        return "", ""
    first = texts[0]
    if " at " in first.lower():
        parts = re.split(r"\s+at\s+", first, flags=re.I)
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
    position = first
    company = ""
    if len(texts) > 1:
        company = texts[1]
        company = company.split("\u00b7")[0].strip()
    return position, company


def find_location_from_block(texts: list[str]) -> str:
    for text in texts:
        if "," in text and len(text) <= 60 and not DATE_RANGE_RE.search(text):
            return text
        if (
            len(text) <= 20
            and text[:1].isupper()
            and text.isalpha()
            and not contains_role_keyword(text)
        ):
            return text
    return ""


def split_highlights(texts: list[str]) -> tuple[list[str], str]:
    highlights = []
    summary_parts = []
    last_was_highlight = False
    for text in texts:
        stripped = text.strip()
        if stripped.lower() in {"achievements:", "achievements", "main responsibilities:"}:
            continue
        if stripped.startswith(("\u2022", "-", "\u2013")):
            highlights.append(stripped.lstrip("\u2022-\u2013 ").strip())
            last_was_highlight = True
        elif highlights and last_was_highlight:
            highlights[-1] = f"{highlights[-1]} {stripped}".strip()
        else:
            summary_parts.append(stripped)
            last_was_highlight = False
    summary = " ".join(summary_parts).strip()
    return highlights, summary


def parse_degree(line: str) -> tuple[str, str]:
    if not line:
        return "", ""
    line = re.sub(r"\s*\(.*?\d{4}.*?\)", "", line).strip()
    line = line.replace("\u00b7", " ").strip()
    degree_keywords = [
        "bachelor",
        "master",
        "phd",
        "doctor",
        "bsc",
        "msc",
        "mba",
        "ba",
        "ma",
    ]
    study_type = ""
    area = ""
    if "," in line:
        left, right = line.split(",", 1)
        if any(keyword in left.lower() for keyword in degree_keywords):
            study_type = left.strip()
            area = right.strip()
            return study_type or line, area
    for keyword in degree_keywords:
        if keyword in line.lower():
            study_type = line
            break
    if " in " in line.lower():
        parts = re.split(r"\s+in\s+", line, flags=re.I)
        if len(parts) >= 2:
            study_type = parts[0].strip()
            area = parts[1].strip()
    return study_type or line, area


def parse_company_position(header: list[str], last_company: str) -> tuple[str, str]:
    if not header:
        return last_company, ""
    if len(header) >= 2:
        company = header[0]
        position = header[1]
        if " at " in company.lower():
            position, company = split_title_company([company, position])
        return company, position
    return last_company, header[0]


def clean_header_lines(header: list[str]) -> list[str]:
    cleaned = []
    for text in header:
        if not text:
            continue
        if text.lower() in {"achievements:", "main responsibilities:"}:
            continue
        if is_duration_line(text) or is_employment_type_line(text):
            continue
        cleaned.append(text)
    return cleaned


def looks_like_header_start(texts: list[str], idx: int) -> bool:
    text = texts[idx]
    if not text or text.lower() in {"achievements:", "main responsibilities:"}:
        return False
    if text.startswith(("-", "\u2022", "\u2013")):
        return False
    next_text = texts[idx + 1] if idx + 1 < len(texts) else ""
    if is_duration_line(next_text):
        return True
    if (
        next_text
        and contains_role_keyword(next_text)
        and idx + 2 < len(texts)
        and DATE_RANGE_RE.search(texts[idx + 2])
    ):
        return is_company_name_word(text) or is_header_candidate(text)
    if len(text) > 50 or not is_header_candidate(text):
        return False
    for offset in range(1, 4):
        if idx + offset < len(texts) and DATE_RANGE_RE.search(texts[idx + offset]):
            return True
    return False


def is_header_candidate(text: str) -> bool:
    if text.endswith((".", ":")):
        return False
    if contains_role_keyword(text):
        return True
    if any(suffix in text for suffix in (" Oy", " Inc", " LLC", " Ltd", " GmbH", " S.A.")):
        return True
    words = text.split()
    if len(words) >= 2:
        caps = sum(1 for word in words if word[:1].isupper())
        return caps >= max(1, len(words) // 2)
    return False


def is_company_name_word(text: str) -> bool:
    stripped = text.strip()
    if stripped.endswith((".", ":")):
        return False
    parts = stripped.split()
    if len(parts) != 1:
        return False
    return parts[0][:1].isupper()


def is_title_token(token: str) -> bool:
    if token.startswith(".") and len(token) > 1:
        return True
    if token.isupper():
        return True
    return token[:1].isupper()


def contains_role_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(
        keyword in lowered
        for keyword in (
            "developer",
            "engineer",
            "manager",
            "director",
            "lead",
            "architect",
            "consultant",
            "analyst",
            "designer",
            "owner",
            "founder",
            "cto",
            "ceo",
            "vp",
            "head",
            "principal",
        )
    )


def filter_block_texts(
    texts: list[str], drop_duration: bool = False, drop_employment: bool = False
) -> list[str]:
    filtered = []
    for text in texts:
        if is_page_header(text) or is_noise_line(text):
            continue
        if text.strip().lower() in {"achievements:", "achievements"}:
            continue
        if drop_duration and is_duration_line(text):
            continue
        if drop_employment and is_employment_type_line(text):
            continue
        filtered.append(text)
    return filtered


def is_page_header(text: str) -> bool:
    return bool(PAGE_RE.match(text.strip()))


def is_duration_line(text: str) -> bool:
    if re.search(r"\b\d{4}\b", text):
        return False
    return bool(DURATION_RE.search(text))


def is_employment_type_line(text: str) -> bool:
    lowered = text.lower()
    return any(
        term in lowered
        for term in (
            "full-time",
            "part-time",
            "contract",
            "internship",
            "self-employed",
            "freelance",
        )
    )


def is_noise_line(text: str) -> bool:
    lowered = text.strip().lower()
    if lowered.startswith("page ") or PAGE_RE.match(lowered):
        return True
    if lowered == "contact" or lowered.startswith("contact "):
        return True
    return lowered in {"способы связаться", "контакты", "контактная информация"}


def is_entry_start(lines: list[Line], idx: int) -> bool:
    text = lines[idx].text.strip()
    if not text or text.lower() in {"achievements:", "main responsibilities:"}:
        return False
    if text.startswith(("-", "\u2022", "\u2013")):
        return False
    if DATE_RANGE_RE.search(text):
        return False
    if len(text) > 60:
        return False
    next_text = lines[idx + 1].text.strip() if idx + 1 < len(lines) else ""
    if is_duration_line(next_text):
        return True
    if DATE_RANGE_RE.search(next_text):
        prev_text = lines[idx - 1].text.strip() if idx > 0 else ""
        if not is_duration_line(prev_text):
            return True
    if idx + 2 < len(lines) and DATE_RANGE_RE.search(lines[idx + 2].text):
        middle_text = lines[idx + 1].text.strip()
        if not is_duration_line(middle_text) and not DATE_RANGE_RE.search(middle_text):
            return True
    return False


def is_position_only_start(lines: list[Line], idx: int) -> bool:
    text = lines[idx].text.strip()
    if DATE_RANGE_RE.search(text):
        return False
    next_text = lines[idx + 1].text.strip() if idx + 1 < len(lines) else ""
    prev_text = lines[idx - 1].text.strip() if idx > 0 else ""
    return bool(DATE_RANGE_RE.search(next_text)) and not is_duration_line(prev_text)


def is_company_line(lines: list[Line], idx: int) -> bool:
    next_text = lines[idx + 1].text.strip() if idx + 1 < len(lines) else ""
    return is_duration_line(next_text)


def looks_like_degree_line(text: str) -> bool:
    if DATE_RANGE_RE.search(text):
        return True
    if re.search(r"\(\d{4}", text):
        return True
    return any(keyword in text.lower() for keyword in ("degree", "bachelor", "master", "phd"))


def is_trailing_year_line(text: str) -> bool:
    return bool(re.match(r"^\d{4}\)?$", text.strip()))
