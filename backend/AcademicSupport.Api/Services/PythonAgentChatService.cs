using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using AcademicSupport.Api.Models;

namespace AcademicSupport.Api.Services;

public sealed class PythonAgentChatService(
    IAcademicStore store,
    IConfiguration configuration,
    ILogger<PythonAgentChatService> logger) : IChatAnswerService
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true
    };

    public async Task<ChatResponse> AnswerAsync(
        ChatRequest request,
        CancellationToken cancellationToken = default)
    {
        var session = store.EnsureSession(request.StudentId, request.SessionId, request.Message.Trim());
        var userMessage = store.AddMessage(session.Id, "user", request.Message.Trim());

        try
        {
            var agent = await RunPythonAgentAsync(request, session.Id, cancellationToken);
            var cards = BuildCards(agent);
            var citations = BuildCitations(agent);
            var answer = string.IsNullOrWhiteSpace(agent.Answer)
                ? "AI Core chưa trả về nội dung trả lời."
                : agent.Answer;

            if (agent.NeedsClarification && agent.ClarificationQuestions.Count > 0)
            {
                answer = $"{answer}\n\n{string.Join("\n", agent.ClarificationQuestions.Select(item => $"- {item}"))}";
            }

            var assistantMessage = store.AddMessage(session.Id, "assistant", answer);
            return new ChatResponse(
                session.Id,
                userMessage,
                assistantMessage,
                citations,
                cards,
                agent.Status,
                agent.Route,
                agent.NeedsClarification,
                agent.ClarificationQuestions,
                agent.Error,
                agent.Raw);
        }
        catch (Exception exception)
        {
            logger.LogError(exception, "Python AI Core failed.");
            var error = new Dictionary<string, object?>
            {
                ["code"] = "ERR_AI_CORE_UNAVAILABLE",
                ["message"] = "AI Core/RAG chưa xử lý được yêu cầu.",
                ["details"] = exception.Message
            };
            var answer = "AI Core/RAG đang gặp lỗi khi xử lý yêu cầu. Hãy kiểm tra Python environment, huit_db và log backend rồi thử lại.";
            var assistantMessage = store.AddMessage(session.Id, "assistant", answer);
            return new ChatResponse(
                session.Id,
                userMessage,
                assistantMessage,
                [],
                [],
                "fallback",
                "ai_core_error",
                false,
                [],
                error,
                error);
        }
    }

    private async Task<AgentBridgeResponse> RunPythonAgentAsync(
        ChatRequest request,
        Guid sessionId,
        CancellationToken cancellationToken)
    {
        var projectRoot = ResolveProjectRoot();
        var python = ResolvePythonExecutable(projectRoot);
        var script = Path.Combine(projectRoot, "scripts", "run_agent_service_cli.py");

        if (!File.Exists(script))
        {
            throw new FileNotFoundException("Không tìm thấy script Python AgentService.", script);
        }

        using var process = new Process();
        process.StartInfo = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = projectRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            UseShellExecute = false
        };

        process.StartInfo.ArgumentList.Add("-X");
        process.StartInfo.ArgumentList.Add("utf8");
        process.StartInfo.ArgumentList.Add(script);
        process.StartInfo.ArgumentList.Add(request.Message.Trim());
        process.StartInfo.ArgumentList.Add("--student-id");
        process.StartInfo.ArgumentList.Add(request.StudentId);
        process.StartInfo.ArgumentList.Add("--session-id");
        process.StartInfo.ArgumentList.Add($"web-{sessionId:N}");
        process.StartInfo.ArgumentList.Add("--include-retrieval");

        ApplyDefaultEnvironment(process.StartInfo, configuration);

        process.Start();
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);

        var timeoutSeconds = configuration.GetValue("PythonAgent:TimeoutSeconds", 90);
        var waitForExitTask = process.WaitForExitAsync(cancellationToken);
        var completed = await Task.WhenAny(waitForExitTask, Task.Delay(TimeSpan.FromSeconds(timeoutSeconds), cancellationToken));
        if (completed != waitForExitTask)
        {
            try
            {
                process.Kill(entireProcessTree: true);
            }
            catch
            {
                // Process may already have exited.
            }

            throw new TimeoutException($"Python AI Core quá thời gian {timeoutSeconds} giây.");
        }

        await waitForExitTask;

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"Python AI Core exit code {process.ExitCode}: {stderr}");
        }

        var json = ExtractJson(stdout);
        var raw = JsonSerializer.Deserialize<Dictionary<string, object?>>(json, JsonOptions) ?? [];
        var response = JsonSerializer.Deserialize<AgentBridgeResponse>(json, JsonOptions)
            ?? throw new InvalidOperationException("Không đọc được JSON response từ Python AI Core.");
        response.Raw = raw;
        return response;
    }

    private string ResolveProjectRoot()
    {
        var configured = configuration["PythonAgent:ProjectRoot"];
        if (!string.IsNullOrWhiteSpace(configured) && Directory.Exists(configured))
        {
            return configured;
        }

        var current = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "scripts", "run_agent_service_cli.py")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Không xác định được project root chứa scripts/run_agent_service_cli.py.");
    }

    private string ResolvePythonExecutable(string projectRoot)
    {
        var configured = configuration["PythonAgent:Executable"];
        if (!string.IsNullOrWhiteSpace(configured))
        {
            return configured;
        }

        var venvPython = Path.Combine(projectRoot, "venv", "Scripts", "python.exe");
        return File.Exists(venvPython) ? venvPython : "python";
    }

    private static void ApplyDefaultEnvironment(ProcessStartInfo startInfo, IConfiguration configuration)
    {
        SetDefault("PYTHONIOENCODING", "utf-8");
        SetDefault("HF_HUB_OFFLINE", "1");
        SetDefault("TRANSFORMERS_OFFLINE", "1");
        SetDefault("HYBRID_PLANNER_MODE", "auto");
        startInfo.Environment["STUDENT_API_PROVIDER"] = "http";
        startInfo.Environment["STUDENT_API_BASE_URL"] =
            configuration["PythonAgent:StudentApiBaseUrl"] ?? "http://localhost:5098/api";
        return;

        void SetDefault(string key, string value)
        {
            if (!startInfo.Environment.ContainsKey(key) || string.IsNullOrWhiteSpace(startInfo.Environment[key]))
            {
                startInfo.Environment[key] = value;
            }
        }
    }

    private static string ExtractJson(string stdout)
    {
        var start = stdout.IndexOf('{');
        var end = stdout.LastIndexOf('}');
        if (start < 0 || end <= start)
        {
            throw new InvalidOperationException("Python AI Core không trả JSON hợp lệ.");
        }

        return stdout[start..(end + 1)];
    }

    private static IReadOnlyList<ChatCitation> BuildCitations(AgentBridgeResponse agent)
    {
        if (agent.Citations.Count == 0)
        {
            return [];
        }

        return agent.Citations
            .Select((citation, index) => new ChatCitation("AI Core / RAG", $"Nguồn {index + 1}", citation))
            .ToList();
    }

    private static IReadOnlyList<ChatCard> BuildCards(AgentBridgeResponse agent)
    {
        var cards = new List<ChatCard>();
        if (agent.ToolResults is not null)
        {
            cards.Add(new ChatCard("tool_results", "Kết quả tool-use", agent.ToolResults));
        }

        if (agent.RetrievalResults.Count > 0)
        {
            cards.Add(new ChatCard("retrieval_results", "Đoạn tài liệu RAG đã truy xuất", agent.RetrievalResults));
        }

        return cards;
    }
}

public sealed class AgentBridgeResponse
{
    [JsonPropertyName("answer")]
    public string Answer { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "fallback";

    [JsonPropertyName("route")]
    public string Route { get; set; } = "fallback";

    [JsonPropertyName("student_id")]
    public string? StudentId { get; set; }

    [JsonPropertyName("needs_clarification")]
    public bool NeedsClarification { get; set; }

    [JsonPropertyName("clarification_questions")]
    public List<string> ClarificationQuestions { get; set; } = [];

    [JsonPropertyName("citations")]
    public List<string> Citations { get; set; } = [];

    [JsonPropertyName("error")]
    public Dictionary<string, object?>? Error { get; set; }

    [JsonPropertyName("tool_results")]
    public Dictionary<string, object?>? ToolResults { get; set; }

    [JsonPropertyName("retrieval_results")]
    public List<Dictionary<string, object?>> RetrievalResults { get; set; } = [];

    public Dictionary<string, object?> Raw { get; set; } = [];
}
