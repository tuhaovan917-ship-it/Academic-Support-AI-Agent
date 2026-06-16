# Stage 22 - QĐ-3344 Table Cleanup

## Input

- `data/processed_chunks_enriched.jsonl`
- `data/review/approved_chunks.jsonl`
- PDF text extracted from QĐ-3344 pages containing Bảng 1, Bảng 2, Bảng 3, Bảng 4 and GPA conversion.

## Process

1. Identified table-heavy QĐ-3344 chunks from Stage 21 audit.
2. Added Markdown table versions to the existing chunk text without removing original legal text.
3. Updated chunk metadata with `table_cleanup_status` and refreshed `content_hash`.

## Output

- `data\processed_chunks_enriched.jsonl`: patched 5 chunks
- `data\review\approved_chunks.jsonl`: patched 5 chunks

## Patched Tables

- Điều 18, Bảng 1: thời gian thiết kế và thời gian tối đa của khóa học.
- Điều 21, Bảng 2: số tín chỉ đăng ký tối thiểu và tối đa trong học kỳ.
- Điều 30, Bảng 3: quy đổi thang điểm 10, thang điểm 4, điểm chữ.
- Điều 30, Bảng 4: một số điểm đặc biệt trong bảng kết quả học tập.
- Điều 32: quy đổi điểm chữ sang thang điểm 4 và công thức GPA.

## Next

Upsert `data/review/approved_chunks.jsonl` into ChromaDB and rerun QĐ-3344 audit plus retrieval audit.
