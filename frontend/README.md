# Frontend - HUIT AI Chat UI

Angular frontend cho chatbot tư vấn học vụ HUIT. Giao diện hiện đã sẵn sàng gọi backend qua `/api/chat`, hiển thị tin nhắn, trạng thái đang trả lời, bảng dữ liệu học vụ và citations khi backend/RAG trả về.

## Cấu trúc

```text
frontend/
├── src/
│   ├── app/
│   │   ├── app.component.html
│   │   ├── app.component.css
│   │   ├── app.component.ts
│   │   ├── models/
│   │   │   └── academic.models.ts
│   │   └── services/
│   │       └── academic-api.service.ts
│   └── environments/
│       └── environment.ts
├── angular.json
├── package.json
└── package-lock.json
```

## Cài dependencies

Chạy trong thư mục `frontend`:

```powershell
npm install
```

Nếu `node_modules` đã có sẵn thì có thể bỏ qua bước này.

## Chạy frontend

Trước tiên chạy backend:

```powershell
dotnet run --project ..\backend\AcademicSupport.Api\AcademicSupport.Api.csproj --urls http://localhost:5098
```

Sau đó chạy frontend:

```powershell
npm start
```

Mở trình duyệt:

```text
http://127.0.0.1:4200
```

## Cấu hình API

Frontend đọc backend URL tại:

```text
src/environments/environment.ts
```

Mặc định:

```ts
export const environment = {
  apiBaseUrl: 'http://localhost:5098/api',
};
```

Nếu đổi port backend, sửa `apiBaseUrl` cho khớp.

## Build kiểm tra

```powershell
npm run build
```

Thư mục `dist/` là output build, không cần commit.

## Luồng chat hiện tại

- Người dùng nhập câu hỏi.
- UI hiển thị câu hỏi ngay và tự cuộn xuống cuối.
- UI hiển thị trạng thái HUIT AI đang kiểm tra dữ liệu.
- Backend trả `ChatResponse`.
- UI hiển thị câu trả lời, cards như lịch học/điểm/thông tin sinh viên, và citations nếu có.

## Khi tích hợp RAG

Frontend không cần biết backend dùng mock, SQL hay RAG. Chỉ cần backend tiếp tục trả format:

```text
sessionId
userMessage
assistantMessage
cards
citations
```

Nếu RAG trả nguồn tài liệu, đưa vào `citations` để UI hiển thị.
