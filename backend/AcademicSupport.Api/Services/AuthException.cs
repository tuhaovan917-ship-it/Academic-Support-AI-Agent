namespace AcademicSupport.Api.Services;

public sealed class AuthException(string code, string message) : Exception(message)
{
    public string Code { get; } = code;
}
