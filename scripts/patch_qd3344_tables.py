from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    PROJECT_ROOT / "data" / "processed_chunks_enriched.jsonl",
    PROJECT_ROOT / "data" / "review" / "approved_chunks.jsonl",
]
SUMMARY_PATH = PROJECT_ROOT / "data" / "review" / "stage22_qd3344_table_cleanup_summary.md"
MARKER = "[STAGE22_TABLE_CLEANUP]"


TABLE_PATCHES = {
    "huit_qd_3344_2025:legal_article:article_18:fdaecb0cbcdc3ecd": """

[STAGE22_TABLE_CLEANUP]

#### Bảng 1. Thời gian thiết kế và thời gian tối đa của một khóa học

| STT | Khóa học | Số HK theo thiết kế (Nkh) | Số năm học theo thiết kế (Ykh) | Số học kỳ tối đa (Nmax) | Số năm học tối đa (Ymax) |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Liên thông cao đẳng lên đại học, chính quy, cấp bằng cử nhân | 3 | 1,5 | 6 | 3 |
| 2 | Liên thông cao đẳng lên đại học, chính quy, cấp bằng kỹ sư | 4 | 2 | 7 | 3,5 |
| 3 | Liên thông cao đẳng lên đại học, vừa làm vừa học, cấp bằng cử nhân | 5 | 2,5 | 10 | 5 |
| 4 | Liên thông cao đẳng lên đại học, vừa làm vừa học, cấp bằng kỹ sư | 6 | 3 | 12 | 6 |
| 5 | Đại học chính quy, cấp bằng cử nhân | 7 | 3,5 | 12 | 6 |
| 6 | Đại học chính quy, cấp bằng kỹ sư | 8 | 4 | 14 | 7 |
| 7 | Đại học văn bằng thứ hai, cấp bằng cử nhân | 4-5 | 2-2,5 | 8 | 4 |
| 8 | Đại học văn bằng thứ hai, cấp bằng kỹ sư | 5-6 | 2,5-3 | 9 | 4,5 |
| 9 | Đại học vừa làm vừa học, cấp bằng cử nhân | 9 | 4,5 | 18 | 9 |
| 10 | Đại học vừa làm vừa học, cấp bằng kỹ sư | 10 | 5 | 20 | 10 |
""",
    "huit_qd_3344_2025:legal_clause:article_21_clause_2:b2b2e00542665387": """

[STAGE22_TABLE_CLEANUP]

#### Bảng 2. Số tín chỉ đăng ký tối thiểu và tối đa trong học kỳ

| TT | Bậc, hệ đào tạo | Đối tượng người học | Số tín chỉ tối thiểu/học kỳ, trừ học kỳ cuối khóa | Số tín chỉ tối đa/học kỳ |
| --- | --- | --- | ---: | --- |
| 1 | Đại học hệ chính quy | Điểm trung bình chung tích lũy đạt từ 2,00 trở lên | 14 | Không giới hạn |
| 1 | Đại học hệ chính quy | Điểm trung bình chung tích lũy dưới 2,00 nhưng chưa rơi vào trường hợp buộc thôi học | 10 | 14 |
| 1 | Đại học hệ chính quy | Người học học kỳ phụ trong hè | Không giới hạn | Không giới hạn |
| 2 | Đại học văn bằng thứ hai | Người học văn bằng thứ hai | 10 | Không giới hạn |
| 3 | Đại học liên thông | Người học liên thông | 10 | Không giới hạn |
| 4 | Đại học vừa làm vừa học | Người học vừa làm vừa học | 10 | Không giới hạn |
""",
    "huit_qd_3344_2025:legal_clause:article_30_clause_4:060beb13d7769fda": """

[STAGE22_TABLE_CLEANUP]

#### Bảng 3. Quy đổi giữa các thang điểm

| Xếp loại | Thang điểm 10 | Thang điểm 4 | Thang điểm chữ |
| --- | --- | ---: | --- |
| Giỏi | 8,5-10 | 4,0 | A |
| Khá | 8,0-8,4 | 3,5 | B+ |
| Khá | 7,0-7,9 | 3,0 | B |
| Trung bình | 6,5-6,9 | 2,5 | C+ |
| Trung bình | 5,5-6,4 | 2,0 | C |
| Trung bình yếu | 5,0-5,4 | 1,5 | D+ |
| Trung bình yếu | 4,0-4,9 | 1,0 | D |
| Kém | Dưới 4 | 0 | F |
""",
    "huit_qd_3344_2025:legal_clause:article_30_clause_5:0534610bcdb9261e": """

[STAGE22_TABLE_CLEANUP]

#### Bảng 4. Một số điểm đặc biệt dùng trong bảng kết quả học tập

| Ý nghĩa - tên điểm | Điểm chữ | Ghi chú - tính điểm trung bình và tích lũy |
| --- | --- | --- |
| Cấm thi | F | Tính như điểm 0 |
| Miễn thi, điểm thưởng | MT | Ghi chú tạm trong bảng điểm học kỳ; điểm miễn hệ 10 do Khoa đề nghị khi hoàn tất thủ tục |
| Vắng thi không phép | F | Tính như điểm 0 |
| Vắng thi có phép | I | Tính chưa tích lũy |
| Chưa nhận điểm thi | Z | Ghi chú tạm, tính chưa tích lũy |
| Bảo lưu | X | Tích lũy và ghi trong mục bảo lưu; không tính vào điểm trung bình học kỳ |
| Rút học phần | RT | Không tính điểm |
| Hủy học phần | H | Xóa hoàn toàn trong dữ liệu điểm |
""",
    "huit_qd_3344_2025:legal_article:article_32:62c51a457fd580a5": """

[STAGE22_TABLE_CLEANUP]

#### Quy đổi điểm chữ sang thang điểm 4 để tính GPA

| Điểm chữ | Điểm thang 4 |
| --- | ---: |
| A | 4,0 |
| B+ | 3,5 |
| B | 3,0 |
| C+ | 2,5 |
| C | 2,0 |
| D+ | 1,5 |
| D | 1,0 |
| F | 0,0 |

Công thức: GPA = tổng(ai * ni) / tổng(ni), trong đó ai là điểm học phần thứ i sau khi quy đổi sang thang điểm 4, ni là số tín chỉ của học phần thứ i.
""",
}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def patch_file(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    patched: list[str] = []
    for row in rows:
        chunk_id = row.get("chunk_id")
        patch = TABLE_PATCHES.get(chunk_id)
        if not patch:
            continue
        if MARKER not in row.get("text", ""):
            row["text"] = row["text"].rstrip() + patch.rstrip() + "\n"
            metadata = row.setdefault("metadata", {})
            metadata["content_hash"] = content_hash(row["text"])
            metadata["table_cleanup_status"] = "stage22_markdown_table_added"
            metadata["table_cleanup_stage"] = "stage22_qd3344_table_cleanup"
            patched.append(chunk_id)
    write_jsonl(path, rows)
    return {"path": str(path.relative_to(PROJECT_ROOT)), "patched_count": len(patched), "patched_chunk_ids": patched}


def main() -> int:
    results = [patch_file(path) for path in TARGETS]
    lines = [
        "# Stage 22 - QĐ-3344 Table Cleanup",
        "",
        "## Input",
        "",
        "- `data/processed_chunks_enriched.jsonl`",
        "- `data/review/approved_chunks.jsonl`",
        "- PDF text extracted from QĐ-3344 pages containing Bảng 1, Bảng 2, Bảng 3, Bảng 4 and GPA conversion.",
        "",
        "## Process",
        "",
        "1. Identified table-heavy QĐ-3344 chunks from Stage 21 audit.",
        "2. Added Markdown table versions to the existing chunk text without removing original legal text.",
        "3. Updated chunk metadata with `table_cleanup_status` and refreshed `content_hash`.",
        "",
        "## Output",
        "",
    ]
    for result in results:
        lines.append(f"- `{result['path']}`: patched {result['patched_count']} chunks")
    lines.extend(
        [
            "",
            "## Patched Tables",
            "",
            "- Điều 18, Bảng 1: thời gian thiết kế và thời gian tối đa của khóa học.",
            "- Điều 21, Bảng 2: số tín chỉ đăng ký tối thiểu và tối đa trong học kỳ.",
            "- Điều 30, Bảng 3: quy đổi thang điểm 10, thang điểm 4, điểm chữ.",
            "- Điều 30, Bảng 4: một số điểm đặc biệt trong bảng kết quả học tập.",
            "- Điều 32: quy đổi điểm chữ sang thang điểm 4 và công thức GPA.",
            "",
            "## Next",
            "",
            "Upsert `data/review/approved_chunks.jsonl` into ChromaDB and rerun QĐ-3344 audit plus retrieval audit.",
        ]
    )
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"results": results, "summary_path": str(SUMMARY_PATH.relative_to(PROJECT_ROOT))}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
