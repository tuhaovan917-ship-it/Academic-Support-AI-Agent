# Academic Support AI Agent

Dự án này xây dựng pipeline Retrieval-Augmented Generation (RAG) cho trợ lý học vụ HCMUT. Ở giai đoạn hiện tại, project tập trung vào việc xử lý dữ liệu từ **Sổ tay sinh viên** và **FAQ**, đưa dữ liệu vào **Chroma vector database**, rồi kiểm tra khả năng truy hồi thông tin.

## Cấu trúc thư mục

```text
AIAgentHocVu/
├── data/
│   ├── SỔ TAY SV - Bách Khoa - NĂM HỌC 2025-2026.pdf
│   └── faq_hcmut.jsonl
├── chroma_db/
├── src/
│   ├── __init__.py
│   ├── data_processor.py
│   └── retriever.py
├── tests/
│   └── test_retrieval.py
├── main.py
├── requirements.txt
└── thu_nghiem.ipynb
```

## Vai trò từng phần

- `data/`: chứa dữ liệu gốc, gồm PDF sổ tay sinh viên và file FAQ dạng JSONL.
- `src/data_processor.py`: đọc PDF/FAQ, chia nhỏ tài liệu thành chunks, gắn metadata.
- `src/retriever.py`: tạo Chroma DB, load Chroma DB, và chạy similarity search.
- `main.py`: script chính để build lại vector database.
- `tests/test_retrieval.py`: script test retrieval nhanh bằng một câu hỏi mẫu hoặc câu hỏi tự nhập.
- `thu_nghiem.ipynb`: notebook nháp, chỉ nên dùng để gọi lại các hàm trong `src/`.
- `chroma_db/`: database vector được sinh ra sau khi chạy build. Thư mục này không nên commit lên Git.

## Luồng hoạt động

1. `main.py` gọi `prepare_data()` trong `src/data_processor.py`.
2. `prepare_data()` đọc PDF bằng `UnstructuredPDFLoader`.
3. Nếu có `faq_hcmut.jsonl`, FAQ cũng được chuyển thành `Document`.
4. Toàn bộ tài liệu được chia chunk bằng `RecursiveCharacterTextSplitter`.
5. Mỗi chunk được gắn metadata như `source_name`, `page_number`, `category`, `chunk_id`.
6. `setup_vector_db()` trong `src/retriever.py` embedding các chunks bằng model `intfloat/multilingual-e5-base`.
7. Chunks sau khi embedding được lưu vào `chroma_db/`.
8. Khi test, `tests/test_retrieval.py` load lại `chroma_db/` và tìm các đoạn liên quan nhất với câu hỏi.

## Cài đặt môi trường

Nếu dùng virtualenv đã có trong project:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu đang kích hoạt sẵn môi trường Python khác:

```powershell
pip install -r requirements.txt
```

## Khi nào cần build lại từ đầu?

Bạn nên build lại Chroma DB khi:

- sửa logic trong `src/data_processor.py`;
- đổi `chunk_size`, `chunk_overlap`, hoặc `separators`;
- thêm/sửa file PDF hoặc FAQ;
- đổi embedding model;
- thấy kết quả retrieval bị lẫn dữ liệu cũ hoặc trùng lặp.

Vì bạn vừa sửa `data_processor.py`, nên **nên chạy lại từ đầu**.

## Có cần xóa `chroma_db/` không?

Có, trong trường hợp này nên xóa hoặc reset `chroma_db/` trước khi build lại. Lý do là Chroma DB cũ đang được tạo từ cấu hình chunking cũ. Nếu build chồng lên DB cũ, dữ liệu có thể bị trùng hoặc retrieval trả về kết quả lẫn giữa cấu hình cũ và mới.

Bạn không cần xóa thủ công. Hãy dùng flag `--reset`:

```powershell
.\venv\Scripts\python.exe main.py --reset
```

Lệnh này sẽ xóa `chroma_db/` cũ rồi tạo lại database mới từ dữ liệu trong `data/`.

## Build lại Chroma DB

Chạy bản đầy đủ, gồm cả PDF và FAQ:

```powershell
.\venv\Scripts\python.exe main.py --reset
```

Nếu chỉ muốn index PDF, không đưa FAQ vào DB:

```powershell
.\venv\Scripts\python.exe main.py --reset --no-faq
```

Nếu muốn thử thông số chunking khác:

```powershell
.\venv\Scripts\python.exe main.py --reset --chunk-size 800 --chunk-overlap 150
```

## Test retrieval

Chạy câu hỏi mặc định:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py
```

Test bằng câu hỏi riêng:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py --query "Việc đánh giá điểm rèn luyện dựa trên bao nhiêu tiêu chí?" --k 5
```

Ví dụ khác:

```powershell
.\venv\Scripts\python.exe tests\test_retrieval.py --query "Sinh viên năm nhất có cần tự đăng ký môn học không?" --k 3
```

## Cách đánh giá kết quả retrieval

Kết quả tốt khi:

- đoạn trả về có liên quan trực tiếp tới câu hỏi;
- nếu hỏi về quy định, đoạn trả về nên bám sát điều/khoản/trang trong sổ tay;
- nếu hỏi câu phổ biến đã có trong FAQ, kết quả nên ưu tiên hoặc ít nhất có xuất hiện nội dung từ `faq_hcmut`;
- các đoạn không bị quá dài, quá vụn, hoặc lạc chủ đề.

Nếu kết quả bị lệch, hãy tinh chỉnh trong `src/data_processor.py`:

- giảm `chunk_size` nếu đoạn trả về quá lan man;
- tăng `chunk_overlap` nếu câu trả lời bị thiếu ngữ cảnh;
- chỉnh `separators` nếu chunk bị cắt giữa Điều/Khoản quan trọng.

## Ghi chú

- Lần đầu chạy embedding model có thể mất thời gian vì cần load model từ Hugging Face cache.
- Nếu thấy cảnh báo `HF_TOKEN`, đó chỉ là cảnh báo rate limit. Có token thì tải model ổn định hơn, nhưng không bắt buộc nếu model đã có cache.
- `chroma_db/` là dữ liệu sinh ra tự động, đã được thêm vào `.gitignore`.
