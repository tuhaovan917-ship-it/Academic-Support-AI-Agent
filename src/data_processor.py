from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from langchain_core.documents import Document
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

MIN_CHUNK_CHARS = 80
MAX_CHUNK_CHARS = 2600
OVERLAP_CHARS = 220

CATEGORY_FALLBACK_KEYWORDS = {
    "chuan_ngoai_ngu": [
        "chuẩn đầu ra ngoại ngữ",
        "chuẩn ngoại ngữ",
        "ngoại ngữ thứ nhất",
        "ngoại ngữ thứ hai",
        "miễn học ngoại ngữ",
        "miễn thi ngoại ngữ",
    ],
    "chuan_cntt": [
        "chuẩn kỹ năng sử dụng công nghệ thông tin",
        "chuẩn công nghệ thông tin",
        "chứng chỉ ứng dụng công nghệ thông tin",
        "kỹ năng sử dụng công nghệ thông tin",
        "tin học",
        "cntt",
    ],
    "cong_tac_sinh_vien": [
        "quy chế công tác sinh viên",
        "công tác sinh viên",
        "khen thưởng sinh viên",
        "kỷ luật sinh viên",
        "quyền của sinh viên",
        "nghĩa vụ của sinh viên",
    ],
    "diem_ren_luyen": [
        "điểm rèn luyện",
        "rèn luyện sinh viên",
        "đánh giá điểm rèn luyện",
        "xếp loại rèn luyện",
        "tiêu chí rèn luyện",
    ],
    "quy_che_dao_tao": [
        "quy chế đào tạo",
        "tín chỉ",
        "thời gian đào tạo",
        "chuẩn đầu ra",
        "chương trình đào tạo",
    ],
    "hoc_phi_hoc_bong": [
        "học phí",
        "học bổng",
        "miễn giảm",
        "khuyến khích học tập",
        "vay ưu đãi",
        "tài chính",
    ],
    "dang_ky_mon_hoc": [
        "đăng ký môn học",
        "đăng ký học phần",
        "rút môn",
        "học lại",
        "thời khóa biểu",
    ],
    "thu_tuc_hanh_chinh": [
        "thủ tục",
        "giấy xác nhận",
        "thẻ sinh viên",
        "chỉnh sửa thông tin",
        "một cửa",
        "bảng điểm",
    ],
    "hoc_vu": [
        "cảnh báo học tập",
        "cảnh cáo học vụ",
        "xử lý kết quả",
        "hoãn thi",
        "phúc khảo",
        "bảo lưu",
    ],
    "tot_nghiep": [
        "tốt nghiệp",
        "xét tốt nghiệp",
        "cấp bằng",
        "chuẩn tốt nghiệp",
        "khóa luận",
    ],
    "y_te_bao_hiem": [
        "bảo hiểm y tế",
        "bảo hiểm tai nạn",
        "khám sức khỏe",
        "y tế học đường",
    ],
    "ngoai_tru_noi_tru": [
        "ký túc xá",
        "nội trú",
        "ngoại trú",
        "lưu trú",
        "chỗ ở",
    ],
    "ngoai_khoa_doan_hoi": [
        "đoàn",
        "hội sinh viên",
        "câu lạc bộ",
        "ngoại khóa",
        "kỹ năng mềm",
        "hoạt động phong trào",
    ],
    "nghien_cuu_khoa_hoc": [
        "nghiên cứu khoa học",
        "nckh",
        "đề tài nghiên cứu",
        "sáng tạo",
    ],
}

STOPWORDS = {
    "sinh",
    "viên",
    "trường",
    "được",
    "không",
    "trong",
    "của",
    "cho",
    "với",
    "các",
    "theo",
    "này",
    "khi",
    "bao",
    "nhiêu",
}


@dataclass
class Heading:
    level: str
    text: str


def list_pdf_paths(data_dir: str | Path = DATA_DIR) -> list[Path]:
    return sorted(Path(data_dir).glob("*.pdf"))


def list_knowledge_source_paths(data_dir: str | Path = DATA_DIR) -> list[Path]:
    """List source files for indexing.

    For folders like data/raw/HUIT, PDFs are the primary sources. If a PDF has a
    sibling *_extracted.txt file, that text file is used as cache later. Standalone
    .txt files are also included, but extracted text caches are not indexed twice.
    """
    data_dir = Path(data_dir)
    pdf_paths = sorted(data_dir.glob("*.pdf"))
    standalone_text_paths = sorted(
        path
        for path in data_dir.glob("*.txt")
        if not path.stem.endswith("_extracted")
    )
    return [*pdf_paths, *standalone_text_paths]


def get_school_from_source_path(source_path: str | Path) -> str:
    source_path = Path(source_path)
    name = source_path.name.casefold()
    parent_name = source_path.parent.name.casefold()

    if "huit" in name or parent_name == "huit":
        return "HUIT"
    if "công thương" in name or "cong thuong" in name:
        return "HUIT"
    if "hcmut" in name or "bách khoa" in name or "bach khoa" in name:
        return "HCMUT"
    if "nttu" in name or "nguyễn tất thành" in name or "nguyen tat thanh" in name:
        return "NTTU"
    return "UNKNOWN"


def get_school_from_pdf_name(pdf_path: str | Path) -> str:
    return get_school_from_source_path(pdf_path)


def get_faq_path_for_school(school: str) -> Path | None:
    school = school.lower()
    candidates = [
        RAW_DIR / school.upper() / f"faq_{school}.jsonl",
        RAW_DIR / school / f"faq_{school}.jsonl",
        DATA_DIR / f"faq_{school}.jsonl",
    ]
    return next((path for path in candidates if path.exists()), None)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _clean_line(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text.strip()


def _extract_keywords(text: str) -> set[str]:
    words = set(re.findall(r"[\wÀ-ỹ]+", _normalize_text(text), flags=re.UNICODE))
    return {word for word in words if len(word) >= 4 and word not in STOPWORDS}


@lru_cache(maxsize=16)
def _category_keywords_from_faq(faq_path_text: str | None) -> dict[str, set[str]]:
    keywords = {
        category: {_normalize_text(keyword) for keyword in category_keywords}
        for category, category_keywords in CATEGORY_FALLBACK_KEYWORDS.items()
    }
    if not faq_path_text:
        return keywords

    faq_path = Path(faq_path_text)
    if not faq_path.exists():
        return keywords

    with faq_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            category = item.get("category", "khac")
            content = f"{item.get('question', '')} {item.get('answer', '')}"
            keywords.setdefault(category, set()).update(_extract_keywords(content))

    return keywords


def map_category(chunk_text: str, faq_path: str | Path | None = None) -> str:
    normalized_text = _normalize_text(chunk_text)

    if "ngoại ngữ" in normalized_text and ("chuẩn" in normalized_text or "miễn học" in normalized_text):
        return "chuan_ngoai_ngu"
    if (
        "công nghệ thông tin" in normalized_text or "cntt" in normalized_text or "tin học" in normalized_text
    ) and ("chuẩn" in normalized_text or "chứng chỉ" in normalized_text or "kỹ năng" in normalized_text):
        return "chuan_cntt"
    if "công tác sinh viên" in normalized_text or "quy chế công tác sinh viên" in normalized_text:
        return "cong_tac_sinh_vien"
    if "điểm rèn luyện" in normalized_text or "rèn luyện sinh viên" in normalized_text:
        return "diem_ren_luyen"

    category_keywords = _category_keywords_from_faq(str(faq_path) if faq_path else None)
    scores: dict[str, int] = {}
    for category, keywords in category_keywords.items():
        score = sum(1 for keyword in keywords if keyword and keyword in normalized_text)
        if score:
            scores[category] = score

    return max(scores, key=scores.get) if scores else "khac"


def _html_table_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[list[str]] = []
    for tr in soup.find_all("tr"):
        cells = [
            re.sub(r"\s+", " ", cell.get_text(" ", strip=True))
            for cell in tr.find_all(["th", "td"])
        ]
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    max_columns = max(len(row) for row in rows)
    rows = [row + [""] * (max_columns - len(row)) for row in rows]
    markdown_rows = [
        "| " + " | ".join(rows[0]) + " |",
        "| " + " | ".join(["---"] * max_columns) + " |",
    ]
    markdown_rows.extend("| " + " | ".join(row) + " |" for row in rows[1:])
    return "\n".join(markdown_rows)


def _element_to_text(element: object) -> str:
    text = _clean_line(str(element))
    if not text:
        return ""

    category = getattr(element, "category", "")
    metadata = getattr(element, "metadata", None)
    table_html = getattr(metadata, "text_as_html", None) if metadata else None
    if category == "Table" and table_html:
        return _html_table_to_markdown(table_html) or text

    return text


def _pdf_to_text_with_pypdf(pdf_path: Path, text_path: Path) -> Path:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages = []
    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"--- PAGE {page_index} ---\n{page_text.strip()}")

    text_path.write_text("\n\n".join(pages), encoding="utf-8")
    return text_path


def pdf_to_text(
    pdf_path: str | Path,
    output_dir: str | Path = PROCESSED_DIR,
    force: bool = False,
) -> Path:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / f"{pdf_path.stem}.txt"

    if text_path.exists() and not force:
        return text_path

    try:
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(
            filename=str(pdf_path),
            strategy="hi_res",
            infer_table_structure=True,
            languages=["vie"],
        )
        blocks = [_element_to_text(element) for element in elements]
        text_path.write_text("\n\n".join(block for block in blocks if block), encoding="utf-8")
        return text_path
    except ModuleNotFoundError:
        return _pdf_to_text_with_pypdf(pdf_path, text_path)


def source_to_text_path(
    source_path: str | Path,
    output_dir: str | Path = PROCESSED_DIR,
    force_pdf_extract: bool = False,
) -> Path:
    source_path = Path(source_path)
    if source_path.suffix.casefold() == ".txt":
        return source_path

    if source_path.suffix.casefold() != ".pdf":
        raise ValueError(f"Không hỗ trợ định dạng nguồn: {source_path}")

    extracted_text_path = source_path.with_name(f"{source_path.stem}_extracted.txt")
    if (
        extracted_text_path.exists()
        and not force_pdf_extract
        and len("".join(extracted_text_path.read_text(encoding="utf-8").split())) >= MIN_CHUNK_CHARS
    ):
        return extracted_text_path

    school = get_school_from_source_path(source_path)
    school_output_dir = Path(output_dir) / school.lower()
    return pdf_to_text(source_path, output_dir=school_output_dir, force=force_pdf_extract)


def _is_toc_line(line: str) -> bool:
    normalized = _normalize_text(line)
    if normalized in {"mục lục", "nội dung"}:
        return True
    if "mục lục" in normalized and len(normalized) < 80:
        return True
    if re.search(r"\.{4,}\s*\d+\s*$", line):
        return True
    if line.startswith("|") and re.search(r"\.{3,}", line):
        return True
    if line.startswith("|") and re.search(r"\|\s*\d{1,3}\s*\|?\s*$", line):
        toc_keywords = [
            "thông tin",
            "học bổng",
            "học phí",
            "phần",
            "quy trình",
            "hướng dẫn",
            "các ",
            "đăng ký",
        ]
        if any(keyword in normalized for keyword in toc_keywords):
            return True
    return False


def _is_toc_chunk(text: str) -> bool:
    normalized = _normalize_text(text)
    pipe_count = text.count("|")
    toc_terms = [
        "thông tin về",
        "mục lục",
        "phần 3:",
        "phần 4:",
        "học bổng khuyến khích",
        "quy trình giao tiếp",
        "các thông tin về",
    ]
    return pipe_count >= 12 and sum(term in normalized for term in toc_terms) >= 2


def _is_footer_or_noise(line: str) -> bool:
    normalized = _normalize_text(line)
    if not normalized:
        return True
    if re.fullmatch(r"\d{1,3}", normalized):
        return True
    if re.fullmatch(r"trang\s+\d{1,3}", normalized):
        return True
    if "sổ tay sinh viên" in normalized and "trang" in normalized and len(normalized) < 120:
        return True
    if len(line) <= 2:
        return True
    return False


def _is_probably_heading_text(line: str) -> bool:
    if len(line) > 180:
        return False
    if line.startswith("|") or "http" in line.casefold():
        return False
    if re.search(r"\.{4,}", line):
        return False
    return True


def detect_heading(line: str, school: str) -> Heading | None:
    line = _clean_line(line)
    normalized = _normalize_text(line)
    if not _is_probably_heading_text(line):
        return None
    if normalized.startswith("điều kiện"):
        return None

    if re.match(r"^phần\s+\d+\b", normalized):
        return Heading("part", line)
    if re.match(r"^chương\s+[ivxlcdm\d]+\b", normalized):
        return Heading("chapter", line)
    if re.match(r"^mục\s+\d+\b", normalized):
        return Heading("section", line)
    if re.match(r"^điều\s+\d+\b", normalized):
        return Heading("article", line)
    if re.match(r"^\d+\.\d+(\.\d+)*\b", normalized):
        return Heading("numbered", line)

    special_headings = [
        "đánh giá điểm rèn luyện sinh viên",
        "thông tin về điểm rèn luyện",
        "công tác sinh viên",
        "công tác đào tạo",
        "quy chế đào tạo",
        "đăng ký học phần",
        "kết quả học tập",
        "tạm dừng học tập",
        "chuyển ngành",
        "cảnh báo học vụ",
        "buộc thôi học",
        "chuẩn đầu ra",
        "học phí",
        "học bổng",
        "bảo hiểm y tế",
        "nghiên cứu khoa học",
        "xét tốt nghiệp",
    ]
    if any(keyword in normalized for keyword in special_headings):
        return Heading("topic", line)

    uppercase_letters = re.findall(r"[A-ZÀ-ỸĐ]", line)
    letters = re.findall(r"[A-Za-zÀ-ỹĐđ]", line)
    if (
        school in {"HCMUT", "HUIT"}
        and letters
        and len(line) <= 90
        and len(uppercase_letters) / max(len(letters), 1) > 0.75
    ):
        return Heading("topic", line)

    return None


def _heading_rank(level: str) -> int:
    return {
        "part": 1,
        "chapter": 2,
        "section": 3,
        "topic": 4,
        "article": 5,
        "numbered": 5,
    }.get(level, 5)


def _update_hierarchy(hierarchy: list[Heading], heading: Heading) -> list[Heading]:
    rank = _heading_rank(heading.level)
    kept = [item for item in hierarchy if _heading_rank(item.level) < rank]
    kept.append(heading)
    return kept


def _hierarchy_path(hierarchy: list[Heading]) -> str:
    return " > ".join(item.text for item in hierarchy)


def _split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
            current = current[-OVERLAP_CHARS:] if len(current) > OVERLAP_CHARS else ""
        if len(paragraph) > max_chars:
            sentences = re.split(r"(?<=[.!?。])\s+", paragraph)
            for sentence in sentences:
                if len(current) + len(sentence) + 1 > max_chars and current:
                    chunks.append(current.strip())
                    current = current[-OVERLAP_CHARS:] if len(current) > OVERLAP_CHARS else ""
                current = f"{current} {sentence}".strip()
        else:
            current = f"{current}\n\n{paragraph}".strip()

    if current:
        chunks.append(current.strip())
    return chunks


def legal_chunk_text(text: str, school: str) -> list[Document]:
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    documents: list[Document] = []
    hierarchy: list[Heading] = []
    current_heading = ""
    current_lines: list[str] = []
    current_chunk_type = "section"

    def flush() -> None:
        nonlocal current_lines, current_heading, current_chunk_type
        content = "\n".join(current_lines).strip()
        if len(content) < MIN_CHUNK_CHARS:
            current_lines = []
            return
        if _is_toc_line(current_heading) or _normalize_text(current_heading) == "mục lục":
            current_lines = []
            return

        for part_index, part in enumerate(_split_long_text(content)):
            if _is_toc_chunk(part):
                continue
            metadata = {
                "section_heading": current_heading,
                "hierarchy_path": _hierarchy_path(hierarchy),
                "chunk_type": current_chunk_type,
                "chunk_part": part_index,
            }
            documents.append(Document(page_content=part, metadata=metadata))
        current_lines = []

    for line in lines:
        if _is_footer_or_noise(line) or _is_toc_line(line):
            continue

        heading = detect_heading(line, school)
        if heading:
            flush()
            hierarchy = _update_hierarchy(hierarchy, heading)
            current_heading = heading.text
            current_chunk_type = heading.level
            current_lines = [line]
            continue

        if not current_heading:
            current_heading = "Giới thiệu"
            current_chunk_type = "intro"
        current_lines.append(line)

    flush()
    return documents


def load_faq_documents(faq_path: str | Path) -> list[Document]:
    faq_path = Path(faq_path)
    if not faq_path.exists():
        return []

    documents: list[Document] = []
    with faq_path.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            content = f"Câu hỏi: {item.get('question', '')}\nTrả lời: {item.get('answer', '')}"
            metadata = {
                "school": item.get("school", ""),
                "source": faq_path.name,
                "category": item.get("category", "khac"),
                "section_heading": item.get("question", ""),
                "hierarchy_path": f"FAQ > {item.get('category', 'khac')}",
                "chunk_type": "faq",
                "chunk_id": item.get("id", f"faq_{index}"),
            }
            documents.append(Document(page_content=content, metadata=metadata))
    return documents


def enrich_chunks(
    chunks: Iterable[Document],
    source_path: str | Path,
    faq_path: str | Path | None,
) -> list[Document]:
    source_path = Path(source_path)
    school = get_school_from_source_path(source_path)
    source_slug = re.sub(r"[^a-z0-9]+", "_", source_path.stem.casefold()).strip("_")
    enriched_chunks: list[Document] = []

    for index, chunk in enumerate(chunks):
        metadata = dict(chunk.metadata)
        metadata.update(
            {
                "school": school,
                "category": map_category(chunk.page_content, faq_path),
                "source": source_path.name,
                "chunk_id": f"{school.lower()}_{source_slug}_{index:05d}",
            }
        )
        enriched_chunks.append(Document(page_content=chunk.page_content, metadata=metadata))
    return enriched_chunks


def prepare_data(
    pdf_paths: Iterable[str | Path] | None = None,
    source_paths: Iterable[str | Path] | None = None,
    data_dir: str | Path = DATA_DIR,
    force_markdown: bool = False,
    include_faq: bool = True,
) -> list[Document]:
    """Task 1.2 pipeline: source files -> clean legal chunks -> metadata -> vector-ready docs."""
    print("--- Bắt đầu xử lý dữ liệu Task 1.2 ---")

    if source_paths is not None:
        paths = [Path(path) for path in source_paths]
    elif pdf_paths is not None:
        paths = [Path(path) for path in pdf_paths]
    else:
        paths = list_knowledge_source_paths(data_dir)
    if not paths:
        raise FileNotFoundError(f"Không tìm thấy PDF/TXT nguồn trong {Path(data_dir)}")

    all_chunks: list[Document] = []
    for source_path in tqdm(paths, desc="Xử lý nguồn"):
        school = get_school_from_source_path(source_path)
        faq_path = get_faq_path_for_school(school)

        text_path = source_to_text_path(source_path, force_pdf_extract=force_markdown)
        text = text_path.read_text(encoding="utf-8")
        legal_chunks = legal_chunk_text(text, school=school)
        enriched_chunks = enrich_chunks(legal_chunks, source_path, faq_path)
        all_chunks.extend(enriched_chunks)

        print(
            f"{source_path.name}: {len(enriched_chunks)} chunks, "
            f"text={text_path.name}, school={school}, faq={faq_path.name if faq_path else 'khong co'}"
        )

    if include_faq:
        for school in sorted({get_school_from_source_path(path) for path in paths}):
            faq_path = get_faq_path_for_school(school)
            if faq_path:
                faq_docs = load_faq_documents(faq_path)
                all_chunks.extend(faq_docs)
                print(f"{faq_path.name}: {len(faq_docs)} FAQ chunks")

    print(f"Hoàn thành. Tổng số chunks: {len(all_chunks)}")
    return all_chunks
