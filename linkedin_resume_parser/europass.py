from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

NS_DEFAULT = "http://www.europass.eu/1.0"
NS_OA = "http://www.openapplications.org/oagis/9"
NS_HR = "http://www.hr-xml.org/3"
NS_EURES = "http://www.europass_eures.eu/1.0"
NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"


def export_europass(
    resume_path: Path, metadata_path: Path, config_path: Path, output_path: Path
) -> None:
    resume = load_json(resume_path)
    metadata = load_json(metadata_path)
    config = load_json_optional(config_path)

    ET.register_namespace("", NS_DEFAULT)
    ET.register_namespace("oa", NS_OA)
    ET.register_namespace("eures", NS_EURES)
    ET.register_namespace("hr", NS_HR)
    ET.register_namespace("xsi", NS_XSI)

    root = ET.Element(
        q(NS_DEFAULT, "Candidate"),
        {
            q(NS_XSI, "schemaLocation"): "http://www.europass.eu/1.0 Candidate.xsd",
        },
    )

    add_document_id(root, config)
    add_candidate_supplier(root, resume, config)
    add_candidate_person(root, resume, metadata, config)
    add_candidate_profile(root, resume, metadata, config)
    add_rendering_information(root, config)

    ET.indent(root, space="    ")
    xml_body = ET.tostring(root, encoding="utf-8").decode("utf-8")
    xml_text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
    xml_text += xml_body.replace(" />", "/>")
    output_path.write_text(xml_text, encoding="utf-8")


def add_document_id(parent: ET.Element, config: dict) -> None:
    attrs = {
        "schemeID": config.get("document_scheme_id", "Test-0001"),
        "schemeName": config.get("document_scheme_name", "DocumentIdentifier"),
        "schemeAgencyName": config.get("document_scheme_agency", "EUROPASS"),
        "schemeVersionID": config.get("document_scheme_version", "4.0"),
    }
    ET.SubElement(parent, q(NS_HR, "DocumentID"), attrs)


def add_candidate_supplier(parent: ET.Element, resume: dict, config: dict) -> None:
    supplier = ET.SubElement(parent, q(NS_DEFAULT, "CandidateSupplier"))
    attrs = {
        "schemeID": config.get("party_scheme_id", "Test-0001"),
        "schemeName": config.get("party_scheme_name", "PartyID"),
        "schemeAgencyName": config.get("party_scheme_agency", "EUROPASS"),
        "schemeVersionID": config.get("party_scheme_version", "1.0"),
    }
    ET.SubElement(supplier, q(NS_HR, "PartyID"), attrs)
    add_text(supplier, NS_HR, "PartyName", config.get("party_name", "Owner"))
    person_contact = ET.SubElement(supplier, q(NS_DEFAULT, "PersonContact"))
    add_person_name(person_contact, resume.get("basics", {}).get("name", ""))
    add_text(supplier, NS_HR, "PrecedenceCode", config.get("precedence_code", "1"))


def add_candidate_person(
    parent: ET.Element, resume: dict, metadata: dict, config: dict
) -> None:
    person = ET.SubElement(parent, q(NS_DEFAULT, "CandidatePerson"))
    add_person_name(person, resume.get("basics", {}).get("name", ""))
    add_person_address(person, metadata, config)
    nationality_code = metadata.get("nationality_code", "")
    if nationality_code:
        add_text(person, NS_DEFAULT, "NationalityCode", nationality_code.lower())
    birth_date = metadata.get("birth_date", "")
    if birth_date:
        add_text(person, NS_HR, "BirthDate", birth_date)
    gender = metadata.get("gender", "")
    if gender:
        add_text(person, NS_DEFAULT, "GenderCode", gender)


def add_candidate_profile(
    parent: ET.Element, resume: dict, metadata: dict, config: dict
) -> None:
    profile = ET.SubElement(
        parent,
        q(NS_DEFAULT, "CandidateProfile"),
        {"languageCode": metadata.get("language_code", "en")},
    )
    attrs = {
        "schemeID": config.get("profile_scheme_id", "Test-0001"),
        "schemeName": config.get("profile_scheme_name", "CandidateProfileID"),
        "schemeAgencyName": config.get("profile_scheme_agency", "EUROPASS"),
        "schemeVersionID": config.get("profile_scheme_version", "1.0"),
    }
    profile_id = config.get("candidate_profile_id") or uuid.uuid4().hex
    add_text(profile, NS_HR, "ID", profile_id, attrs)

    add_employment_history(profile, resume, metadata, config)
    add_education_history(profile, resume, metadata)

    ET.SubElement(profile, q(NS_EURES, "Licenses"))
    add_certifications(profile, resume)
    ET.SubElement(profile, q(NS_DEFAULT, "PublicationHistory"))
    ET.SubElement(profile, q(NS_DEFAULT, "PersonQualifications"))
    ET.SubElement(profile, q(NS_DEFAULT, "EmploymentReferences"))
    ET.SubElement(profile, q(NS_DEFAULT, "CreativeWorks"))
    ET.SubElement(profile, q(NS_DEFAULT, "Projects"))
    ET.SubElement(profile, q(NS_DEFAULT, "SocialAndPoliticalActivities"))
    add_skills(profile, resume)
    ET.SubElement(profile, q(NS_DEFAULT, "NetworksAndMemberships"))
    ET.SubElement(profile, q(NS_DEFAULT, "ConferencesAndSeminars"))
    ET.SubElement(profile, q(NS_DEFAULT, "VoluntaryWorks"))
    ET.SubElement(profile, q(NS_DEFAULT, "CourseCertifications"))


def add_employment_history(
    parent: ET.Element, resume: dict, metadata: dict, config: dict
) -> None:
    work = resume.get("work", [])
    if not work:
        return
    history = ET.SubElement(parent, q(NS_DEFAULT, "EmploymentHistory"))
    for entry in work:
        employer_history = ET.SubElement(history, q(NS_DEFAULT, "EmployerHistory"))
        add_text(
            employer_history,
            NS_HR,
            "OrganizationName",
            entry.get("name", ""),
        )
        add_organization_contact(employer_history, entry.get("location", ""), metadata)
        position_history = ET.SubElement(employer_history, q(NS_DEFAULT, "PositionHistory"))
        add_position_title(position_history, entry.get("position", ""), config)
        add_employment_period(position_history, entry.get("startDate"), entry.get("endDate"))
        description_text = build_description(entry)
        if description_text:
            add_text(position_history, NS_OA, "Description", description_text)
        city = extract_city(entry.get("location", "")) or metadata.get("municipality", "")
        if city:
            add_text(position_history, NS_DEFAULT, "City", city)
        country_code = metadata.get("country_code", "")
        if country_code:
            add_text(position_history, NS_DEFAULT, "Country", country_code.lower())


def add_education_history(parent: ET.Element, resume: dict, metadata: dict) -> None:
    education = resume.get("education", [])
    if not education:
        return
    history = ET.SubElement(parent, q(NS_DEFAULT, "EducationHistory"))
    for entry in education:
        attendance = ET.SubElement(history, q(NS_DEFAULT, "EducationOrganizationAttendance"))
        add_text(
            attendance,
            NS_HR,
            "OrganizationName",
            entry.get("institution", ""),
        )
        add_organization_contact(attendance, metadata.get("municipality", ""), metadata)
        level_code = map_education_level(entry)
        if level_code:
            add_text(attendance, NS_DEFAULT, "EducationLevelCode", level_code)
        add_attendance_period(attendance, entry.get("startDate"), entry.get("endDate"))
        degree = ET.SubElement(attendance, q(NS_DEFAULT, "EducationDegree"))
        degree_name = build_degree_name(entry)
        add_text(degree, NS_HR, "DegreeName", degree_name)
        area = entry.get("area", "")
        if area:
            add_text(degree, NS_DEFAULT, "OccupationalSkillsCovered", f"<p>{area}</p>")


def add_rendering_information(parent: ET.Element, config: dict) -> None:
    rendering = ET.SubElement(parent, q(NS_DEFAULT, "RenderingInformation"))
    design = ET.SubElement(rendering, q(NS_DEFAULT, "Design"))
    add_text(design, NS_DEFAULT, "Template", config.get("template", "Template1"))
    add_text(design, NS_DEFAULT, "Color", config.get("color", "Default"))
    add_text(design, NS_DEFAULT, "FontSize", config.get("font_size", "Medium"))
    add_text(design, NS_DEFAULT, "Logo", config.get("logo", "FirstPage"))
    add_text(design, NS_DEFAULT, "PageNumbers", str(bool(config.get("page_numbers", False))).lower())
    sections = config.get("sections_order", [])
    if sections:
        order = ET.SubElement(design, q(NS_DEFAULT, "SectionsOrder"))
        for section_title in sections:
            section = ET.SubElement(order, q(NS_DEFAULT, "Section"))
            add_text(section, NS_DEFAULT, "Title", section_title)


def add_person_name(parent: ET.Element, full_name: str) -> None:
    first, last = split_name(full_name)
    name = ET.SubElement(parent, q(NS_DEFAULT, "PersonName"))
    add_text(name, NS_OA, "GivenName", first)
    add_text(name, NS_HR, "FamilyName", last)


def add_person_address(parent: ET.Element, metadata: dict, config: dict) -> None:
    country_code = metadata.get("country_code", "")
    municipality = metadata.get("municipality", "")
    phone = (metadata.get("phone") or "").strip()
    if not (country_code or municipality or phone):
        return
    comm = ET.SubElement(parent, q(NS_DEFAULT, "Communication"))
    add_text(comm, NS_DEFAULT, "UseCode", config.get("address_use", "home"))
    if country_code or municipality:
        address = ET.SubElement(
            comm, q(NS_DEFAULT, "Address"), {"type": config.get("address_type", "home")}
        )
        if country_code:
            add_text(address, NS_DEFAULT, "CountryCode", country_code.lower())
        if municipality:
            add_text(address, NS_OA, "CityName", municipality)
    if phone:
        add_phone_contact(comm, phone)


def add_phone_contact(parent: ET.Element, phone: str) -> None:
    telephone_list = ET.SubElement(parent, q(NS_DEFAULT, "TelephoneList"))
    telephone = ET.SubElement(telephone_list, q(NS_DEFAULT, "Telephone"))
    add_text(telephone, NS_DEFAULT, "Contact", phone)
    use = ET.SubElement(telephone, q(NS_DEFAULT, "Use"))
    add_text(use, NS_DEFAULT, "Code", "mobile")


def add_organization_contact(parent: ET.Element, location: str, metadata: dict) -> None:
    city = extract_city(location) or metadata.get("municipality", "")
    country_code = metadata.get("country_code", "")
    if not city and not country_code:
        return
    contact = ET.SubElement(parent, q(NS_DEFAULT, "OrganizationContact"))
    comm = ET.SubElement(contact, q(NS_DEFAULT, "Communication"))
    address = ET.SubElement(comm, q(NS_DEFAULT, "Address"))
    if city:
        add_text(address, NS_OA, "CityName", city)
    if country_code:
        add_text(address, NS_DEFAULT, "CountryCode", country_code.lower())


def add_position_title(parent: ET.Element, title: str, config: dict) -> None:
    attrs = {}
    uri = config.get("position_uri", "")
    if uri:
        attrs["typeCode"] = "URI"
        attrs["languageID"] = uri
    add_text(parent, NS_DEFAULT, "PositionTitle", title, attrs)


def add_employment_period(parent: ET.Element, start_date: str, end_date: str) -> None:
    period = ET.SubElement(parent, q(NS_EURES, "EmploymentPeriod"))
    if start_date:
        start = ET.SubElement(period, q(NS_EURES, "StartDate"))
        add_text(start, NS_HR, "FormattedDateTime", normalize_date(start_date))
    if end_date:
        end = ET.SubElement(period, q(NS_EURES, "EndDate"))
        add_text(end, NS_HR, "FormattedDateTime", normalize_date(end_date))
        add_text(period, NS_HR, "CurrentIndicator", "false")
    else:
        add_text(period, NS_HR, "CurrentIndicator", "true")


def add_attendance_period(parent: ET.Element, start_date: str, end_date: str) -> None:
    period = ET.SubElement(parent, q(NS_DEFAULT, "AttendancePeriod"))
    if start_date:
        start = ET.SubElement(period, q(NS_DEFAULT, "StartDate"))
        add_text(start, NS_HR, "FormattedDateTime", normalize_date(start_date))
    if end_date:
        end = ET.SubElement(period, q(NS_DEFAULT, "EndDate"))
        add_text(end, NS_HR, "FormattedDateTime", normalize_date(end_date))
        add_text(period, NS_DEFAULT, "Ongoing", "false")
    else:
        add_text(period, NS_DEFAULT, "Ongoing", "true")


def build_description(entry: dict) -> str:
    summary = entry.get("summary", "")
    highlights = entry.get("highlights") or []
    parts = []
    if summary:
        parts.append(f"<p>{summary}</p>")
    if highlights:
        items = "".join(f"<li>{item}</li>" for item in highlights if item)
        if items:
            parts.append(f"<ul>{items}</ul>")
    if not parts:
        return ""
    return "".join(parts)


def build_degree_name(entry: dict) -> str:
    study_type = entry.get("studyType", "")
    area = entry.get("area", "")
    if study_type and area:
        return f"{study_type} - {area}"
    return study_type or area or "Education"


def normalize_date(value: str) -> str:
    parts = value.split("-")
    year = parts[0]
    month = parts[1] if len(parts) > 1 else "01"
    day = parts[2] if len(parts) > 2 else "01"
    return f"{year}-{month}-{day}"


def extract_city(location: str) -> str:
    if "," in location:
        return location.split(",", 1)[0].strip()
    return location.strip()


def split_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def map_education_level(entry: dict) -> str:
    study_type = (entry.get("studyType") or "").lower()
    if "master" in study_type:
        return "7"
    if "bachelor" in study_type:
        return "6"
    if "cert" in study_type:
        return "3"
    if study_type:
        return "3"
    return ""


def add_text(
    parent: ET.Element, ns: str, tag: str, value: str, attrs: dict | None = None
) -> None:
    element = ET.SubElement(parent, q(ns, tag), attrs or {})
    if value:
        element.text = value


def q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def add_skills(parent: ET.Element, resume: dict) -> None:
    skills = resume.get("skills", [])
    if not skills:
        return
    skills_element = ET.SubElement(parent, q(NS_DEFAULT, "Skills"))
    for entry in skills:
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        taxonomy_id = (
            entry.get("taxonomyId")
            or entry.get("taxonomy")
            or entry.get("taxonomy_id")
            or ""
        ).strip()
        competency_id = (
            entry.get("competencyId")
            or entry.get("competency_id")
            or entry.get("id")
            or entry.get("uri")
            or ""
        ).strip()
        if not taxonomy_id and competency_id and "data.europa.eu/esco" in competency_id:
            taxonomy_id = "ESCO_Skill"
        taxonomy_id = taxonomy_id or "Digital_Skill"

        competency = ET.SubElement(skills_element, q(NS_DEFAULT, "PersonCompetency"))
        if competency_id:
            add_text(competency, NS_DEFAULT, "CompetencyID", competency_id)
        add_text(competency, NS_HR, "TaxonomyID", taxonomy_id)
        add_text(competency, NS_HR, "CompetencyName", name)


def add_certifications(parent: ET.Element, resume: dict) -> None:
    certifications = resume.get("certificates", [])
    certs_element = ET.SubElement(parent, q(NS_DEFAULT, "Certifications"))
    for entry in certifications:
        name = (entry.get("name") or "").strip()
        issuer = (entry.get("issuer") or "").strip()
        date = (entry.get("date") or "").strip()
        if not (name or issuer or date):
            continue
        cert = ET.SubElement(certs_element, q(NS_DEFAULT, "Certification"))
        if name:
            add_text(cert, NS_DEFAULT, "CertificationName", name)
        if issuer:
            add_text(cert, NS_DEFAULT, "IssuerName", issuer)
        if date:
            add_text(cert, NS_DEFAULT, "CertificationDate", normalize_date(date))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_optional(path: Path) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return load_json(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export JSON Resume to Europass Candidate XML."
    )
    parser.add_argument(
        "resume",
        type=Path,
        nargs="?",
        default=Path("resume.json"),
        help="Path to resume.json",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        type=Path,
        default=Path("personal_info.json"),
        help="Path to personal info JSON",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("europass_config.json"),
        help="Path to Europass technical configuration JSON",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("europass.xml"),
        help="Output Europass XML path",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    export_europass(args.resume, args.metadata, args.config, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
