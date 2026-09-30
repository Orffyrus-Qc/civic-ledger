using System.Diagnostics;

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
            Application.Run(new SetupForm());
    }
}

sealed class SetupForm : Form
{
    readonly Label _wslStatus = StatusLabel();
    readonly Label _dockerStatus = StatusLabel();
    readonly Label _ollamaStatus = StatusLabel();
    readonly Button _installWsl = new() { Text = "Enable WSL 2", Width = 160, Height = 32 };
    readonly Button _installDocker = new() { Text = "Install Docker Desktop", Width = 180, Height = 32 };
    readonly Button _installOllama = new() { Text = "Install Ollama", Width = 160, Height = 32 };
    readonly Button _startDocker = new() { Text = "Start Docker", Width = 120, Height = 32 };
    readonly Button _refresh = new() { Text = "Refresh", Width = 100, Height = 32 };
    readonly Button _installApp = new() { Text = "Install Civic Ledger", Width = 180, Height = 36 };
    readonly Button _launch = new() { Text = "Launch Civic Ledger", Width = 180, Height = 36, Enabled = false };
    readonly Button _uninstall = new() { Text = "Uninstall…", Width = 120, Height = 36 };
    readonly Label _hint = new()
    {
        AutoSize = false,
        Height = 40,
        Dock = DockStyle.Top,
        Padding = new Padding(16, 4, 16, 4),
    };
    readonly System.Windows.Forms.Timer _timer = new() { Interval = 4000 };

    public SetupForm()
    {
        Text = "Civic Ledger Setup";
        Width = 720;
        Height = 640;
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        Font = new Font("Segoe UI", 10f);

        var intro = new Label
        {
            AutoSize = false,
            Dock = DockStyle.Top,
            Height = 56,
            Padding = new Padding(16, 12, 16, 4),
            Text =
                "NOT TESTED YET. This installer and uninstaller have not been verified on a clean PC.\n"
                + "A new Windows PC needs WSL 2, Docker Desktop, and Ollama. Enable them in order, reboot if asked, then install Civic Ledger.",
        };

        var wslBanner = new Label
        {
            AutoSize = false,
            Dock = DockStyle.Top,
            Height = 168,
            Padding = new Padding(16, 10, 16, 10),
            BackColor = Color.FromArgb(255, 220, 180),
            Font = new Font("Segoe UI", 9.5f),
            Text = Prereqs.WslExplanation,
        };

        var grid = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 156,
            Padding = new Padding(16, 8, 16, 8),
            ColumnCount = 3,
            RowCount = 3,
        };
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 28));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 36));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 36));
        grid.Controls.Add(new Label { Text = "1. WSL 2", AutoSize = true, Padding = new Padding(0, 8, 0, 0) }, 0, 0);
        grid.Controls.Add(_wslStatus, 1, 0);
        grid.Controls.Add(_installWsl, 2, 0);
        grid.Controls.Add(new Label { Text = "2. Docker Desktop", AutoSize = true, Padding = new Padding(0, 8, 0, 0) }, 0, 1);
        grid.Controls.Add(_dockerStatus, 1, 1);
        var dockerBtns = new FlowLayoutPanel { WrapContents = false, AutoSize = true };
        dockerBtns.Controls.Add(_installDocker);
        dockerBtns.Controls.Add(_startDocker);
        grid.Controls.Add(dockerBtns, 2, 1);
        grid.Controls.Add(new Label { Text = "3. Ollama", AutoSize = true, Padding = new Padding(0, 8, 0, 0) }, 0, 2);
        grid.Controls.Add(_ollamaStatus, 1, 2);
        grid.Controls.Add(_installOllama, 2, 2);

        var bottom = new FlowLayoutPanel
        {
            Dock = DockStyle.Bottom,
            Height = 52,
            FlowDirection = FlowDirection.RightToLeft,
            Padding = new Padding(12, 8, 12, 8),
        };
        bottom.Controls.Add(_installApp);
        bottom.Controls.Add(_launch);
        bottom.Controls.Add(_uninstall);
        bottom.Controls.Add(_refresh);

        Controls.Add(bottom);
        Controls.Add(_hint);
        Controls.Add(grid);
        Controls.Add(wslBanner);
        Controls.Add(intro);

        _installWsl.Click += async (_, _) =>
        {
            var ok = MessageBox.Show(
                this,
                Prereqs.WslExplanation + "\n\nEnable WSL 2 on this Windows PC now?\nWindows will likely ask for administrator permission and a reboot.",
                "Enable WSL 2 — large Windows change",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button2);
            if (ok != DialogResult.Yes)
                return;
            _hint.Text = "Starting WSL 2 install. Reboot if Windows asks, then run this setup again.";
            Prereqs.InstallWsl2();
            await RefreshStatus();
        };
        _installDocker.Click += async (_, _) =>
        {
            _hint.Text = "Starting Docker Desktop installer. Then click Refresh.";
            await Prereqs.InstallDocker();
            await RefreshStatus();
        };
        _installOllama.Click += async (_, _) =>
        {
            _hint.Text = "Starting Ollama installer. Then click Refresh.";
            await Prereqs.InstallOllama();
            await RefreshStatus();
        };
        _startDocker.Click += async (_, _) =>
        {
            Prereqs.StartDockerDesktop();
            _hint.Text = "Starting Docker Desktop. Wait until the whale icon is idle, then Refresh.";
            await RefreshStatus();
        };
        _refresh.Click += async (_, _) => await RefreshStatus();
        _installApp.Click += async (_, _) => await InstallMsi();
        _launch.Click += (_, _) => LaunchApp();
        _uninstall.Click += (_, _) =>
        {
            using var f = new UninstallForm();
            f.ShowDialog(this);
        };
        _timer.Tick += async (_, _) => await RefreshStatus();

        Shown += async (_, _) =>
        {
            await RefreshStatus();
            _timer.Start();
        };
        FormClosed += (_, _) => _timer.Stop();
    }

    static Label StatusLabel() => new()
    {
        AutoSize = true,
        Padding = new Padding(0, 8, 0, 0),
        Font = new Font("Segoe UI", 10f, FontStyle.Bold),
    };

    async Task RefreshStatus()
    {
        var wsl = await Prereqs.DetectWsl();
        var dockerInstalled = Prereqs.DockerDesktopInstalled();
        var dockerRunning = dockerInstalled && await Prereqs.DockerEngineRunning();
        var ollamaInstalled = Prereqs.OllamaInstalled();
        var ollamaReady = ollamaInstalled && await Prereqs.OllamaResponding();

        SetStatus(_wslStatus, Prereqs.WslStatusText(wsl));
        SetStatus(_dockerStatus, dockerRunning ? "Ready" : dockerInstalled ? "Installed — not running" : "Missing");
        SetStatus(_ollamaStatus, ollamaReady ? "Ready" : ollamaInstalled ? "Installed — start Ollama" : "Missing");
        _startDocker.Enabled = dockerInstalled && !dockerRunning;
        _installApp.Enabled = wsl == WslState.Ready && dockerRunning && ollamaInstalled;
        _hint.Text = _installApp.Enabled
            ? "Requirements are present. Install Civic Ledger, then Launch."
            : wsl == WslState.NeedsReboot
                ? "WSL 2 is enabled. Reboot Windows, then open this setup again."
                : "Enable WSL 2 first (big Windows feature), then Docker Desktop, then Ollama.";
    }

    static void SetStatus(Label label, string text)
    {
        label.Text = text;
        label.ForeColor = text.StartsWith("Ready", StringComparison.Ordinal) ? Color.ForestGreen
            : text.Contains("reboot", StringComparison.OrdinalIgnoreCase) || text.StartsWith("Installed", StringComparison.Ordinal)
                ? Color.DarkOrange
            : Color.Firebrick;
    }

    async Task InstallMsi()
    {
        var msi = FindMsi();
        if (msi is null)
        {
            MessageBox.Show(
                this,
                "CivicLedgerSetup.msi was not found next to this setup program.",
                "Civic Ledger Setup",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
            return;
        }
        _installApp.Enabled = false;
        _hint.Text = "Installing Civic Ledger…";
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "msiexec",
                Arguments = "/i \"" + msi + "\"",
                UseShellExecute = true,
            };
            using var proc = Process.Start(psi);
            if (proc is not null)
                await proc.WaitForExitAsync();
            _launch.Enabled = File.Exists(LauncherPath());
            _hint.Text = _launch.Enabled
                ? "Civic Ledger is installed. Click Launch, then Start and pick an AI model."
                : "Installer finished. Open Civic Ledger from the Start menu if Launch is disabled.";
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Install failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
            _installApp.Enabled = true;
        }
    }

    static string? FindMsi()
    {
        var nextTo = Path.Combine(AppContext.BaseDirectory, "CivicLedgerSetup.msi");
        if (File.Exists(nextTo))
            return nextTo;
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 6 && dir is not null; i++, dir = dir.Parent)
        {
            var p = Path.Combine(dir.FullName, "CivicLedgerSetup.msi");
            if (File.Exists(p))
                return p;
            p = Path.Combine(dir.FullName, "bin", "CivicLedgerSetup.msi");
            if (File.Exists(p))
                return p;
            p = Path.Combine(dir.FullName, "dist", "CivicLedgerSetup.msi");
            if (File.Exists(p))
                return p;
        }
        return null;
    }

    static string LauncherPath() => Path.Combine(Prereqs.CivicLedgerDir(), "CivicLedger.exe");

    static void LaunchApp()
    {
        var exe = LauncherPath();
        if (!File.Exists(exe))
            return;
        Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true });
    }
}
