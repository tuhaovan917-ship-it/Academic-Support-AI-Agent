using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public sealed class MockChatService(MockAcademicStore store)
{
    public ChatResponse Answer(ChatRequest request)
    {
        var session = store.EnsureSession(request.StudentId, request.SessionId);
        var userMessage = store.AddMessage(session.Id, "user", request.Message.Trim());
        var normalized = request.Message.ToLowerInvariant();

        var cards = new List<ChatCard>();
        var citations = new List<ChatCitation>();
        string answer;

        if (normalized.Contains("lich") || normalized.Contains("thoi khoa bieu") || normalized.Contains("schedule"))
        {
            var schedule = store.GetSchedule(request.StudentId);
            cards.Add(new ChatCard("schedule", "Thoi khoa bieu hoc ky hien tai", schedule));
            answer = schedule.Count == 0
                ? "Hien chua co lich hoc trong du lieu mock cho sinh vien nay."
                : "Minh da lay thoi khoa bieu tu Mock Academic API. Ban xem bang lich hoc ben duoi; khi noi AI Core that vao, buoc nay se duoc goi nhu mot tool.";
        }
        else if (normalized.Contains("diem") || normalized.Contains("gpa") || normalized.Contains("mon no"))
        {
            var summary = store.GetAcademicSummary(request.StudentId);
            cards.Add(new ChatCard("grades", "Diem va tinh trang hoc tap", new
            {
                summary,
                grades = store.GetGrades(request.StudentId)
            }));
            answer = summary is null
                ? "Khong tim thay thong tin diem cho sinh vien nay."
                : $"GPA tam tinh he 10 la {summary.Gpa10}, he 4 la {summary.Gpa4}. So tin chi no la {summary.DebtCredits}.";
        }
        else if (normalized.Contains("dang ky") || normalized.Contains("hoc phan") || normalized.Contains("rut mon"))
        {
            citations.Add(new ChatCitation(
                "HUIT corpus mock",
                "Huong dan dang ky hoc phan",
                "Du lieu nay se duoc thay bang ket qua RAG tu Task 1.2 khi tich hop Python AI Core."));
            answer = "Voi cau hoi ve dang ky hoc phan, ban nen doi chieu quy dinh hoc vu va thong bao phong dao tao. Ban hien dang xem cau tra loi mock; buoc tiep theo la noi Retriever Agent de lay dieu khoan that.";
        }
        else
        {
            citations.Add(new ChatCitation(
                "Fallback policy",
                "Graceful degradation",
                "Neu khong tim thay can cu, chatbot huong dan sinh vien lien he phong dao tao/co van hoc tap."));
            answer = "Minh chua noi AI Core/RAG that o buoc nay, nen day la phan hoi mock an toan. Ban co the hoi thu: 'Cho em xem lich hoc', 'Diem GPA cua em bao nhieu?', hoac 'Em dang ky hoc phan the nao?'.";
        }

        var assistantMessage = store.AddMessage(session.Id, "assistant", answer);
        return new ChatResponse(session.Id, userMessage, assistantMessage, citations, cards);
    }
}
