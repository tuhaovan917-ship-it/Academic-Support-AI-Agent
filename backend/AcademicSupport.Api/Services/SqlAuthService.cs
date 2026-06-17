using System.Security.Cryptography;
using System.Text;
using AcademicSupport.Api.Models;
using Microsoft.Data.SqlClient;

namespace AcademicSupport.Api.Services;

public sealed class SqlAuthService(IConfiguration configuration, IAcademicStore store) : IAuthService
{
    private string ConnectionString =>
        configuration.GetConnectionString("AcademicSupportDb")
        ?? throw new InvalidOperationException("Missing connection string: AcademicSupportDb");

    public AuthResponse Register(RegisterRequest request)
    {
        var fullName = request.FullName.Trim();
        var email = NormalizeEmail(request.Email);
        var password = request.Password.Trim();

        if (string.IsNullOrWhiteSpace(fullName))
        {
            throw new AuthException("invalid_full_name", "Vui lòng nhập họ và tên.");
        }

        if (!IsValidEmail(email))
        {
            throw new AuthException("invalid_email", "Email không hợp lệ.");
        }

        if (password.Length < 6)
        {
            throw new AuthException("weak_password", "Mật khẩu cần có ít nhất 6 ký tự.");
        }

        var studentId = ResolveStudentId(request.StudentId);
        var student = store.GetStudent(studentId)
            ?? throw new AuthException("student_not_found", "Không tìm thấy sinh viên để gắn với tài khoản.");

        if (FindAccountByEmail(email) is not null)
        {
            throw new AuthException("email_exists", "Email này đã được đăng ký.");
        }

        const string sql = """
            INSERT INTO dbo.UserAccounts (StudentId, FullName, Email, PasswordHash)
            OUTPUT INSERTED.UserId, INSERTED.FullName, INSERTED.Email, INSERTED.StudentId
            VALUES (@StudentId, @FullName, @Email, @PasswordHash)
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@StudentId", student.Id);
        command.Parameters.AddWithValue("@FullName", fullName);
        command.Parameters.AddWithValue("@Email", email);
        command.Parameters.AddWithValue("@PasswordHash", HashPassword(password));
        using var reader = command.ExecuteReader();
        if (!reader.Read())
        {
            throw new AuthException("register_failed", "Không tạo được tài khoản.");
        }

        var account = ReadAccount(reader);
        return ToResponse(account, student, rememberMe: true);
    }

    public AuthResponse Login(LoginRequest request)
    {
        var email = NormalizeEmail(request.Email);
        var passwordHash = HashPassword(request.Password.Trim());
        var account = FindAccountByEmail(email);

        if (account is null || account.PasswordHash != passwordHash)
        {
            throw new AuthException("invalid_credentials", "Email hoặc mật khẩu không đúng.");
        }

        var student = store.GetStudent(account.StudentId)
            ?? throw new AuthException("student_not_found", "Tài khoản chưa được gắn với sinh viên hợp lệ.");

        MarkLastLogin(account.Id);
        return ToResponse(account, student, request.RememberMe);
    }

    private string ResolveStudentId(string? requestedStudentId)
    {
        if (!string.IsNullOrWhiteSpace(requestedStudentId))
        {
            return requestedStudentId.Trim().ToUpperInvariant();
        }

        var firstStudent = store.GetStudents().FirstOrDefault();
        if (firstStudent is null)
        {
            throw new AuthException("student_not_found", "Chưa có dữ liệu sinh viên.");
        }

        return firstStudent.Id;
    }

    private AuthResponse ToResponse(AccountRecord account, Student student, bool rememberMe)
    {
        var token = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32));
        SaveAuthSession(account.Id, token, rememberMe ? TimeSpan.FromDays(30) : TimeSpan.FromHours(8));
        return new AuthResponse(
            token,
            new AuthUser(account.Id, account.FullName, account.Email, account.StudentId),
            student);
    }

    private AccountRecord? FindAccountByEmail(string email)
    {
        const string sql = """
            SELECT UserId, FullName, Email, StudentId, PasswordHash
            FROM dbo.UserAccounts
            WHERE Email = @Email
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@Email", email);
        using var reader = command.ExecuteReader();
        return reader.Read() ? ReadAccount(reader) : null;
    }

    private void SaveAuthSession(Guid userId, string token, TimeSpan lifetime)
    {
        const string sql = """
            INSERT INTO dbo.UserSessions (UserId, AccessTokenHash, ExpiresAt)
            VALUES (@UserId, @AccessTokenHash, @ExpiresAt)
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@UserId", userId);
        command.Parameters.AddWithValue("@AccessTokenHash", HashPassword(token));
        command.Parameters.AddWithValue("@ExpiresAt", DateTimeOffset.UtcNow.Add(lifetime));
        command.ExecuteNonQuery();
    }

    private void MarkLastLogin(Guid userId)
    {
        const string sql = """
            UPDATE dbo.UserAccounts
            SET LastLoginAt = SYSDATETIMEOFFSET()
            WHERE UserId = @UserId
            """;

        using var connection = OpenConnection();
        using var command = new SqlCommand(sql, connection);
        command.Parameters.AddWithValue("@UserId", userId);
        command.ExecuteNonQuery();
    }

    private SqlConnection OpenConnection()
    {
        var connection = new SqlConnection(ConnectionString);
        connection.Open();
        return connection;
    }

    private static AccountRecord ReadAccount(SqlDataReader reader) =>
        new(
            reader.GetGuid(0),
            reader.GetString(1),
            reader.GetString(2),
            reader.GetString(3),
            reader.FieldCount > 4 ? reader.GetString(4) : string.Empty);

    private static string NormalizeEmail(string value) => value.Trim().ToLowerInvariant();

    private static bool IsValidEmail(string email) =>
        email.Contains('@', StringComparison.Ordinal) && email.Contains('.', StringComparison.Ordinal);

    private static string HashPassword(string value)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(value));
        return Convert.ToHexString(bytes);
    }

    private sealed record AccountRecord(
        Guid Id,
        string FullName,
        string Email,
        string StudentId,
        string PasswordHash);
}
