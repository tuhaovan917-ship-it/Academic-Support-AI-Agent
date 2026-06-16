# HUIT Academic Support RAG

Du an xay dung bo du lieu va Vector Database cho AI Agent tu van hoc vu HUIT, theo Task 1 trong `Tai lieu tham khao/TTS_T02_ChatBot.docx`.

Task 1 da hoan thanh gom:

- Task 1.1: Xay dung corpus hoc vu.
- Task 1.2: Tien xu ly, chunking giu cau truc dieu khoan/muc, vector hoa va kiem thu retrieval.

Kien truc du lieu di theo huong RAG trong bai `Tai lieu tham khao/2005.11401v4.pdf`: tai lieu duoc dua vao bo nho phi tham so dang dense vector index, retriever lay top-k doan lien quan, generator/agent se dung cac doan nay lam can cu tra loi co citation.

## Trang Thai

- Vector DB local: `huit_db/`
- Chroma collection: `huit_academic_chunks`
- Embedding model: `BAAI/bge-m3`
- Tong chunks trong DB: `141`
- Audit retrieval: `100/100` pass
- Active audit cases: `96`
- Pending-source audit cases: `3`
- Discarded-source audit cases: `1`

`huit_db/` la artifact local va duoc ignore khoi git. Co the rebuild tu cac script va du lieu trong repo.

## Input Task 1

Nguon du lieu chinh nam trong `data/raw/`:

- QD-3344 nam 2025: Quy che dao tao dai hoc theo he thong tin chi, nguon luat hien hanh uu tien cao nhat.
- Huong dan hoc vu 2026:
  - Dang ky hoc phan.
  - Hoc vu: tam dung, hoc lai, thoi hoc, chuyen nganh.
  - Ket qua hoc tap va tot nghiep.
- Bieu mau: BM02, BM03, BM04, BM08, BM09, BM10, BM11, BM12.
- FAQ tu thu thap: `faq_huit.jsonl`.
- Nguon scan/pending: QD-2658, QD-3297.

Tai lieu tham khao nam trong `Tai lieu tham khao/`:

- `TTS_T02_ChatBot.docx`
- `2005.11401v4.pdf`
- `2308.11432v7.pdf`

## Output Hien Tai

Artifact quan trong:

- `data/document_manifest.yaml`: manifest dieu phoi nguon, do uu tien, trang thai current/pending/discarded.
- `data/processed_chunks.jsonl`: chunks sau khi tach cau truc.
- `data/processed_chunks_enriched.jsonl`: chunks kem metadata, citation, hash, priority.
- `data/forms_preview/`: ban xem nhanh cho bieu mau.
- `data/review/approved_chunks.jsonl`: chunks duoc phe duyet de vector hoa.
- `data/review/audit_cases.jsonl`: 100 cau hoi audit.
- `data/review/retrieval_audit_report.json`: ket qua audit chi tiet.
- `data/review/retrieval_audit_report.md`: report audit dang Markdown.
- `data/review/source_review_decisions.yaml`: quyet dinh review nguon.
- `huit_db/`: Chroma vector DB local.

## Ket Qua Xu Ly

Da thuc hien:

- Lap `document_manifest.yaml` cho toan bo nguon.
- Boc tach PDF, DOCX, JSONL.
- Lam sach text va tao manual review queue.
- Nhan dien cau truc QD-3344 theo chuong, dieu, khoan, diem.
- Chunk theo loai tai lieu:
  - legal article/clause cho quy che.
  - procedure section cho huong dan hoc vu.
  - form quick-view cho bieu mau.
  - faq chunk cho cau hoi thuong gap.
- Giu citation theo dinh dang Viet Nam, vi du:

```text
Quyet dinh so 3344/QD-DCT ngay 05/09/2025, Dieu 40, trang 40
```

- Lam sach cac bang quan trong trong QD-3344:
  - Dieu 18, Bang 1.
  - Dieu 21, Bang 2.
  - Dieu 30, Bang 3.
  - Dieu 30, Bang 4.
  - Dieu 32, cong thuc GPA.
- Tao form preview cho BM02, BM03, BM04, BM08, BM10, BM11, BM12.
- Giu BM09 o trang thai pending vi co dau hieu domain HUFI cu.
- Bo QD-3230 theo quyet dinh user, khong dung cho cau tra loi quy dinh hien hanh.
- Giu QD-2658 va QD-3297 o pending, khong vector hoa cho toi khi review thu cong.
- Upsert approved chunks vao ChromaDB.
- Audit retrieval voi 100 cau hoi bao phu nhieu chu de, ket qua `100/100`.

## Chinh Sach Nguon

Khi hoi quy dinh hien hanh, thu tu uu tien la:

```text
QD-3344/current official docs > guidance 2026 > form > FAQ
```

Nguyen tac:

- QD-3344 la nguon luat hien hanh cao nhat trong corpus HUIT.
- FAQ chi ho tro bat intent va dien giai, khong thay nguon phap ly.
- Form chi dung de goi y bieu mau, khong thay the dieu khoan quy dinh.
- Nguon pending/discarded khong duoc dung cho cau tra loi quy dinh hien hanh.
- Neu sau nay bo sung du lieu, chi can chay lai pipeline/upsert incremental theo `content_hash`, khong can huan luyen lai model tu dau.

## Pipeline

Chay trong PowerShell tu project root:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

### 1. Extract Raw Documents

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\extract_raw_documents.py
```

Output:

```text
data/processed_raw/
data/processed_raw/_extraction_summary.json
```

### 2. Clean Raw Documents

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\clean_raw_documents.py
```

Output:

```text
data/processed_clean/
data/review/manual_review_items.jsonl
```

### 3. Structure Documents

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\structure_documents.py
```

Output:

```text
data/intermediate/structured_documents.jsonl
data/intermediate/structure_summary.json
```

### 4. Build Chunks

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\build_chunks.py
```

Output:

```text
data/processed_chunks.jsonl
data/processed_chunks_enriched.jsonl
data/intermediate/chunk_summary.json
```

### 5. Generate Form Previews

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\generate_form_previews.py
```

Output:

```text
data/forms_preview/
data/review/form_review_summary.json
```

### 6. Apply Review Gate

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\apply_review_gate.py
```

Output:

```text
data/review/approved_chunks.jsonl
data/review/pending_chunks.jsonl
data/review/rejected_or_blocked_chunks.jsonl
data/review/review_summary.json
```

### 7. Upsert Vector DB

Lan dau co the can model tu HuggingFace. Sau khi model da co cache, co the chay offline:

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -X utf8 scripts\upsert_vector_db.py --reset
```

Output:

```text
huit_db/
data/intermediate/vector_upsert_summary.json
```

### 8. Audit Retrieval

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -X utf8 scripts\audit_retrieval.py
```

Output:

```text
data/review/retrieval_audit_report.json
data/review/retrieval_audit_report.md
```

## Cach Kiem Tra Nhanh

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe -X utf8 tests\test_retriever.py
```

Kiem tra audit summary:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -c "import json; d=json.load(open('data/review/retrieval_audit_report.json', encoding='utf-8')); print({k:d[k] for k in ['total_cases','passed_cases','failed_cases','active_cases','pending_source_cases','discarded_source_cases','collection_count']})"
```

Ket qua mong doi:

```text
total_cases: 100
passed_cases: 100
failed_cases: 0
active_cases: 96
pending_source_cases: 3
discarded_source_cases: 1
collection_count: 141
```

## Retriever API

Retriever chinh nam tai `src/retriever.py`.

Vi du:

```python
from src.retriever import search_academic_policy

results = search_academic_policy(
    "Xep loai tot nghiep co bi giam neu hoc lai qua 5% tin chi khong?",
    intent="current_policy",
    k=3,
)
```

Ket qua tra ve gom:

- `chunk_id`
- `document_id`
- `source_type`
- `citation`
- `text`
- `score`
- metadata lien quan den dieu/khoan/bieu mau.

## Trang Thai Nguon Pending Va Discarded

Pending:

- BM09: co dau hieu domain HUFI cu, can xac nhan ban HUIT moi.
- QD-2658: PDF scan, can review thu cong truoc khi vector hoa.
- QD-3297: PDF scan, can review thu cong truoc khi vector hoa.

Discarded:

- QD-3230: da bo theo quyet dinh user, khong xu ly tiep va khong dung cho cau hoi quy dinh hien hanh.

## Buoc Tiep Theo

Task 1 da hoan thanh. Buoc tiep theo la Task 2:

- Planner Agent phan loai cau hoi.
- Retriever Agent goi `src/retriever.py`.
- Answering Agent tong hop cau tra loi co citation.
- Critic Agent kiem tra cau tra loi, canh bao khi thieu nguon hoac nguon pending.
