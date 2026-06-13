using AcademicSupport.Api.Models;
using AcademicSupport.Api.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy(
        "Frontend",
        policy => policy
            .WithOrigins(
                "http://localhost:4200",
                "http://127.0.0.1:4200",
                "http://localhost:5173",
                "http://127.0.0.1:5173")
            .AllowAnyHeader()
            .AllowAnyMethod());
});

builder.Services.AddSingleton<MockAcademicStore>();
builder.Services.AddSingleton<MockChatService>();

var app = builder.Build();

app.UseCors("Frontend");

app.MapGet("/api/health", () => Results.Ok(new
{
    service = "AcademicSupport.Api",
    status = "ok",
    mode = "mock",
    timestamp = DateTimeOffset.UtcNow
}));

app.MapGet("/api/students", (MockAcademicStore store) =>
    Results.Ok(store.GetStudents()));

app.MapGet("/api/students/{studentId}", (string studentId, MockAcademicStore store) =>
{
    var student = store.GetStudent(studentId);
    return student is null
        ? Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."))
        : Results.Ok(student);
});

app.MapGet("/api/students/{studentId}/schedule", (string studentId, MockAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."));
    }

    return Results.Ok(store.GetSchedule(studentId));
});

app.MapGet("/api/students/{studentId}/grades", (string studentId, MockAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."));
    }

    return Results.Ok(store.GetGrades(studentId));
});

app.MapGet("/api/students/{studentId}/academic-summary", (string studentId, MockAcademicStore store) =>
{
    var summary = store.GetAcademicSummary(studentId);
    return summary is null
        ? Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."))
        : Results.Ok(summary);
});

app.MapPost("/api/chat/sessions", (CreateSessionRequest request, MockAcademicStore store) =>
{
    if (store.GetStudent(request.StudentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."));
    }

    return Results.Created(
        $"/api/chat/sessions/{request.StudentId}",
        store.CreateSession(request.StudentId, request.Title));
});

app.MapGet("/api/chat/sessions", (string? studentId, MockAcademicStore store) =>
    Results.Ok(store.GetSessions(studentId)));

app.MapGet("/api/chat/sessions/{sessionId:guid}/messages", (Guid sessionId, MockAcademicStore store) =>
    Results.Ok(store.GetMessages(sessionId)));

app.MapPost("/api/chat", (ChatRequest request, MockAcademicStore store, MockChatService chatService) =>
{
    if (string.IsNullOrWhiteSpace(request.Message))
    {
        return Results.BadRequest(new ApiError("empty_message", "Noi dung cau hoi khong duoc de trong."));
    }

    if (store.GetStudent(request.StudentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Khong tim thay sinh vien."));
    }

    var response = chatService.Answer(request);
    return Results.Ok(response);
});

app.Run();
