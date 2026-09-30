using System.Diagnostics;
using System.Text;

namespace CivicLedger;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        if (args.Any(a => a.Equals("/uninstall", StringComparison.OrdinalIgnoreCase)))
            Application.Run(new UninstallForm());
        else
            Application.Run(new MainForm());
    }
}

sealed class ModelChoice
{
    public required string Name { get; init; }
    public required string Kind { get; init; } // installed | host | download
    public override string ToString() => Kind switch
    {
        "installed" => Name + "  (installed)",
        "host" => Name + "  (on this PC — copy download)",
        _ => Name + "  (download default, ~5 GB)",
    };
}

sealed class MainForm : Form
{
    const string DefaultModel = "qwen3:8b";

    readonly Button _start = new() { Text = "Start", Width = 120, Height = 36 };
    readonly Button _stop = new() { Text = "Stop", Width = 120, Height = 36 };
    readonly ComboBox _models = new()
    {
        DropDownStyle = ComboBoxStyle.DropDownList,
        Width = 280,
        Height = 28,
    };
    readonly Button _refreshModels = new() { Text = "Refresh", Width = 90, Height = 36 };
    readonly Button _downloadDefault = new() { Text = "Download default", Width = 150, Height = 36 };
    readonly Button _uninstall = new() { Text = "Uninstall…", Width = 110, Height = 36 };
    readonly Label _status = new() { AutoSize = false, Height = 28, TextAlign = ContentAlignment.MiddleLeft };
    readonly TextBox _log = new()
    {
        Multiline = true,
        ReadOnly = true,
        ScrollBars = ScrollBars.Vertical,
        Font = new Font("Consolas", 9f),
        Dock = DockStyle.Fill,
    };

    readonly string _stackRoot;

    public MainForm()
    {
        _stackRoot = FindStackRoot();
        Text = "Civic Ledger";
        Width = 640;
        Height = 420;
        MinimumSize = new Size(560, 320);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.Sizable;
        Font = new Font("Segoe UI", 10f);

        var top = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 52,
            Padding = new Padding(12, 8, 12, 4),
            WrapContents = false,
        };
        top.Controls.Add(_start);
        top.Controls.Add(_stop);
        top.Controls.Add(_uninstall);

        var modelRow = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 48,
            Padding = new Padding(12, 4, 12, 4),
            WrapContents = false,
        };
        var modelLabel = new Label
        {
            Text = "AI model",
            AutoSize = true,
            Padding = new Padding(0, 8, 8, 0),
        };
        modelRow.Controls.Add(modelLabel);
        modelRow.Controls.Add(_models);
        modelRow.Controls.Add(_refreshModels);
        modelRow.Controls.Add(_downloadDefault);

        _status.Dock = DockStyle.Top;
        _status.Padding = new Padding(14, 0, 14, 0);
        _status.Text = "Stack folder: " + _stackRoot;

        var logHost = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12, 6, 12, 12) };
        logHost.Controls.Add(_log);

        Controls.Add(logHost);
        Controls.Add(_status);
        Controls.Add(modelRow);
        Controls.Add(top);

        _start.Click += async (_, _) => await StartStack();
        _stop.Click += async (_, _) => await StopStack();
        _refreshModels.Click += async (_, _) => await RefreshModels();
        _downloadDefault.Click += async (_, _) => await DownloadDefault();
        _uninstall.Click += (_, _) =>
        {
            using var f = new UninstallForm();
            f.ShowDialog(this);
        };

        Shown += async (_, _) =>
        {
            SelectSavedModel();
            await RefreshStatus();
            await RefreshModels();
        };
    }

    async Task StartStack()
    {
        if (!await EnsurePrereqs())
            return;
        SetBusy(true);
        _status.Text = "Starting…";
        try
        {
            var choice = CurrentChoice();
            WriteModelEnv(choice.Name);

            var (code, _) = await Exec("docker", ["compose", "up", "-d", "--build", "searxng", "llm", "app"], log: true);
            if (code != 0)
            {
                _status.Text = "Failed (exit " + code + "). Is Docker Desktop running?";
                return;
            }

            if (!await WaitForLlm())
            {
                _status.Text = "Ollama did not become ready.";
                return;
            }

            var installed = await ListDockerModels();
            if (!installed.Contains(choice.Name, StringComparer.OrdinalIgnoreCase))
            {
                var sizeHint = choice.Name == DefaultModel ? " (~5 GB)" : "";
                var ok = MessageBox.Show(
                    this,
                    "Download " + choice.Name + sizeHint + " into Civic Ledger?\n\n"
                    + "This is a separate copy from any model already on the host. "
                    + "It can take several minutes. Choose No to start the UI without a model.",
                    "Confirm model download",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question,
                    MessageBoxDefaultButton.Button2);
                if (ok != DialogResult.Yes)
                {
                    _status.Text = "Running without a model — http://127.0.0.1:8088";
                    return;
                }
                _status.Text = "Downloading " + choice.Name + "…";
                var pull = await Exec("docker", ["exec", "cpl-llm", "ollama", "pull", choice.Name], log: true);
                if (pull.Code != 0)
                {
                    _status.Text = "Model download failed.";
                    return;
                }
            }

            await Exec("docker", ["compose", "up", "-d", "app"], log: true);
            _status.Text = "Running — http://127.0.0.1:8088  (" + choice.Name + ")";
            await RefreshModels();
        }
        catch (Exception ex)
        {
            AppendLog(ex.Message);
            _status.Text = "Failed. Is Docker on PATH?";
        }
        finally
        {
            SetBusy(false);
        }
    }

    async Task StopStack()
    {
        SetBusy(true);
        _status.Text = "Stopping…";
        try
        {
            var (code, _) = await Exec("docker", ["compose", "down"], log: true);
            _status.Text = code == 0 ? "Stopped." : "Stop failed (exit " + code + ").";
        }
        catch (Exception ex)
        {
            AppendLog(ex.Message);
            _status.Text = "Failed. Is Docker on PATH?";
        }
        finally
        {
            SetBusy(false);
        }
    }

    async Task<bool> EnsurePrereqs()
    {
        var wsl = await Prereqs.DetectWsl();
        if (wsl != WslState.Ready)
        {
            var ask = MessageBox.Show(
                this,
                Prereqs.WslExplanation + "\n\nWSL 2 status: " + Prereqs.WslStatusText(wsl)
                + "\n\nEnable WSL 2 now? Windows will likely reboot.",
                "WSL 2 required — large Windows change",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button2);
            if (ask == DialogResult.Yes)
                Prereqs.InstallWsl2();
            return false;
        }
        if (!Prereqs.DockerDesktopInstalled())
        {
            var ask = MessageBox.Show(
                this,
                "Docker Desktop is required and is not installed.\n\nInstall Docker Desktop now?",
                "Civic Ledger",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);
            if (ask == DialogResult.Yes)
                await Prereqs.InstallDocker();
            return false;
        }
        if (!await Prereqs.DockerEngineRunning())
        {
            var ask = MessageBox.Show(
                this,
                "Docker Desktop is installed but not running.\n\nStart Docker Desktop now?",
                "Civic Ledger",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);
            if (ask == DialogResult.Yes)
                Prereqs.StartDockerDesktop();
            _status.Text = "Start Docker Desktop, wait until it is idle, then click Start again.";
            return false;
        }
        if (!Prereqs.OllamaInstalled())
        {
            var ask = MessageBox.Show(
                this,
                "Ollama is required and is not installed.\n\nInstall Ollama now?",
                "Civic Ledger",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);
            if (ask == DialogResult.Yes)
                await Prereqs.InstallOllama();
            return false;
        }
        return true;
    }

    async Task DownloadDefault()
    {
        SetBusy(true);
        try
        {
            var ok = MessageBox.Show(
                this,
                "Download the default model " + DefaultModel + " (~5 GB) into Civic Ledger?\n\n"
                + "This can take several minutes and uses GPU 1.",
                "Confirm model download",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question,
                MessageBoxDefaultButton.Button2);
            if (ok != DialogResult.Yes)
                return;

            WriteModelEnv(DefaultModel);
            var up = await Exec("docker", ["compose", "up", "-d", "llm"], log: true);
            if (up.Code != 0)
            {
                _status.Text = "Could not start Ollama.";
                return;
            }
            if (!await WaitForLlm())
            {
                _status.Text = "Ollama did not become ready.";
                return;
            }
            _status.Text = "Downloading " + DefaultModel + "…";
            var pull = await Exec("docker", ["exec", "cpl-llm", "ollama", "pull", DefaultModel], log: true);
            _status.Text = pull.Code == 0 ? "Default model ready: " + DefaultModel : "Download failed.";
            await RefreshModels();
        }
        finally
        {
            SetBusy(false);
        }
    }

    async Task RefreshModels()
    {
        var saved = ReadModelEnv() ?? (CurrentChoice()?.Name);
        var docker = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try { docker.UnionWith(await ListDockerModels()); } catch { /* llm not up */ }
        var host = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try { host.UnionWith(await ListHostModels()); } catch { /* no host ollama */ }

        _models.Items.Clear();
        foreach (var name in docker.OrderBy(n => n, StringComparer.OrdinalIgnoreCase))
            _models.Items.Add(new ModelChoice { Name = name, Kind = "installed" });
        foreach (var name in host.Except(docker).OrderBy(n => n, StringComparer.OrdinalIgnoreCase))
            _models.Items.Add(new ModelChoice { Name = name, Kind = "host" });
        if (!_models.Items.Cast<ModelChoice>().Any(c => c.Name.Equals(DefaultModel, StringComparison.OrdinalIgnoreCase)))
            _models.Items.Add(new ModelChoice { Name = DefaultModel, Kind = "download" });

        if (_models.Items.Count == 0)
            _models.Items.Add(new ModelChoice { Name = DefaultModel, Kind = "download" });

        SelectByName(saved ?? DefaultModel);
    }

    void SelectSavedModel()
    {
        var saved = ReadModelEnv();
        if (saved is null) return;
        _models.Items.Clear();
        _models.Items.Add(new ModelChoice { Name = saved, Kind = "installed" });
        _models.SelectedIndex = 0;
    }

    void SelectByName(string name)
    {
        for (var i = 0; i < _models.Items.Count; i++)
        {
            if (_models.Items[i] is ModelChoice c && c.Name.Equals(name, StringComparison.OrdinalIgnoreCase))
            {
                _models.SelectedIndex = i;
                return;
            }
        }
        if (_models.Items.Count > 0)
            _models.SelectedIndex = 0;
    }

    ModelChoice CurrentChoice()
    {
        if (_models.SelectedItem is ModelChoice c)
            return c;
        return new ModelChoice { Name = DefaultModel, Kind = "download" };
    }

    async Task<bool> WaitForLlm()
    {
        for (var i = 0; i < 30; i++)
        {
            var (code, _) = await Exec("docker", ["exec", "cpl-llm", "ollama", "list"], log: false);
            if (code == 0) return true;
            await Task.Delay(2000);
        }
        return false;
    }

    async Task<List<string>> ListDockerModels()
    {
        var (code, output) = await Exec("docker", ["exec", "cpl-llm", "ollama", "list"], log: false);
        if (code != 0) return [];
        return ParseOllamaList(output);
    }

    async Task<List<string>> ListHostModels()
    {
        var (code, output) = await Exec("ollama", ["list"], log: false);
        if (code != 0) return [];
        return ParseOllamaList(output);
    }

    static List<string> ParseOllamaList(string output)
    {
        var names = new List<string>();
        foreach (var raw in output.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries))
        {
            var line = raw.Trim();
            if (line.StartsWith("NAME", StringComparison.OrdinalIgnoreCase)) continue;
            var name = line.Split(' ', StringSplitOptions.RemoveEmptyEntries).FirstOrDefault();
            if (!string.IsNullOrWhiteSpace(name))
                names.Add(name);
        }
        return names;
    }

    void WriteModelEnv(string model)
    {
        File.WriteAllText(Path.Combine(_stackRoot, ".env"), "OLLAMA_MODEL=" + model + Environment.NewLine);
    }

    string? ReadModelEnv()
    {
        var path = Path.Combine(_stackRoot, ".env");
        if (!File.Exists(path)) return null;
        foreach (var line in File.ReadAllLines(path))
        {
            if (line.StartsWith("OLLAMA_MODEL=", StringComparison.OrdinalIgnoreCase))
            {
                var v = line["OLLAMA_MODEL=".Length..].Trim();
                if (v.Length > 0) return v;
            }
        }
        return null;
    }

    void SetBusy(bool busy)
    {
        _start.Enabled = !busy;
        _stop.Enabled = !busy;
        _models.Enabled = !busy;
        _refreshModels.Enabled = !busy;
        _downloadDefault.Enabled = !busy;
        _uninstall.Enabled = !busy;
    }

    async Task RefreshStatus()
    {
        try
        {
            var (code, output) = await Exec("docker", ["compose", "ps", "-q"], log: false);
            if (code == 0 && output.Trim().Length > 0
                && !_status.Text.StartsWith("Starting", StringComparison.Ordinal)
                && !_status.Text.StartsWith("Stopping", StringComparison.Ordinal)
                && !_status.Text.StartsWith("Failed", StringComparison.Ordinal)
                && !_status.Text.StartsWith("Downloading", StringComparison.Ordinal))
            {
                var model = ReadModelEnv();
                _status.Text = "Running — http://127.0.0.1:8088"
                    + (model is null ? "" : "  (" + model + ")");
            }
        }
        catch
        {
            // leave the last status
        }
    }

    async Task<(int Code, string Output)> Exec(string file, string[] args, bool log)
    {
        var psi = new ProcessStartInfo
        {
            FileName = file,
            WorkingDirectory = _stackRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        foreach (var a in args)
            psi.ArgumentList.Add(a);

        var proc = new Process { StartInfo = psi, EnableRaisingEvents = true };
        var buf = new StringBuilder();
        void Handle(string? data)
        {
            if (data is null) return;
            buf.AppendLine(data);
            if (log)
                BeginInvoke(() => AppendLog(data));
        }
        proc.OutputDataReceived += (_, e) => Handle(e.Data);
        proc.ErrorDataReceived += (_, e) => Handle(e.Data);
        proc.Start();
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();
        await proc.WaitForExitAsync();
        return (proc.ExitCode, buf.ToString());
    }

    void AppendLog(string line)
    {
        if (string.IsNullOrWhiteSpace(line)) return;
        _log.AppendText(line.TrimEnd() + Environment.NewLine);
    }

    static string FindStackRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 10 && dir is not null; i++, dir = dir.Parent)
        {
            var compose = Path.Combine(dir.FullName, "docker-compose.yml");
            if (File.Exists(compose))
                return dir.FullName;
        }
        foreach (var fallback in new[]
                 {
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Civic Ledger"),
                     @"F:\canadian-political-leak",
                 })
        {
            if (File.Exists(Path.Combine(fallback, "docker-compose.yml")))
                return fallback;
        }
        throw new DirectoryNotFoundException("docker-compose.yml not found.");
    }
}
