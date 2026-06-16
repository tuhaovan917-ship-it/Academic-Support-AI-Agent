# Backend - AcademicSupport.Api

ASP.NET Core Web API cho chatbot tư vấn học vụ HUIT. Backend hiện ở trạng thái demo/RAG-ready: API đã ổn định để frontend gọi, còn dữ liệu đang lấy từ mock service.

## Cấu trúc

```text
backend/
└── AcademicSupport.Api/
    ├── Models/
    │   └── AcademicModels.cs
    ├── Services/
    │   ├── IAcademicStore.cs
    │   ├── IChatAnswerService.cs
    │   ├── MockAcademicStore.cs
    │   └── MockChatService.cs
    ├── Program.cs
    ├── appsettings.json
    └── appsettings.Development.json
```

## Chạy backend

Chạy từ thư mục gốc project:

```powershell
dotnet run --project backend\AcademicSupport.Api\AcademicSupport.Api.csproj --urls http://localhost:5098
```

Kiểm tra API:

```powershell
Invoke-RestMethod http://localhost:5098/api/health
```

## Endpoint chính

```text
GET  /api/health
GET  /api/students
GET  /api/students/{studentId}
GET  /api/students/{studentId}/schedule
GET  /api/students/{studentId}/grades
GET  /api/students/{studentId}/academic-summary
GET  /api/chat/sessions?studentId=SV001
GET  /api/chat/sessions/{sessionId}/messages
POST /api/chat
```

Ví dụ gọi chat:

```powershell
$body = @{
  studentId = "SV001"
  message = "Tên sinh viên của em là gì?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://localhost:5098/api/chat" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

## Dữ liệu hiện tại

Hiện backend dùng dữ liệu mock trong `MockAcademicStore.cs`. File SQL trong `database/sqlserver` đã chuẩn bị schema và seed, nhưng backend chưa đọc SQL Server thật.

Để tạo database mẫu:

1. Mở SQL Server Management Studio hoặc Azure Data Studio.
2. Chạy `database/sqlserver/schema.sql`.
3. Chạy `database/sqlserver/seed.sql`.
4. Kiểm tra connection string trong `appsettings.Development.json`.

## Sẵn sàng thay bằng SQL/RAG

Backend đã tách interface:

```csharp
builder.Services.AddSingleton<IAcademicStore, MockAcademicStore>();
builder.Services.AddSingleton<IChatAnswerService, MockChatService>();
```

Khi có database thật:

```csharp
builder.Services.AddSingleton<IAcademicStore, SqlAcademicStore>();
```

Khi có RAG service thật:

```csharp
builder.Services.AddSingleton<IChatAnswerService, RagChatService>();
```

Frontend không cần đổi endpoint nếu response vẫn giữ `ChatResponse`.
