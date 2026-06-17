using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public interface IAcademicStore
{
    IReadOnlyList<Student> GetStudents();

    Student? GetStudent(string studentId);

    IReadOnlyList<ScheduleItem> GetSchedule(string studentId);

    IReadOnlyList<GradeRecord> GetGrades(string studentId);

    AcademicSummary? GetAcademicSummary(string studentId);

    ChatSession CreateSession(string studentId, string? title);

    IReadOnlyList<ChatSession> GetSessions(string? studentId);

    IReadOnlyList<ChatMessage> GetMessages(Guid sessionId);

    ChatSession EnsureSession(string studentId, Guid? sessionId, string? fallbackTitle = null);

    ChatMessage AddMessage(Guid sessionId, string role, string content);
}
