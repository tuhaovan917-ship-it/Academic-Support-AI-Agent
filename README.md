# HUIT Academic Support RAG & Agent

Dự án xây dựng bộ dữ liệu, Vector Database và lõi AI Agent tư vấn học vụ HUIT theo đề bài `Tài liệu tham khảo/TTS_T02_ChatBot.docx`.

Kiến trúc dữ liệu đi theo hướng RAG trong `Tài liệu tham khảo/2005.11401v4.pdf`: tài liệu học vụ được tiền xử lý, chia chunk, vector hóa, truy xuất top-k và dùng làm căn cứ trả lời có trích dẫn. Phần agent bám theo hướng autonomous agent/ReAct trong `Tài liệu tham khảo/2308.11432v7.pdf`: planner, retriever/tool action, memory ngắn hạn, answering và critic.

## Trạng Thái Hiện Tại

- Task 1.1: hoàn thành corpus học vụ.
- Task 1.2: hoàn thành tiền xử lý, chunking, vector hóa và audit retrieval.
- Task 2A: hoàn thành scaffold Multi-Agent rule-based với mock tools.
- Task 2B: hoàn thành `LLMClient` abstraction cho `mock`, `openai`, `ollama`; mặc định vẫn chạy mock và fallback an toàn về template Stage 2A.
- Task 2C: hoàn thành service contract, mã lỗi chuẩn và student API adapter để Task 3 có thể tích hợp.

Vector DB local:

- Thư mục: `huit_db/`
- Collection: `huit_academic_chunks`
- Embedding model: `BAAI/bge-m3`
- Tổng chunks trong DB: `141`
- Retrieval audit: `100/100` pass

`huit_db/` là artifact local và được ignore khỏi git. Có thể rebuild từ dữ liệu và script trong repo.

## Input Task 1

Nguồn dữ liệu chính nằm trong `data/raw/`:

- QĐ-3344 năm 2025: Quy chế đào tạo đại học theo hệ thống tín chỉ, nguồn luật hiện hành ưu tiên cao nhất.
- Hướng dẫn học vụ 2026: đăng ký học phần, học lại, rút học phần, tạm dừng, thôi học, chuyển ngành, kết quả học tập và tốt nghiệp.
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
- `data/review/approved_chunks.jsonl`: chunks đã duyệt để vector hóa.
- `data/review/audit_cases.jsonl`: 100 câu hỏi audit.
- `data/review/retrieval_audit_report.json`: kết quả audit chi tiết.
- `data/review/retrieval_audit_report.md`: report audit dạng Markdown.
- `data/review/source_review_decisions.yaml`: quyết định review nguồn.
- `huit_db/`: Chroma vector DB local.

Citation dùng định dạng Việt Nam, ví dụ:

```text
Quyết định số 3344/QĐ-DCT ngày 05/09/2025, Điều 40, trang 40
```

## Trạng Thái Nguồn Pending Và Discarded

Pending:

- BM09: có dấu hiệu domain HUFI cũ, cần xác nhận bản HUIT mới.
- QĐ-2658: PDF scan, cần review thủ công trước khi vector hóa.
- QĐ-3297: PDF scan, cần review thủ công trước khi vector hóa.

Discarded:

- QĐ-3230: đã bỏ theo quyết định người dùng, không dùng cho câu hỏi quy định hiện hành.

## Task 2A Và 2B - Core AI & Agents

Code được tổ chức như core module để CLI, Python API hoặc Task 3 API Gateway có thể dùng lại cùng một interface.

```text
src/agents/
  planner.py          # route câu hỏi và clarification
  retriever_agent.py  # gọi Vector DB Task 1
  tool_agent.py       # gọi tool interface
  answering_agent.py  # template answer + LLM answering
  critic_agent.py     # checklist pháp lý
  fallback.py         # câu trả lời an toàn
  orchestrator.py     # run_agent()

src/llm/
  base.py             # LLMResponse, LLMError, protocol
  factory.py          # chọn provider từ .env
  mock_client.py      # deterministic mock cho test
  openai_client.py    # OpenAI provider
  ollama_client.py    # Ollama provider
  prompts.py          # strict prompts

src/tools/
  mock_student_api.py # mock API lịch học, điểm, tốt nghiệp

src/memory/
  session_memory.py   # short-term session memory

data/mock/
  students.json
  schedules.json
  grades.json
```

Interface chính:

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
- `llm`
- `session_id`
- `student_id`

## Mock Sinh Viên

Stage 2A/2B có 5 sinh viên mẫu:

- `SV001`: đủ điều kiện cơ bản.
- `SV002`: còn nợ môn.
- `SV003`: GPA tích lũy dưới 2.0.
- `SV004`: học lại quá 5% tín chỉ, cần cảnh báo Điều 40.
- `SV005`: thiếu chứng chỉ/điều kiện bổ trợ.

## Cấu Hình LLM Stage 2B

Tạo `.env` từ `.env.example` nếu cần:

```env
LLM_PROVIDER=mock

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

LLM_TIMEOUT_SECONDS=30
LLM_TEMPERATURE=0.2
```

Provider:

- `mock`: mặc định, không gọi API thật, dùng cho test.
- `openai`: gọi OpenAI API khi có `OPENAI_API_KEY`.
- `ollama`: gọi Ollama local qua `http://localhost:11434`.

Hybrid Planner:

- `HYBRID_PLANNER_ENABLED=1`: bật kiến trúc hybrid.
- `HYBRID_PLANNER_MODE=auto`: mặc định; rule guard chạy trước, LLM planner chỉ xử lý câu mơ hồ hoặc rule chưa đủ chắc.
- `HYBRID_PLANNER_MODE=always`: ép gọi LLM Intent Classifier + Query Rewriter cho mọi câu không bị rule guard chặn.
- `HYBRID_PLANNER_MODE=off`: quay về planner rule-based.
- `HYBRID_PLANNER_MIN_CONFIDENCE=0.65`: ngưỡng confidence tối thiểu để nhận quyết định từ LLM planner.

Nếu provider lỗi, thiếu key, timeout, JSON sai hoặc citation không hợp lệ, hệ thống fallback về rule/template Stage 2A. Rule Guard và Critic vẫn kiểm soát nguồn pending/discarded, citation và các ràng buộc pháp lý.

## Chạy CLI

Mock mặc định:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="mock"
$env:MOCK_LLM_MODE="template"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_cli.py "SV002 còn nợ môn thì có được xét tốt nghiệp không?" --json
```

Ollama local:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_MODEL="qwen2.5:7b"
$env:HYBRID_PLANNER_MODE="auto"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_cli.py "SV004 học lại nhiều thì xếp loại giỏi có bị ảnh hưởng không?" --json
```

Ép kiểm tra Hybrid Planner bằng Ollama:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_MODEL="qwen2.5:7b"
$env:LLM_TIMEOUT_SECONDS="90"
$env:HYBRID_PLANNER_MODE="always"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_cli.py "Điểm A là từ mấy đến mấy?" --json
```

OpenAI:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_MODEL="gpt-4o-mini"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_cli.py "Muốn xét tốt nghiệp thì dùng biểu mẫu nào?" --json
```

## Setup Cho Máy Mới

Phần này dành cho đồng nghiệp pull repo về để chạy tiếp Task 3 hoặc kiểm thử Task 1/2.

### 1. Clone Và Tạo Môi Trường

```powershell
git clone https://github.com/tuhaovan917-ship-it/Academic-Support-AI-Agent.git
cd Academic-Support-AI-Agent
git checkout dev

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell không cho activate script, chạy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### 2. Cấu Hình `.env`

Tạo `.env` từ `.env.example`:

```powershell
Copy-Item .env.example .env
```

Cấu hình tối thiểu để chạy không cần AI local hoặc API key:

```env
LLM_PROVIDER=mock
MOCK_LLM_MODE=template
HYBRID_PLANNER_MODE=auto
STUDENT_API_PROVIDER=mock
```

Dùng OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Dùng Ollama local, nếu máy có cài Ollama:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
LLM_TIMEOUT_SECONDS=90
```

Nếu nhóm muốn dùng Gemini, kiến trúc đã có `LLMClient` abstraction nhưng hiện chưa có `GeminiClient`; chỉ cần thêm provider mới trong `src/llm/` mà không phải viết lại agent.

### 3. Chuẩn Bị Vector DB

`huit_db/` là artifact local và không nên push lên GitHub. Máy mới cần một trong hai cách:

Cách nhanh: copy nguyên thư mục `huit_db/` từ máy đã build sang thư mục gốc repo.

Cách rebuild:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="0"
$env:TRANSFORMERS_OFFLINE="0"
.\venv\Scripts\python.exe -X utf8 scripts\upsert_vector_db.py
```

Sau khi máy đã có sẵn embedding model trong cache, có thể chạy offline:

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
```

### 4. Chạy Kiểm Tra Nhanh

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="mock"
$env:MOCK_LLM_MODE="template"
$env:HYBRID_PLANNER_MODE="auto"
$env:STUDENT_API_PROVIDER="mock"

.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe -X utf8 tests\test_agent_stage2a.py
.\venv\Scripts\python.exe -X utf8 tests\test_llm_stage2b.py
.\venv\Scripts\python.exe -X utf8 tests\test_agent_service_2c.py
```

Chạy thử service contract cho Task 3:

```powershell
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_service_cli.py "Điểm A là từ mấy đến mấy?"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_service_cli.py "SV004 học lại nhiều thì xếp loại tốt nghiệp có bị ảnh hưởng không?" --debug
```

### 5. Kết Nối API Sinh Viên Thật Ở Task 3

Mặc định hệ thống dùng mock:

```env
STUDENT_API_PROVIDER=mock
```

Khi backend có API thật:

```env
STUDENT_API_PROVIDER=http
STUDENT_API_BASE_URL=http://localhost:5000
STUDENT_API_TIMEOUT_SECONDS=10
STUDENT_API_TOKEN=
```

Contract endpoint nằm ở `docs/contracts/student_api_contract.md`. Nếu backend trả khác tên trường, chỉ cần sửa adapter `src/tools/student_client.py`, không cần đổi Planner/Retriever/Answering/Critic.

## Test

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -m compileall scripts src tests
.\venv\Scripts\python.exe -X utf8 tests\test_retriever.py
.\venv\Scripts\python.exe -X utf8 tests\test_agent_stage2a.py
.\venv\Scripts\python.exe -X utf8 tests\test_llm_stage2b.py
```

Audit Hybrid Planner Stage 2B bằng mock, bao phủ route luật, tool, mixed, biểu mẫu, nguồn bị chặn và câu hỏi tự nhiên:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\venv\Scripts\python.exe -X utf8 scripts\audit_stage2b_hybrid.py --provider mock --planner-mode auto
```

Report được ghi tại:

- `data/review/stage2b_hybrid_audit.json`
- `data/review/stage2b_hybrid_audit.md`

Audit Ollama Stage 2B với các câu hỏi đại diện:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_MODEL="qwen2.5:7b"
$env:LLM_TIMEOUT_SECONDS="90"
.\venv\Scripts\python.exe -X utf8 scripts\audit_stage2b_ollama.py
```

Output:

```text
data/review/stage2b_ollama_audit.json
data/review/stage2b_ollama_audit.md
```

Audit full-domain Stage 2B.2:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_MODEL="qwen2.5:7b"
$env:LLM_TIMEOUT_SECONDS="90"
.\venv\Scripts\python.exe -X utf8 scripts\audit_stage2b2_full_domain.py
```

Output:

```text
data/review/stage2b2_full_domain_audit.json
data/review/stage2b2_full_domain_audit.md
```

Stage 2B.2 kiểm tra thêm constraint mapping của Điều 40, citation đến cấp điều/khoản khi phù hợp, metadata địa điểm biểu mẫu như Phòng Đào tạo/C.105, và knowledge boundary cho các mảng chưa có dữ liệu đã duyệt.

## Task 2C - Service Contract Cho Task 3

Task 2C đóng gói core agent thành service module ổn định để backend/API gateway ở Task 3 có thể gọi trực tiếp.

Module chính:

```text
src/api/
  agent_service.py   # AgentService.ask()
  schemas.py         # request/response dataclass
  errors.py          # mã lỗi chuẩn cho backend

src/tools/
  student_client.py  # mock/http student client factory
```

Interface cho Task 3:

```python
from src.api import AgentService, AgentServiceRequest

request = AgentServiceRequest(
    query="SV004 học lại nhiều thì xếp loại tốt nghiệp có bị ảnh hưởng không?",
    session_id="web-session-001",
    include_debug=False,
)

response = AgentService().ask(request)
payload = response.to_dict()
```

Response contract gồm:

- `answer`, `status`, `route`
- `session_id`, `student_id`
- `needs_clarification`, `clarification_questions`
- `citations`
- `error` với mã lỗi chuẩn như `ERR_MISSING_MSSV`, `ERR_STUDENT_API_UNAVAILABLE`, `ERR_POLICY_NOT_FOUND`
- `tool_results` nếu cần trả dữ liệu mock/API cá nhân

File contract mẫu:

- `docs/contracts/agent_request.example.json`
- `docs/contracts/agent_response_policy.example.json`
- `docs/contracts/agent_response_clarification.example.json`
- `docs/contracts/agent_response_tool.example.json`
- `docs/contracts/agent_response_fallback.example.json`
- `docs/contracts/student_api_contract.md`

Cấu hình mặc định vẫn dùng mock:

```env
STUDENT_API_PROVIDER=mock
```

Khi Task 3 có API sinh viên thật, đổi cấu hình:

```env
STUDENT_API_PROVIDER=http
STUDENT_API_BASE_URL=http://localhost:5000
STUDENT_API_TIMEOUT_SECONDS=10
STUDENT_API_TOKEN=
```

Nếu API thật trả schema đúng theo `docs/contracts/student_api_contract.md`, core agent không cần đổi logic. Nếu backend dùng tên trường khác, chỉ cần sửa adapter trong `src/tools/student_client.py`.

Chạy service CLI:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="mock"
$env:MOCK_LLM_MODE="template"
$env:HYBRID_PLANNER_MODE="auto"
$env:STUDENT_API_PROVIDER="mock"
.\venv\Scripts\python.exe -X utf8 scripts\run_agent_service_cli.py "SV004 học lại nhiều thì xếp loại tốt nghiệp có bị ảnh hưởng không?" --debug
```

Test contract Task 2C:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:LLM_PROVIDER="mock"
$env:MOCK_LLM_MODE="template"
$env:HYBRID_PLANNER_MODE="auto"
$env:STUDENT_API_PROVIDER="mock"
.\venv\Scripts\python.exe -X utf8 tests\test_agent_service_2c.py
```

Test bao phủ:

- Policy retrieval có citation.
- Form/procedure retrieval.
- Tool lịch học.
- Tool điểm/GPA.
- Mixed query: dữ liệu cá nhân + QĐ-3344.
- Clarification loop nhiều lượt khi thiếu MSSV.
- Fallback khi ngoài phạm vi hoặc không tìm thấy sinh viên.
- LLM mock path.
- Fallback khi LLM lỗi, provider sai, JSON/citation không hợp lệ.

## Bước Tiếp Theo

- Task 3: xây backend/API layer gọi `AgentService.ask()` theo contract trong `docs/contracts/`.
- Khi có API sinh viên thật, bật `STUDENT_API_PROVIDER=http` và đổi `STUDENT_API_BASE_URL`.
- Chạy thêm đánh giá với LLM thật OpenAI/Ollama trên bộ câu hỏi đại diện khi cần nâng chất lượng trả lời tự nhiên.
