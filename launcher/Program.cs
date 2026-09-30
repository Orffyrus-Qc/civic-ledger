using System.Diagnostics;
using System.Text;

namespace CivicLedger;

static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}

sealed class MainForm : Form
{
    readonly Button _start = new() { Text = "Start", Width = 140, Height = 40 };
    readonly Button _stop = new() { Text = "Stop", Width = 140, Height = 40 };
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
        Width = 560;
        Height = 360;
        MinimumSize = new Size(480, 280);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.Sizable;
        Font = new Font("Segoe UI", 10f);

        var top = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 56,
            Padding = new Padding(12, 10, 12, 6),
            WrapContents = false,
        };
        top.Controls.Add(_start);
        top.Controls.Add(_stop);

        _status.Dock = DockStyle.Top;
        _status.Padding = new Padding(14, 0, 14, 0);
        _status.Text = "Stack folder: " + _stackRoot;

        var logHost = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12, 6, 12, 12) };
        logHost.Controls.Add(_log);

        Controls.Add(logHost);
        Controls.Add(_status);
        Controls.Add(top);

        _start.Click += async (_, _) => await RunCompose("up", "-d", "--build");
        _stop.Click += async (_, _) => await RunCompose("down");

        Shown += async (_, _) => await RefreshStatus();
    }

    async Task RunCompose(params string[] args)
    {
        _start.Enabled = false;
        _stop.Enabled = false;
        _status.Text = args[0] == "up" ? "Starting…" : "Stopping…";
        _log.Clear();
        try
        {
            var (code, output) = await Exec("docker", Prepend("compose", args));
            AppendLog(output);
            if (code != 0)
            {
                _status.Text = "Failed (exit " + code + "). Is Docker Desktop running?";
                return;
            }
            _status.Text = args[0] == "up"
                ? "Running — http://127.0.0.1:8088"
                : "Stopped.";
        }
        catch (Exception ex)
        {
            AppendLog(ex.Message);
            _status.Text = "Failed. Is Docker on PATH?";
        }
        finally
        {
            _start.Enabled = true;
            _stop.Enabled = true;
            await RefreshStatus();
        }
    }

    async Task RefreshStatus()
    {
        try
        {
            var (code, output) = await Exec("docker", ["compose", "ps", "-q"]);
            if (code == 0 && output.Trim().Length > 0 && !_status.Text.StartsWith("Starting", StringComparison.Ordinal)
                && !_status.Text.StartsWith("Stopping", StringComparison.Ordinal)
                && !_status.Text.StartsWith("Failed", StringComparison.Ordinal))
            {
                _status.Text = "Running — http://127.0.0.1:8088";
            }
        }
        catch
        {
            // leave the last status
        }
    }

    async Task<(int Code, string Output)> Exec(string file, string[] args)
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
        proc.OutputDataReceived += (_, e) =>
        {
            if (e.Data is null) return;
            buf.AppendLine(e.Data);
            BeginInvoke(() => AppendLog(e.Data));
        };
        proc.ErrorDataReceived += (_, e) =>
        {
            if (e.Data is null) return;
            buf.AppendLine(e.Data);
            BeginInvoke(() => AppendLog(e.Data));
        };
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

    static string[] Prepend(string first, string[] rest)
    {
        var all = new string[rest.Length + 1];
        all[0] = first;
        Array.Copy(rest, 0, all, 1, rest.Length);
        return all;
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
