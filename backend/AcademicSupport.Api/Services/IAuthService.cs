using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public interface IAuthService
{
    AuthResponse Register(RegisterRequest request);

    AuthResponse Login(LoginRequest request);
}
