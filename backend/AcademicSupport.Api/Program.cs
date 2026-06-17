using System.Diagnostics;
using AcademicSupport.Api.Models;
using AcademicSupport.Api.Services;
using Microsoft.Data.SqlClient;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new()
    {
        Title = "HUIT Academic Support API",
        Version = "v1",
        Description = ".NET API Gateway for Nexus AI, Python AgentService, RAG, and student academic tools."
    });
});

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

builder.Services.AddSingleton<IAcademicStore, SqlAcademicStore>();
builder.Services.AddSingleton<IChatAnswerService, PythonAgentChatService>();
builder.Services.AddSingleton<IAuthService, SqlAuthService>();

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI(options =>
{
    options.SwaggerEndpoint("/swagger/v1/swagger.json", "HUIT Academic Support API v1");
    options.RoutePrefix = "swagger";
    options.DocumentTitle = "HUIT Academic Support API";
});

app.UseCors("Frontend");

if (app.Environment.IsDevelopment() && app.Configuration.GetValue("Swagger:AutoOpen", true))
{
    app.Lifetime.ApplicationStarted.Register(() =>
    {
        try
        {
            var baseUrl = app.Urls.FirstOrDefault(url => url.StartsWith("http://", StringComparison.OrdinalIgnoreCase))
                ?? app.Urls.FirstOrDefault()
                ?? "http://localhost:5098";
            Process.Start(new ProcessStartInfo
            {
                FileName = $"{baseUrl.TrimEnd('/')}/swagger",
                UseShellExecute = true
            });
        }
        catch
        {
            // Swagger is still available even if the browser cannot be opened automatically.
        }
    });
}

app.MapGet("/api/health", () => Results.Ok(new
{
    service = "AcademicSupport.Api",
    status = "ok",
    mode = "agent",
    timestamp = DateTimeOffset.UtcNow
}));

app.MapPost("/api/auth/register", (RegisterRequest request, IAuthService authService) =>
{
    try
    {
        return Results.Created("/api/auth/session", authService.Register(request));
    }
    catch (AuthException exception)
    {
        return Results.BadRequest(new ApiError(exception.Code, exception.Message));
    }
});

app.MapPost("/api/auth/login", (LoginRequest request, IAuthService authService) =>
{
    try
    {
        return Results.Ok(authService.Login(request));
    }
    catch (AuthException exception)
    {
        return Results.BadRequest(new ApiError(exception.Code, exception.Message));
    }
});

app.MapGet("/api/config/database", (IConfiguration configuration) =>
{
    var connectionString = configuration.GetConnectionString("AcademicSupportDb");
    if (string.IsNullOrWhiteSpace(connectionString))
    {
        return Results.Ok(new
        {
            name = "AcademicSupportDb",
            configured = false,
            connected = false,
            message = "Chưa cấu hình connection string AcademicSupportDb."
        });
    }

    try
    {
        using var connection = new SqlConnection(connectionString);
        connection.Open();
        return Results.Ok(new
        {
            name = "AcademicSupportDb",
            configured = true,
            connected = true,
            database = connection.Database,
            dataSource = connection.DataSource
        });
    }
    catch (Exception exception)
    {
        return Results.Ok(new
        {
            name = "AcademicSupportDb",
            configured = true,
            connected = false,
            message = exception.Message
        });
    }
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

app.MapGet("/api/students/{studentId}/profile", (string studentId, IAcademicStore store) =>
{
    var student = store.GetStudent(studentId);
    if (student is null)
    {
        return Results.NotFound(new
        {
            found = false,
            student_id = studentId.ToUpperInvariant(),
            error = "student_not_found"
        });
    }

    return Results.Ok(new
    {
        found = true,
        student_id = student.Id,
        full_name = student.FullName,
        major = student.Major,
        faculty = student.Faculty,
        class_code = student.ClassCode,
        email = student.Email,
        certificates = new
        {
            foreign_language = student.Id != "SV005",
            gdtc = true,
            gdqp = student.Id != "SV005"
        },
        disciplinary_warning = false
    });
});

app.MapGet("/api/students/{studentId}/schedule", (string studentId, IAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new
        {
            found = false,
            student_id = studentId.ToUpperInvariant(),
            error = "student_not_found"
        });
    }

    return Results.Ok(new
    {
        found = true,
        student_id = studentId.ToUpperInvariant(),
        schedule = store.GetSchedule(studentId).Select(item => new
        {
            semester = "2025-2026-2",
            day = item.DayOfWeek,
            time = $"Tiết {item.StartPeriod}-{item.EndPeriod}",
            course_code = item.CourseCode,
            course_name = item.CourseName,
            room = item.Room,
            lecturer = item.Lecturer
        })
    });
});

app.MapGet("/api/students/{studentId}/grades", (string studentId, IAcademicStore store) =>
{
    if (store.GetStudent(studentId) is null)
    {
        return Results.NotFound(new
        {
            found = false,
            student_id = studentId.ToUpperInvariant(),
            error = "student_not_found"
        });
    }

    var grades = store.GetGrades(studentId);
    var summary = store.GetAcademicSummary(studentId);
    var totalCredits = grades.Sum(grade => grade.Credits);
    var retakenCredits = grades.Where(grade => grade.IsRetakeNeeded).Sum(grade => grade.Credits);
    return Results.Ok(new
    {
        found = true,
        student_id = studentId.ToUpperInvariant(),
        cumulative_gpa = summary?.Gpa4 ?? 0,
        total_credits = totalCredits,
        retaken_credits = retakenCredits,
        retake_ratio = totalCredits == 0 ? 0 : Math.Round((decimal)retakenCredits / totalCredits, 3),
        courses = grades.Select(grade => new
        {
            semester = grade.Semester,
            course_code = grade.CourseCode,
            course_name = grade.CourseName,
            credits = grade.Credits,
            total_score = grade.TotalScore,
            letter_grade = grade.LetterGrade,
            is_retake_needed = grade.IsRetakeNeeded
        }),
        failed_courses = grades.Where(grade => grade.IsRetakeNeeded).Select(grade => new
        {
            course_code = grade.CourseCode,
            course_name = grade.CourseName,
            credits = grade.Credits,
            letter_grade = grade.LetterGrade
        })
    });
});

app.MapGet("/api/students/{studentId}/graduation-snapshot", (string studentId, IAcademicStore store) =>
{
    var student = store.GetStudent(studentId);
    if (student is null)
    {
        return Results.NotFound(new
        {
            found = false,
            student_id = studentId.ToUpperInvariant(),
            error = "student_not_found"
        });
    }

    var grades = store.GetGrades(studentId);
    var summary = store.GetAcademicSummary(studentId);
    var totalCredits = grades.Sum(grade => grade.Credits);
    var retakenCredits = grades.Where(grade => grade.IsRetakeNeeded).Sum(grade => grade.Credits);
    var missingCertificates = student.Id == "SV005"
        ? new[] { "foreign_language", "gdqp" }
        : [];
    var warnings = new List<string>();
    if (totalCredits > 0 && (decimal)retakenCredits / totalCredits > 0.05m)
    {
        warnings.Add("retake_ratio_over_5_percent");
    }

    return Results.Ok(new
    {
        found = true,
        student_id = student.Id,
        full_name = student.FullName,
        major = student.Major,
        cumulative_gpa = summary?.Gpa4 ?? 0,
        total_credits = totalCredits,
        retaken_credits = retakenCredits,
        retake_ratio = totalCredits == 0 ? 0 : Math.Round((decimal)retakenCredits / totalCredits, 3),
        failed_courses = grades.Where(grade => grade.IsRetakeNeeded).Select(grade => new
        {
            course_code = grade.CourseCode,
            course_name = grade.CourseName,
            credits = grade.Credits,
            letter_grade = grade.LetterGrade
        }),
        missing_certificates = missingCertificates,
        eligible_for_graduation = retakenCredits == 0 && missingCertificates.Length == 0,
        warnings
    });
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
