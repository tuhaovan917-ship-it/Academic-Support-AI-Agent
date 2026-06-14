# Academic Support AI Agent

Dự án này triển khai **Task 1.2: Tiền xử lý và Vector hóa** cho dữ liệu sổ tay sinh viên HCMUT/NTTU.

Mục tiêu của Task 1.2:

- bóc tách text từ PDF;
- giữ cấu trúc điều khoản/mục khi chunking để LLM không trả lời sai luật;
- enrich metadata đủ dùng cho truy hồi;
- vector hóa dữ liệu và lưu vào ChromaDB local.

## Cấu trúc chính

```text
AIAgentHocVu/
├── data/
│   ├── SỔ TAY SV - Bách Khoa - NĂM HỌC 2025-2026.pdf
│   ├── Sổ tay sinh viên Nguyễn Tất Thành.pdf
│   ├── faq_hcmut.jsonl
│   └── faq_nttu.jsonl
├── src/
│   ├── data_processor.py
│   └── retriever.py
├── scripts/
│   └── audit_vector_db.py
├── tests/
│   └── test_retrieval.py
├── main.py
└── requirements.txt
```

Các thư mục sinh tự động và không commit:

- `data/processed/`: text cache sau khi bóc PDF.
- `hcmut_nttu_db/`: ChromaDB local.
- `chroma_db/`: DB thử nghiệm cũ, không còn dùng.

## Pipeline Task 1.2

Pipeline hiện tại không phụ thuộc hoàn toàn vào Markdown heading nữa, vì PDF thật sinh heading khá nhiễu. Thay vào đó, project dùng rule-based legal chunking:

```text
PDF
-> unstructured hi_res
-> text sạch + giữ bảng dạng Markdown table nếu có
-> bỏ mục lục/header/footer/số trang rác
-> chunk theo PHẦN / CHƯƠNG / MỤC / Điều / 1.1 / 1.1.1
-> tách phụ nếu chunk quá dài
-> enrich metadata
-> embedding BAAI/bge-m3 bằng GPU nếu có
-> ChromaDB local
```

Metadata mỗi chunk:

- `school`: `HCMUT` hoặc `NTTU`.
- `source`: tên file PDF/FAQ gốc.
- `category`: nhóm nội dung như `diem_ren_luyen`, `hoc_phi_hoc_bong`, `hoc_vu`.
- `section_heading`: tiêu đề gần nhất của chunk.
- `hierarchy_path`: đường dẫn cấu trúc cha.
- `chunk_type`: `part`, `section`, `article`, `numbered`, `topic`, `faq`, ...
- `chunk_id`: mã chunk.

## GPU và HuggingFace

Project đọc token từ `.env` local. File này đã nằm trong `.gitignore`.

PyTorch CUDA hiện đã được cài trong `venv`:

```text
torch 2.11.0+cu128
GPU: NVIDIA GeForce RTX 5050 Laptop GPU
```

Kiểm tra GPU:

```powershell
.\venv\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

## Chạy build lại từ đầu

Nên chạy bằng PowerShell tại thư mục project:

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8
$env:EMBEDDING_DEVICE="cuda"
.\venv\Scripts\python.exe main.py --reset --force-markdown
```

Ý nghĩa:

- `--reset`: xóa `hcmut_nttu_db/` cũ trước khi tạo lại.
- `--force-markdown`: ép bóc PDF lại, không dùng cache trong `data/processed/`.
- `EMBEDDING_DEVICE=cuda`: ép embedding chạy GPU.

Nếu chỉ muốn xử lý một trường:

```powershell
.\venv\Scripts\python.exe main.py --reset --force-markdown --pdf "data\SỔ TAY SV - Bách Khoa - NĂM HỌC 2025-2026.pdf"
```

## Audit chất lượng DB

Sau khi build xong, kiểm tra số lượng chunk và keyword:

```powershell
.\venv\Scripts\python.exe scripts\audit_vector_db.py --keyword "rèn luyện"
```

Lọc riêng HCMUT:

```powershell
.\venv\Scripts\python.exe scripts\audit_vector_db.py --keyword "rèn luyện" --school HCMUT
```

Kỳ vọng tốt:

- Tổng số chunks phải lớn hơn nhiều so với bản lỗi cũ 18 chunks.
- `Chunks thuộc MỤC LỤC` nên bằng 0.
- Keyword `rèn luyện` phải có chunk category `diem_ren_luyen`.
- Không có quá nhiều chunk dài hơn 2600 ký tự.

## Test retrieval

Hybrid search là mặc định, kết hợp BM25 + Chroma vector search:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py --query "Việc đánh giá điểm rèn luyện dựa trên bao nhiêu tiêu chí?" --school HCMUT --k 5
```

So sánh với vector search thuần:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py --query "Việc đánh giá điểm rèn luyện dựa trên bao nhiêu tiêu chí?" --school HCMUT --k 5 --vector-only
```

## Chạy Task 1.2 với dữ liệu HUIT

Dữ liệu HUIT đặt tại `data/raw/HUIT/`. Pipeline sẽ:

- đọc các PDF trong thư mục HUIT;
- ưu tiên dùng file `_extracted.txt` cùng tên nếu đã có;
- nếu `_extracted.txt` rỗng, thử fallback bóc text bằng `pypdf` và cache vào `data/processed/huit/`;
- nạp `faq_huit.jsonl`;
- lưu Chroma DB riêng tại `data/huit_db/`.

Build lại DB HUIT:

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
$env:EMBEDDING_DEVICE="cpu"
.\venv\Scripts\python.exe main.py --school HUIT --reset
```

Nếu 3 PDF scan của HUIT bị rỗng text, chạy OCR trước:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\venv\Scripts\python.exe scripts\ocr_huit_pdfs.py --scale 2
.\venv\Scripts\python.exe main.py --school HUIT --reset
```

Audit nhanh DB HUIT:

```powershell
.\venv\Scripts\python.exe scripts\audit_vector_db.py --school HUIT --keyword "cảnh báo học vụ" --limit 3
```

Test retrieval HUIT:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py --school HUIT --query "Sinh viên bị cảnh báo học vụ mấy lần thì bị buộc thôi học?" --k 3
```

## Ghi chú

- GPU giúp embedding nhanh hơn, nhưng độ chính xác phụ thuộc chủ yếu vào chunking và metadata.
- Mục lục không được index vào Vector DB vì dễ gây nhiễu retrieval.
- FAQ JSONL được đưa vào DB như các chunk riêng để tăng khả năng trả lời các câu hỏi phổ biến.
