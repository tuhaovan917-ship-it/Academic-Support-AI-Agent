using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public sealed class MockAcademicStore
{
    private readonly List<Student> _students =
    [
        new(
            "SV001",
            "Nguyen Van An",
            "Cong nghe thong tin",
            "Ky thuat phan mem",
            "13DHTH01",
            2023,
            "an.nguyen@student.huit.edu.vn"),
        new(
            "SV002",
            "Tran Thi Binh",
            "Quan tri kinh doanh",
            "Marketing",
            "13DHQT02",
            2023,
            "binh.tran@student.huit.edu.vn")
    ];

    private readonly List<ScheduleItem> _schedules =
    [
        new("SCH001", "SV001", "IT301", "Lap trinh Web", "ThS. Le Minh", "Thu 2", 1, 3, "B.09.02", new(2026, 6, 1), new(2026, 8, 30)),
        new("SCH002", "SV001", "IT315", "Co so du lieu", "TS. Pham Hoa", "Thu 4", 4, 6, "C.05.01", new(2026, 6, 1), new(2026, 8, 30)),
        new("SCH003", "SV001", "ENG201", "Tieng Anh 3", "ThS. Nguyen Lan", "Thu 6", 7, 9, "A.03.04", new(2026, 6, 1), new(2026, 8, 30)),
        new("SCH004", "SV002", "MKT210", "Hanh vi khach hang", "ThS. Vo Khanh", "Thu 3", 1, 3, "D.02.06", new(2026, 6, 1), new(2026, 8, 30)),
        new("SCH005", "SV002", "BUS220", "Quan tri hoc", "TS. Do My", "Thu 5", 4, 6, "B.04.03", new(2026, 6, 1), new(2026, 8, 30))
    ];

    private readonly List<GradeRecord> _grades =
    [
        new("GR001", "SV001", "IT101", "Nhap mon lap trinh", 3, 7.5m, 8.0m, 7.8m, "B+", "2025-2026-HK1", false),
        new("GR002", "SV001", "MATH101", "Giai tich", 3, 4.5m, 3.8m, 4.1m, "F", "2025-2026-HK1", true),
        new("GR003", "SV001", "ENG102", "Tieng Anh 2", 2, 6.5m, 6.0m, 6.2m, "C+", "2025-2026-HK1", false),
        new("GR004", "SV002", "BUS101", "Kinh te vi mo", 3, 8.0m, 7.0m, 7.4m, "B", "2025-2026-HK1", false),
        new("GR005", "SV002", "MKT101", "Marketing can ban", 3, 8.5m, 8.2m, 8.3m, "A", "2025-2026-HK1", false)
    ];

    private readonly List<ChatSession> _sessions = [];
    private readonly List<ChatMessage> _messages = [];

    public IReadOnlyList<Student> GetStudents() => _students;

    public Student? GetStudent(string studentId) =>
        _students.FirstOrDefault(student => student.Id.Equals(studentId, StringComparison.OrdinalIgnoreCase));

    public IReadOnlyList<ScheduleItem> GetSchedule(string studentId) =>
        _schedules
            .Where(item => item.StudentId.Equals(studentId, StringComparison.OrdinalIgnoreCase))
            .OrderBy(item => item.DayOfWeek)
            .ThenBy(item => item.StartPeriod)
            .ToList();

    public IReadOnlyList<GradeRecord> GetGrades(string studentId) =>
        _grades
            .Where(grade => grade.StudentId.Equals(studentId, StringComparison.OrdinalIgnoreCase))
            .OrderBy(grade => grade.Semester)
            .ThenBy(grade => grade.CourseCode)
            .ToList();

    public AcademicSummary? GetAcademicSummary(string studentId)
    {
        if (GetStudent(studentId) is null)
        {
            return null;
        }

        var grades = GetGrades(studentId);
        var completedGrades = grades.Where(grade => !grade.IsRetakeNeeded).ToList();
        var totalCredits = grades.Sum(grade => grade.Credits);
        var weightedScore = totalCredits == 0
            ? 0
            : grades.Sum(grade => grade.TotalScore * grade.Credits) / totalCredits;
        var retakeCourses = grades.Where(grade => grade.IsRetakeNeeded).ToList();

        var warnings = new List<string>();
        if (retakeCourses.Count > 0)
        {
            warnings.Add("Co mon can hoc lai/cai thien.");
        }

        if (weightedScore < 5)
        {
            warnings.Add("GPA he 10 dang thap, can gap co van hoc tap.");
        }

        return new AcademicSummary(
            studentId,
            Math.Round(weightedScore, 2),
            Math.Round(weightedScore / 10 * 4, 2),
            completedGrades.Sum(grade => grade.Credits),
            retakeCourses.Sum(grade => grade.Credits),
            warnings,
            retakeCourses);
    }

    public ChatSession CreateSession(string studentId, string? title)
    {
        var now = DateTimeOffset.UtcNow;
        var session = new ChatSession(
            Guid.NewGuid(),
            studentId,
            string.IsNullOrWhiteSpace(title) ? "Hoi dap hoc vu" : title.Trim(),
            now,
            now);
        _sessions.Add(session);
        return session;
    }

    public IReadOnlyList<ChatSession> GetSessions(string? studentId)
    {
        var query = _sessions.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(studentId))
        {
            query = query.Where(session => session.StudentId.Equals(studentId, StringComparison.OrdinalIgnoreCase));
        }

        return query.OrderByDescending(session => session.UpdatedAt).ToList();
    }

    public IReadOnlyList<ChatMessage> GetMessages(Guid sessionId) =>
        _messages
            .Where(message => message.SessionId == sessionId)
            .OrderBy(message => message.CreatedAt)
            .ToList();

    public ChatSession EnsureSession(string studentId, Guid? sessionId)
    {
        if (sessionId is not null)
        {
            var existing = _sessions.FirstOrDefault(session => session.Id == sessionId.Value);
            if (existing is not null)
            {
                return existing;
            }
        }

        return CreateSession(studentId, "Hoi dap hoc vu");
    }

    public ChatMessage AddMessage(Guid sessionId, string role, string content)
    {
        var message = new ChatMessage(Guid.NewGuid(), sessionId, role, content, DateTimeOffset.UtcNow);
        _messages.Add(message);

        var index = _sessions.FindIndex(session => session.Id == sessionId);
        if (index >= 0)
        {
            var session = _sessions[index];
            _sessions[index] = session with { UpdatedAt = DateTimeOffset.UtcNow };
        }

        return message;
    }
}
