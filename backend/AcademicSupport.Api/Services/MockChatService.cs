using System.Globalization;
using System.Text;
using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public sealed class MockChatService(IAcademicStore store) : IChatAnswerService
{
    public Task<ChatResponse> AnswerAsync(
        ChatRequest request,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var session = store.EnsureSession(request.StudentId, request.SessionId, request.Message.Trim());
        var userMessage = store.AddMessage(session.Id, "user", request.Message.Trim());
        var normalized = NormalizeSearchText(request.Message);

        var cards = new List<ChatCard>();
        var citations = new List<ChatCitation>();
        string answer;

        if (ContainsAny(normalized, "ten sinh vien", "ten cua em", "em ten gi", "ho ten", "thong tin sinh vien", "ma sinh vien", "email", "lop", "nganh", "khoa", "toi la ai", "minh la ai", "profile"))
        {
            var student = store.GetStudent(request.StudentId);
            cards.Add(new ChatCard("student", "Thông tin sinh viên", student!));
            answer = student is null
                ? "Không tìm thấy thông tin sinh viên."
                : $"Thông tin của bạn: {student.FullName} ({student.Id}), lớp {student.ClassCode}, ngành {student.Major}, khoa {student.Faculty}, khóa {student.IntakeYear}. Email: {student.Email}.";
        }
        else if (ContainsAny(normalized, "lich", "thoi khoa bieu", "schedule"))
        {
            var schedule = store.GetSchedule(request.StudentId);
            cards.Add(new ChatCard("schedule", "Thời khóa biểu học kỳ hiện tại", schedule));
            answer = schedule.Count == 0
                ? "Hiện chưa có lịch học trong dữ liệu cho sinh viên này."
                : "Mình đã lấy thời khóa biểu từ API học vụ. Bạn xem bảng lịch học bên dưới; khi nối AI Core thật, bước này sẽ được gọi như một tool.";
        }
        else if (ContainsAny(normalized, "diem", "gpa", "mon no", "hoc lai"))
        {
            var summary = store.GetAcademicSummary(request.StudentId);
            cards.Add(new ChatCard("grades", "Điểm và tình trạng học tập", new
            {
                summary,
                grades = store.GetGrades(request.StudentId)
            }));
            answer = summary is null
                ? "Không tìm thấy thông tin điểm cho sinh viên này."
                : $"GPA tạm tính hệ 10 là {summary.Gpa10}, hệ 4 là {summary.Gpa4}. Số tín chỉ nợ là {summary.DebtCredits}.";
        }
        else if (ContainsAny(normalized, "dang ky", "hoc phan", "rut mon"))
        {
            citations.Add(new ChatCitation(
                "HUIT corpus demo",
                "Hướng dẫn đăng ký học phần",
                "Dữ liệu này sẽ được thay bằng kết quả RAG từ Task 1.2 khi tích hợp Python AI Core."));
            answer = "Với câu hỏi về đăng ký học phần, bạn nên đối chiếu quy định học vụ và thông báo của phòng đào tạo. Đây là câu trả lời demo; bước tiếp theo là nối Retriever Agent để lấy điều khoản thật.";
        }
        else
        {
            citations.Add(new ChatCitation(
                "Fallback policy",
                "Cơ chế trả lời an toàn",
                "Nếu không tìm thấy căn cứ, chatbot hướng dẫn sinh viên liên hệ phòng đào tạo hoặc cố vấn học tập."));
            answer = "Mình chưa nối AI Core/RAG thật ở bước này, nên đây là phản hồi demo an toàn. Bạn có thể hỏi thử: “Cho em xem lịch học”, “Điểm GPA của em bao nhiêu?”, hoặc “Em đăng ký học phần thế nào?”.";
        }

        var assistantMessage = store.AddMessage(session.Id, "assistant", answer);
        return Task.FromResult(new ChatResponse(session.Id, userMessage, assistantMessage, citations, cards));
    }

    private static bool ContainsAny(string text, params string[] keywords) =>
        keywords.Any(text.Contains);

    private static string NormalizeSearchText(string value)
    {
        var normalized = value.ToLowerInvariant().Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder(normalized.Length);

        foreach (var character in normalized)
        {
            var category = CharUnicodeInfo.GetUnicodeCategory(character);
            if (category != UnicodeCategory.NonSpacingMark)
            {
                builder.Append(character == 'đ' ? 'd' : character);
            }
        }

        return builder.ToString().Normalize(NormalizationForm.FormC);
    }
}
