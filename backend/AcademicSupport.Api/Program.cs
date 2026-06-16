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

builder.Services.AddSingleton<IAcademicStore, MockAcademicStore>();
builder.Services.AddSingleton<IChatAnswerService, MockChatService>();

var app = builder.Build();

app.UseCors("Frontend");

app.MapGet("/api/health", () => Results.Ok(new
{
    service = "AcademicSupport.Api",
    status = "ok",
    mode = "mock",
    timestamp = DateTimeOffset.UtcNow
}));

app.MapGet("/api/config/database", (IConfiguration configuration) =>
{
    var connectionString = configuration.GetConnectionString("AcademicSupportDb");
    return Results.Ok(new
    {
        name = "AcademicSupportDb",
        configured = !string.IsNullOrWhiteSpace(connectionString)
    });
});

app.MapGet("/api/students", (IAcademicStore store) =>
    Results.Ok(store.GetStudents()));

app.MapGet("/api/students/{studentId}", (string studentId, IAcademicStore store) =>
{
    var student = store.GetStudent(studentId);
    return student is null
        ? Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."))
        : Results.Ok(student);
});

app.MapGet("/api/students/{studentId}/schedule", (string studentId, IAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."));
    }

    return Results.Ok(store.GetSchedule(studentId));
});

app.MapGet("/api/students/{studentId}/grades", (string studentId, IAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."));
    }

    return Results.Ok(store.GetGrades(studentId));
});

app.MapGet("/api/students/{studentId}/academic-summary", (string studentId, IAcademicStore store) =>
{
    var summary = store.GetAcademicSummary(studentId);
    return summary is null
        ? Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."))
        : Results.Ok(summary);
});

app.MapPost("/api/chat/sessions", (CreateSessionRequest request, IAcademicStore store) =>
{
    if (store.GetStudent(request.StudentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."));
    }

    return Results.Created(
        $"/api/chat/sessions/{request.StudentId}",
        store.CreateSession(request.StudentId, request.Title));
});

app.MapGet("/api/chat/sessions", (string? studentId, IAcademicStore store) =>
    Results.Ok(store.GetSessions(studentId)));

app.MapGet("/api/chat/sessions/{sessionId:guid}/messages", (Guid sessionId, IAcademicStore store) =>
    Results.Ok(store.GetMessages(sessionId)));

app.MapPost("/api/chat", async Task<IResult> (
    ChatRequest request,
    IAcademicStore store,
    IChatAnswerService chatService,
    CancellationToken cancellationToken) =>
{
    if (string.IsNullOrWhiteSpace(request.Message))
    {
        return Results.BadRequest(new ApiError("empty_message", "Nội dung câu hỏi không được để trống."));
    }

    if (store.GetStudent(request.StudentId) is null)
    {
        return Results.NotFound(new ApiError("student_not_found", "Không tìm thấy sinh viên."));
    }

    var response = await chatService.AnswerAsync(request, cancellationToken);
    return Results.Ok(response);
});

app.Run();
