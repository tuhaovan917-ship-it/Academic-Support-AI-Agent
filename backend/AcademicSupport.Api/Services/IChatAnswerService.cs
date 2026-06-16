using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public interface IChatAnswerService
{
    Task<ChatResponse> AnswerAsync(
        ChatRequest request,
        CancellationToken cancellationToken = default);
}
