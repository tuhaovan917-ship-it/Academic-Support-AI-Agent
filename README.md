# HUIT Academic Support RAG & Agent

Dự án xây dựng bộ dữ liệu, Vector Database và lõi AI Agent tư vấn học vụ HUIT theo đề bài `Tài liệu tham khảo/TTS_T02_ChatBot.docx`.

Hiện trạng:

- **Task 1.1**: Hoàn thành corpus học vụ.
- **Task 1.2**: Hoàn thành tiền xử lý, chunking theo cấu trúc điều/khoản/mục, vector hóa và audit retrieval.
- **Stage 2A của Task 2**: Hoàn thành scaffold Multi-Agent rule-based với mock tools, chưa gọi LLM thật.

Kiến trúc dữ liệu đi theo hướng RAG trong bài `Tài liệu tham khảo/2005.11401v4.pdf`: tài liệu học vụ được đưa vào dense vector index, retriever lấy top-k đoạn liên quan, agent dùng các đoạn này làm căn cứ trả lời có trích dẫn.

Stage 2A bám theo hướng LLM-based autonomous agent trong `Tài liệu tham khảo/2308.11432v7.pdf`: agent có planner, memory ngắn hạn, retriever/tool action và critic kiểm tra đầu ra.

## Trạng Thái Hiện Tại

- Vector DB local: `huit_db/`
- Chroma collection: `huit_academic_chunks`
- Embedding model: `BAAI/bge-m3`
- Tổng chunks trong DB: `141`
- Retrieval audit: `100/100` pass
- Active audit cases: `96`
- Pending-source audit cases: `3`
- Discarded-source audit cases: `1`

`huit_db/` là artifact local và được ignore khỏi git. Có thể rebuild từ dữ liệu và script trong repo.

## Input Task 1

Nguồn dữ liệu chính nằm trong `data/raw/`:

- QĐ-3344 năm 2025: Quy chế đào tạo đại học theo hệ thống tín chỉ, nguồn luật hiện hành ưu tiên cao nhất.
- Hướng dẫn học vụ 2026:
  - Đăng ký học phần.
  - Học vụ: tạm dừng, học lại, thôi học, chuyển ngành.
  - Kết quả học tập và tốt nghiệp.
- Biểu mẫu: BM02, BM03, BM04, BM08, BM09, BM10, BM11, BM12.
- FAQ tự thu thập: `faq_huit.jsonl`.
- Nguồn scan/pending: QĐ-2658, QĐ-3297.

Tài liệu tham khảo nằm trong `Tài liệu tham khảo/`:

- `TTS_T02_ChatBot.docx`
- `2005.11401v4.pdf`
- `2308.11432v7.pdf`

## Output Task 1

Artifact quan trọng:

- `data/document_manifest.yaml`: manifest điều phối nguồn, độ ưu tiên, trạng thái current/pending/discarded.
- `data/processed_chunks.jsonl`: chunks sau khi tách cấu trúc.
- `data/processed_chunks_enriched.jsonl`: chunks kèm metadata, citation, hash, priority.
- `data/forms_preview/`: bản xem nhanh cho biểu mẫu.
- `data/review/approved_chunks.jsonl`: chunks được phê duyệt để vector hóa.
- `data/review/audit_cases.jsonl`: 100 câu hỏi audit.
- `data/review/retrieval_audit_report.json`: kết quả audit chi tiết.
- `data/review/retrieval_audit_report.md`: report audit dạng Markdown.
- `data/review/source_review_decisions.yaml`: quyết định review nguồn.
- `huit_db/`: Chroma vector DB local.

## Task 1 Đã Xử Lý Gì

Đã thực hiện:

- Lập `document_manifest.yaml` cho toàn bộ nguồn.
- Bóc tách PDF, DOCX, JSONL.
- Làm sạch text và tạo manual review queue.
- Nhận diện cấu trúc QĐ-3344 theo chương, điều, khoản, điểm.
- Chunk theo loại tài liệu:
  - legal article/clause cho quy chế.
  - procedure section cho hướng dẫn học vụ.
  - form quick-view cho biểu mẫu.
  - FAQ chunk cho câu hỏi thường gặp.
- Giữ citation theo định dạng Việt Nam, ví dụ:

```text
Quyết định số 3344/QĐ-DCT ngày 05/09/2025, Điều 40, trang 40
```

- Làm sạch các bảng quan trọng trong QĐ-3344:
  - Điều 18, Bảng 1.
  - Điều 21, Bảng 2.
  - Điều 30, Bảng 3.
  - Điều 30, Bảng 4.
  - Điều 32, công thức GPA.
- Tạo form preview cho BM02, BM03, BM04, BM08, BM10, BM11, BM12.
- Giữ BM09 ở trạng thái pending vì có dấu hiệu domain HUFI cũ.
- Bỏ QĐ-3230 theo quyết định của user, không dùng cho câu trả lời quy định hiện hành.
- Giữ QĐ-2658 và QĐ-3297 ở pending, không vector hóa cho tới khi review thủ công.
- Upsert approved chunks vào ChromaDB.
- Audit retrieval với 100 câu hỏi, kết quả `100/100`.

## Chính Sách Nguồn

Khi hỏi quy định hiện hành, thứ tự ưu tiên là:

```text
QĐ-3344/current official docs > guidance 2026 > form > FAQ
```

Nguyên tắc:

- QĐ-3344 là nguồn luật hiện hành cao nhất trong corpus HUIT.
- FAQ chỉ hỗ trợ bắt intent và diễn giải, không thay nguồn pháp lý.
- Form chỉ dùng để gợi ý biểu mẫu, không thay thế điều khoản quy định.
- Nguồn pending/discarded không được dùng cho câu trả lời quy định hiện hành.
- Nếu sau này bổ sung dữ liệu, chỉ cần chạy lại pipeline/upsert theo `content_hash`, không cần huấn luyện lại model từ đầu.

## Pipeline Task 1

Chạy trong PowerShell từ project root:

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

Lần đầu có thể cần model từ HuggingFace. Sau khi model đã có cache, có thể chạy offline:

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

## Kiểm Tra Nhanh Task 1

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe -X utf8 tests\test_retriever.py
```

Kiểm tra audit summary:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe -c "import json; d=json.load(open('data/review/retrieval_audit_report.json', encoding='utf-8')); print({k:d[k] for k in ['total_cases','passed_cases','failed_cases','active_cases','pending_source_cases','discarded_source_cases','collection_count']})"
```

Kết quả mong đợi:

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

Retriever chính nằm tại `src/retriever.py`.

Ví dụ:

```python
from src.retriever import search_academic_policy

results = search_academic_policy(
    "Xếp loại tốt nghiệp có bị giảm nếu học lại quá 5% tín chỉ không?",
    intent="current_policy",
    k=3,
)
```

Kết quả trả về gồm:

- `chunk_id`
- `document_id`
- `source_type`
- `citation`
- `text`
- `score`
- metadata liên quan đến điều/khoản/biểu mẫu.

## Trạng Thái Nguồn Pending Và Discarded

Pending:

- BM09: có dấu hiệu domain HUFI cũ, cần xác nhận bản HUIT mới.
- QĐ-2658: PDF scan, cần review thủ công trước khi vector hóa.
- QĐ-3297: PDF scan, cần review thủ công trước khi vector hóa.

Discarded:

- QĐ-3230: đã bỏ theo quyết định user, không xử lý tiếp và không dùng cho câu hỏi quy định hiện hành.

## Task 2A - Rule-Based Multi-Agent Scaffold

Stage 2A chưa gọi LLM thật. Code được tổ chức như core module để CLI, Python API hoặc Task 3 API Gateway có thể dùng lại cùng một interface.

### Cấu Trúc

```text
src/agents/
  planner.py          # route câu hỏi và clarification
  retriever_agent.py  # gọi Vector DB Task 1
  tool_agent.py       # gọi tool interface
  answering_agent.py  # template answer blocks
  critic_agent.py     # checklist pháp lý
  fallback.py         # câu trả lời an toàn
  orchestrator.py     # run_agent()

src/tools/
  mock_student_api.py # mock API lịch học, điểm, tốt nghiệp

src/memory/
  session_memory.py   # short-term session memory

data/mock/
  students.json
  schedules.json
  grades.json

scripts/run_agent_cli.py
tests/test_agent_stage2a.py
```

### Interface Chính

```python
from src.agents import run_agent

response = run_agent(
    "SV002 còn nợ môn thì có được xét tốt nghiệp không?",
    session_id="demo",
)

print(response.to_dict())
```

Response gồm:

- `answer`
- `route`
- `status`
- `needs_clarification`
- `clarification_questions`
- `citations`
- `tool_results`
- `retrieval_results`
- `critic`
- `session_id`
- `student_id`

### Mock Sinh Viên

Stage 2A có 5 sinh viên mẫu:

- `SV001`: đủ điều kiện cơ bản.
- `SV002`: còn nợ môn.
- `SV003`: GPA tích lũy dưới 2.0.
- `SV004`: học lại quá 5% tín chỉ, cần cảnh báo Điều 40.
- `SV005`: thiếu chứng chỉ/điều kiện bổ trợ.

### Chạy CLI

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_cli.py "SV002 còn nợ môn thì có được xét tốt nghiệp không?" --json
```

### Test Stage 2A

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe -X utf8 tests\test_agent_stage2a.py
```

Test bao phủ:

- Policy retrieval có citation.
- Form/procedure retrieval.
- Tool lịch học.
- Tool điểm/GPA.
- Mixed query: dữ liệu cá nhân + QĐ-3344.
- Clarification loop nhiều lượt khi thiếu MSSV.
- Fallback khi ngoài phạm vi hoặc không tìm thấy sinh viên.

## Bước Tiếp Theo

- Stage 2B: gắn LLM thật cho Planner/Answering nhưng giữ nguyên interface `run_agent()`.
- Stage 2C: thay `MockStudentAPI` bằng client gọi API thật của Task 3.
- Bổ sung long-term/session memory qua database khi Task 3 có SQL Server.
