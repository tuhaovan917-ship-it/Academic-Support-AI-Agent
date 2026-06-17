using AcademicSupport.Api.Models;
using Microsoft.Data.SqlClient;

namespace AcademicSupport.Api.Services;

public sealed class SqlAcademicStore(IConfiguration configuration) : IAcademicStore
{
    private string ConnectionString =>
        configuration.GetConnectionString("AcademicSupportDb")
        ?? throw new InvalidOperationException("Missing connection string: AcademicSupportDb");

    public IReadOnlyList<Student> GetStudents()
    {
        const string sql = """
            SELECT StudentId, FullName, Faculty, Major, ClassCode, IntakeYear, Email
            FROM dbo.Students
            ORDER BY StudentId
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        using var reader = command.ExecuteReader();
        var students = new List<Student>();
        while (reader.Read())
        {
            students.Add(ReadStudent(reader));
        }

        return students;
    }

    public Student? GetStudent(string studentId)
    {
        const string sql = """
            SELECT StudentId, FullName, Faculty, Major, ClassCode, IntakeYear, Email
            FROM dbo.Students
            WHERE StudentId = @StudentId
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@StudentId", studentId.Trim().ToUpperInvariant());
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadStudent(reader) : null;
    }

    public IReadOnlyList<ScheduleItem> GetSchedule(string studentId)
    {
        const string sql = """
            SELECT
                CONVERT(nvarchar(36), s.ScheduleId) AS ScheduleId,
                s.StudentId,
                s.CourseCode,
                c.CourseName,
                s.Lecturer,
                s.DayOfWeek,
                s.StartPeriod,
                s.EndPeriod,
                s.Room,
                s.StartDate,
                s.EndDate
            FROM dbo.Schedules s
            INNER JOIN dbo.Courses c ON c.CourseCode = s.CourseCode
            WHERE s.StudentId = @StudentId
            ORDER BY s.DayOfWeek, s.StartPeriod
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@StudentId", studentId.Trim().ToUpperInvariant());
        using var reader = command.ExecuteReader();
        var schedule = new List<ScheduleItem>();
        while (reader.Read())
        {
            schedule.Add(new ScheduleItem(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetString(3),
                reader.GetString(4),
                reader.GetString(5),
                reader.GetInt32(6),
                reader.GetInt32(7),
                reader.GetString(8),
                DateOnly.FromDateTime(reader.GetDateTime(9)),
                DateOnly.FromDateTime(reader.GetDateTime(10))));
        }

        return schedule;
    }

    public IReadOnlyList<GradeRecord> GetGrades(string studentId)
    {
        const string sql = """
            SELECT
                CONVERT(nvarchar(36), g.GradeId) AS GradeId,
                g.StudentId,
                g.CourseCode,
                c.CourseName,
                c.Credits,
                g.ProcessScore,
                g.FinalScore,
                g.TotalScore,
                g.LetterGrade,
                g.Semester,
                g.IsRetakeNeeded
            FROM dbo.Grades g
            INNER JOIN dbo.Courses c ON c.CourseCode = g.CourseCode
            WHERE g.StudentId = @StudentId
            ORDER BY g.Semester, g.CourseCode
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@StudentId", studentId.Trim().ToUpperInvariant());
        using var reader = command.ExecuteReader();
        var grades = new List<GradeRecord>();
        while (reader.Read())
        {
            grades.Add(new GradeRecord(
                reader.GetString(0),
                reader.GetString(1),
                reader.GetString(2),
                reader.GetString(3),
                reader.GetInt32(4),
                reader.GetDecimal(5),
                reader.GetDecimal(6),
                reader.GetDecimal(7),
                reader.GetString(8),
                reader.GetString(9),
                reader.GetBoolean(10)));
        }

        return grades;
    }

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
            warnings.Add("Có môn cần học lại/cải thiện.");
        }

        if (weightedScore < 5)
        {
            warnings.Add("GPA hệ 10 đang thấp, cần gặp cố vấn học tập.");
        }

        if (retakeCourses.Sum(grade => grade.Credits) >= 6)
        {
            warnings.Add("Số tín chỉ nợ cao, nên lập kế hoạch học lại trước khi xét tốt nghiệp.");
        }

        return new AcademicSummary(
            studentId.Trim().ToUpperInvariant(),
            Math.Round(weightedScore, 2),
            Math.Round(weightedScore / 10 * 4, 2),
            completedGrades.Sum(grade => grade.Credits),
            retakeCourses.Sum(grade => grade.Credits),
            warnings,
            retakeCourses);
    }

    public ChatSession CreateSession(string studentId, string? title)
    {
        const string sql = """
            INSERT INTO dbo.ChatSessions (StudentId, Title)
            OUTPUT INSERTED.SessionId, INSERTED.StudentId, INSERTED.Title, INSERTED.CreatedAt, INSERTED.UpdatedAt
            VALUES (@StudentId, @Title)
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@StudentId", studentId.Trim().ToUpperInvariant());
        command.Parameters.AddWithValue("@Title", NormalizeSessionTitle(title));
        using var reader = command.ExecuteReader();
        if (!reader.Read())
        {
            throw new InvalidOperationException("Could not create chat session.");
        }

        return ReadChatSession(reader);
    }

    public IReadOnlyList<ChatSession> GetSessions(string? studentId)
    {
        var sql = """
            SELECT SessionId, StudentId, Title, CreatedAt, UpdatedAt
            FROM dbo.ChatSessions
            """;
        if (!string.IsNullOrWhiteSpace(studentId))
        {
            sql += " WHERE StudentId = @StudentId";
        }

        sql += " ORDER BY UpdatedAt DESC";

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        if (!string.IsNullOrWhiteSpace(studentId))
        {
            command.Parameters.AddWithValue("@StudentId", studentId.Trim().ToUpperInvariant());
        }

        using var reader = command.ExecuteReader();
        var sessions = new List<ChatSession>();
        while (reader.Read())
        {
            sessions.Add(ReadChatSession(reader));
        }

        return sessions;
    }

    public IReadOnlyList<ChatMessage> GetMessages(Guid sessionId)
    {
        const string sql = """
            SELECT MessageId, SessionId, Role, Content, CreatedAt
            FROM dbo.ChatMessages
            WHERE SessionId = @SessionId
            ORDER BY CreatedAt
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@SessionId", sessionId);
        using var reader = command.ExecuteReader();
        var messages = new List<ChatMessage>();
        while (reader.Read())
        {
            messages.Add(ReadChatMessage(reader));
        }

        return messages;
    }

    public ChatSession EnsureSession(string studentId, Guid? sessionId, string? fallbackTitle = null)
    {
        if (sessionId is not null)
        {
            var existing = GetSession(sessionId.Value);
            if (existing is not null)
            {
                return existing;
            }
        }

        return CreateSession(studentId, fallbackTitle);
    }

    public ChatMessage AddMessage(Guid sessionId, string role, string content)
    {
        const string insertSql = """
            INSERT INTO dbo.ChatMessages (SessionId, Role, Content)
            OUTPUT INSERTED.MessageId, INSERTED.SessionId, INSERTED.Role, INSERTED.Content, INSERTED.CreatedAt
            VALUES (@SessionId, @Role, @Content)
            """;
        const string updateSessionSql = """
            UPDATE dbo.ChatSessions
            SET UpdatedAt = SYSDATETIMEOFFSET()
            WHERE SessionId = @SessionId
            """;

        using var connection = OpenConnection();
        using var transaction = connection.BeginTransaction();
        try
        {
            ChatMessage message;
            using (var insertCommand = new SqlCommand(insertSql, connection, transaction))
            {
                insertCommand.Parameters.AddWithValue("@SessionId", sessionId);
                insertCommand.Parameters.AddWithValue("@Role", role);
                insertCommand.Parameters.AddWithValue("@Content", content);
                using var reader = insertCommand.ExecuteReader();
                if (!reader.Read())
                {
                    throw new InvalidOperationException("Could not add chat message.");
                }

                message = ReadChatMessage(reader);
            }

            using (var updateCommand = new SqlCommand(updateSessionSql, connection, transaction))
            {
                updateCommand.Parameters.AddWithValue("@SessionId", sessionId);
                updateCommand.ExecuteNonQuery();
            }

            transaction.Commit();
            return message;
        }
        catch
        {
            transaction.Rollback();
            throw;
        }
    }

    private ChatSession? GetSession(Guid sessionId)
    {
        const string sql = """
            SELECT SessionId, StudentId, Title, CreatedAt, UpdatedAt
            FROM dbo.ChatSessions
            WHERE SessionId = @SessionId
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@SessionId", sessionId);
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadChatSession(reader) : null;
    }

    private SqlConnection OpenConnection()
    {
        var connection = new SqlConnection(ConnectionString);
        connection.Open();
        return connection;
    }

    private static Student ReadStudent(SqlDataReader reader) =>
        new(
            reader.GetString(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.GetString(4),
            reader.GetInt32(5),
            reader.GetString(6));

    private static ChatSession ReadChatSession(SqlDataReader reader) =>
        new(
            reader.GetGuid(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetFieldValue<DateTimeOffset>(3),
            reader.GetFieldValue<DateTimeOffset>(4));

    private static ChatMessage ReadChatMessage(SqlDataReader reader) =>
        new(
            reader.GetGuid(0),
            reader.GetGuid(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.GetFieldValue<DateTimeOffset>(4));

    private static string NormalizeSessionTitle(string? title)
    {
        const int maxLength = 60;
        var cleanTitle = string.Join(
            " ",
            (title ?? string.Empty).Trim().Split(' ', StringSplitOptions.RemoveEmptyEntries));

        if (string.IsNullOrWhiteSpace(cleanTitle))
        {
            return "Hội thoại mới";
        }

        return cleanTitle.Length <= maxLength
            ? cleanTitle
            : cleanTitle[..maxLength].TrimEnd() + "...";
    }
}
