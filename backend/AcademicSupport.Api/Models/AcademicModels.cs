namespace AcademicSupport.Api.Models;

public sealed record ApiError(string Code, string Message);

public sealed record UserAccount(
    Guid Id,
    string FullName,
    string Email,
    string StudentId,
    DateTimeOffset CreatedAt);

public sealed record AuthUser(
    Guid Id,
    string FullName,
    string Email,
    string StudentId);

public sealed record RegisterRequest(
    string FullName,
    string Email,
    string Password,
    string? StudentId);

public sealed record LoginRequest(
    string Email,
    string Password,
    bool RememberMe);

public sealed record AuthResponse(
    string AccessToken,
    AuthUser User,
    Student Student);

public sealed record Student(
    string Id,
    string FullName,
    string Faculty,
    string Major,
    string ClassCode,
    int IntakeYear,
    string Email);

public sealed record ScheduleItem(
    string Id,
    string StudentId,
    string CourseCode,
    string CourseName,
    string Lecturer,
    string DayOfWeek,
    int StartPeriod,
    int EndPeriod,
    string Room,
    DateOnly StartDate,
    DateOnly EndDate);

public sealed record GradeRecord(
    string Id,
    string StudentId,
    string CourseCode,
    string CourseName,
    int Credits,
    decimal ProcessScore,
    decimal FinalScore,
    decimal TotalScore,
    string LetterGrade,
    string Semester,
    bool IsRetakeNeeded);

public sealed record AcademicSummary(
    string StudentId,
    decimal Gpa10,
    decimal Gpa4,
    int CompletedCredits,
    int DebtCredits,
    IReadOnlyList<string> WarningFlags,
    IReadOnlyList<GradeRecord> RetakeCourses);

public sealed record ChatSession(
    Guid Id,
    string StudentId,
    string Title,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record ChatMessage(
    Guid Id,
    Guid SessionId,
    string Role,
    string Content,
    DateTimeOffset CreatedAt);

public sealed record CreateSessionRequest(string StudentId, string? Title);

public sealed record ChatRequest(
    string StudentId,
    Guid? SessionId,
    string Message);

public sealed record ChatCitation(
    string Source,
    string Title,
    string Excerpt);

public sealed record ChatCard(
    string Type,
    string Title,
    object Data);

public sealed record ChatResponse(
    Guid SessionId,
    ChatMessage UserMessage,
    ChatMessage AssistantMessage,
    IReadOnlyList<ChatCitation> Citations,
    IReadOnlyList<ChatCard> Cards,
    string Status = "answered",
    string Route = "agent",
    bool NeedsClarification = false,
    IReadOnlyList<string>? ClarificationQuestions = null,
    object? Error = null,
    object? Agent = null);
