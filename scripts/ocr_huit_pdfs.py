from __future__ import annotations

import argparse
import sys
from pathlib import Path

import easyocr
import numpy as np
import pypdfium2 as pdfium
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HUIT_DIR = PROJECT_ROOT / "data" / "raw" / "HUIT"

DEFAULT_TARGET_PATTERNS = [
    "20230913-qd2658-*.pdf",
    "qd3297-*.pdf",
    "q*3230-*.pdf",
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _find_default_pdf_paths(huit_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in DEFAULT_TARGET_PATTERNS:
        paths.extend(huit_dir.glob(pattern))
    return sorted(set(paths))


def _render_page_to_image(page: pdfium.PdfPage, scale: float) -> Image.Image:
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil()
    return image.convert("RGB")


def ocr_pdf(
    pdf_path: Path,
    reader: easyocr.Reader,
    output_path: Path | None = None,
    scale: float = 2.0,
    max_pages: int | None = None,
) -> Path:
    output_path = output_path or pdf_path.with_name(f"{pdf_path.stem}_extracted.txt")
    document = pdfium.PdfDocument(str(pdf_path))

    page_count = len(document)
    if max_pages is not None:
        page_count = min(page_count, max_pages)

    pages: list[str] = []
    try:
        for page_index in range(page_count):
            page = document[page_index]
            try:
                image = _render_page_to_image(page, scale=scale)
                lines = reader.readtext(np.array(image), detail=0, paragraph=True)
            finally:
                page.close()

            text = "\n".join(line.strip() for line in lines if line.strip())
            if text:
                pages.append(f"--- PAGE {page_index + 1} ---\n{text}")
            print(f"{pdf_path.name}: OCR trang {page_index + 1}/{page_count}, {len(text)} ký tự")
    finally:
        document.close()

    output_path.write_text("\n\n".join(pages), encoding="utf-8")
    print(f"Đã ghi {output_path} ({output_path.stat().st_size} bytes)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR các PDF scan trong data/raw/HUIT.")
    parser.add_argument(
        "--pdf",
        action="append",
        type=Path,
        help="PDF cần OCR. Có thể truyền nhiều lần. Mặc định: 3 PDF HUIT đang thiếu text.",
    )
    parser.add_argument("--huit-dir", type=Path, default=DEFAULT_HUIT_DIR)
    parser.add_argument("--scale", type=float, default=2.0, help="Tỉ lệ render PDF. Cao hơn thì OCR chậm hơn.")
    parser.add_argument("--max-pages", type=int, help="OCR thử tối đa N trang mỗi PDF.")
    parser.add_argument("--gpu", action="store_true", help="Dùng GPU cho EasyOCR nếu máy hỗ trợ.")
    args = parser.parse_args()

    pdf_paths = args.pdf or _find_default_pdf_paths(args.huit_dir)
    if not pdf_paths:
        raise FileNotFoundError(f"Không tìm thấy PDF HUIT cần OCR trong {args.huit_dir}")

    print("Khởi tạo EasyOCR Reader...")
    reader = easyocr.Reader(["vi", "en"], gpu=args.gpu)

    for pdf_path in pdf_paths:
        ocr_pdf(
            pdf_path=pdf_path,
            reader=reader,
            scale=args.scale,
            max_pages=args.max_pages,
        )


if __name__ == "__main__":
    main()
