from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .schemas import ResumeItem, ResumeSectionPayload

SECTION_ORDER = [
    ("summary", {"summary", "professional summary", "profile", "about"}),
    ("skills", {"skills", "technical skills", "core skills"}),
    ("experience", {"experience", "work experience", "employment", "professional experience"}),
    ("projects", {"projects", "project experience"}),
    ("education", {"education", "academic background"}),
    ("certifications", {"certifications", "licenses", "certificates"}),
]

HEADING_LOOKUP = {
    alias: section_type for section_type, aliases in SECTION_ORDER for alias in aliases
}


@dataclass(frozen=True)
class ParsedResume:
    raw_text: str
    sections: list[ResumeSectionPayload]


class ResumeParseError(ValueError):
    pass


def _normalize_heading(line: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", line.strip().lower())


def _clean_text_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return [line for line in lines if line]


def extract_text_from_upload(file_name: str, mime_type: str, data: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    normalized_mime = (mime_type or "").lower()

    if suffix == ".docx" or normalized_mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return _extract_docx_text(data)
    if suffix == ".pdf" or normalized_mime == "application/pdf":
        return _extract_pdf_text(data)

    raise ResumeParseError("Unsupported resume file type. Only PDF and DOCX are supported.")


def _extract_docx_text(data: bytes) -> str:
    try:
        document = Document(BytesIO(data))
    except Exception as exc:  # pragma: no cover - library specific failure path
        raise ResumeParseError("Unable to read DOCX file.") from exc

    paragraphs = [
        paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()
    ]
    if not paragraphs:
        raise ResumeParseError("The DOCX file does not contain readable text.")
    return "\n".join(paragraphs)


def _extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:  # pragma: no cover - library specific failure path
        raise ResumeParseError("Unable to read PDF file.") from exc

    pages_text = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            pages_text.append(text)

    combined = "\n".join(pages_text).strip()
    if not combined:
        raise ResumeParseError("The PDF file does not contain readable text.")
    return combined


def _split_claims(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    if "\n" in stripped:
        parts = [line.strip(" -*•\t") for line in stripped.split("\n") if line.strip(" -*•\t")]
        if len(parts) > 1:
            return parts
        stripped = parts[0] if parts else stripped

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", stripped) if part.strip()]
    if len(sentences) > 1:
        return sentences

    return [stripped]


def _is_heading(line: str) -> bool:
    normalized = _normalize_heading(line)
    return normalized in HEADING_LOOKUP or normalized in {
        section_type for section_type, _ in SECTION_ORDER
    }


def _detect_section_type(heading: str) -> str:
    normalized = _normalize_heading(heading)
    return HEADING_LOOKUP.get(normalized, normalized)


def _flush_section(
    sections: list[ResumeSectionPayload],
    section_type: str | None,
    heading: str | None,
    body_lines: list[str],
    start_line_number: int,
) -> None:
    if section_type is None or heading is None:
        return

    body_text = "\n".join(body_lines).strip()
    items: list[ResumeItem] = []
    if body_text:
        for index, claim in enumerate(_split_claims(body_text), start=1):
            items.append(
                ResumeItem(
                    text=claim,
                    evidence_id=f"{section_type}:{start_line_number}:{index}",
                )
            )

    sections.append(ResumeSectionPayload(section_type=section_type, heading=heading, items=items))


def parse_resume_text(text: str) -> ParsedResume:
    lines = _clean_text_lines(text)
    if not lines:
        raise ResumeParseError("The uploaded resume does not contain readable content.")

    sections: list[ResumeSectionPayload] = []
    current_section_type: str | None = None
    current_heading: str | None = None
    current_body: list[str] = []
    current_start_line = 1
    freeform_lines: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        if _is_heading(line):
            _flush_section(
                sections,
                current_section_type,
                current_heading,
                current_body,
                current_start_line,
            )
            current_section_type = _detect_section_type(line)
            current_heading = line
            current_body = []
            current_start_line = line_number
            continue

        if current_section_type is None:
            freeform_lines.append(line)
        else:
            current_body.append(line)

    _flush_section(
        sections, current_section_type, current_heading, current_body, current_start_line
    )

    if not sections and freeform_lines:
        sections.append(
            ResumeSectionPayload(
                section_type="summary",
                heading="Summary",
                items=[
                    ResumeItem(text=claim, evidence_id=f"summary:1:{index}")
                    for index, claim in enumerate(_split_claims("\n".join(freeform_lines)), start=1)
                ],
            )
        )

    if not sections:
        raise ResumeParseError("No recognizable resume sections were found.")

    return ParsedResume(raw_text="\n".join(lines), sections=sections)
