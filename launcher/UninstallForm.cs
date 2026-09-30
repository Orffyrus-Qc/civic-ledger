namespace CivicLedger;

sealed class UninstallForm : Form
{
    readonly CheckBox _civic = new() { Text = "Civic Ledger (app, Start menu, Docker volumes cpl_data / cpl_llm)", Checked = true, AutoSize = true };
    readonly CheckBox _docker = new() { Text = "Docker Desktop (all Docker apps on this PC)", AutoSize = true };
    readonly CheckBox _ollama = new() { Text = "Ollama (host app and its models)", AutoSize = true };
    readonly CheckBox _wsl = new() { Text = "WSL 2 (Windows Subsystem for Linux 2 — major Windows feature)", AutoSize = true };
    readonly TextBox _confirm = new() { Width = 220 };
    readonly Button _go = new() { Text = "Uninstall selected", Width = 180, Height = 36 };
    readonly TextBox _log = new()
    {
        Multiline = true,
        ReadOnly = true,
        ScrollBars = ScrollBars.Vertical,
        Dock = DockStyle.Fill,
        Font = new Font("Consolas", 9f),
    };

    public UninstallForm()
    {
        Text = "Uninstall Civic Ledger";
        Width = 680;
        Height = 560;
        StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10f);

        var warn = new Label
        {
            AutoSize = false,
            Dock = DockStyle.Top,
            Height = 96,
            Padding = new Padding(16, 12, 16, 8),
            BackColor = Color.FromArgb(255, 236, 200),
            Text =
                "NOT TESTED YET. This uninstaller has not been verified on a clean PC. Use at your own risk.\n"
                + "Civic Ledger can be removed by itself. Docker, Ollama, and especially WSL 2 may be used by other software.\n"
                + "Leave those boxes unchecked unless you want them gone from this Windows PC. WSL 2 removal deletes Linux distros and often needs a reboot.",
        };

        var box = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 150,
            Padding = new Padding(16, 8, 16, 8),
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
        };
        box.Controls.Add(_civic);
        box.Controls.Add(_docker);
        box.Controls.Add(_ollama);
        box.Controls.Add(_wsl);

        var confirmRow = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 44,
            Padding = new Padding(16, 0, 16, 0),
            WrapContents = false,
        };
        confirmRow.Controls.Add(new Label
        {
            Text = "To remove WSL 2, type REMOVE and then Uninstall selected:",
            AutoSize = true,
            Padding = new Padding(0, 8, 8, 0),
        });
        confirmRow.Controls.Add(_confirm);
        confirmRow.Controls.Add(_go);

        var logHost = new Panel { Dock = DockStyle.Fill, Padding = new Padding(16, 8, 16, 16) };
        logHost.Controls.Add(_log);

        Controls.Add(logHost);
        Controls.Add(confirmRow);
        Controls.Add(box);
        Controls.Add(warn);

        _go.Click += async (_, _) => await RunUninstall();
    }

    void Log(string line)
    {
        _log.AppendText(line + Environment.NewLine);
    }

    async Task RunUninstall()
    {
        if (!_civic.Checked && !_docker.Checked && !_ollama.Checked && !_wsl.Checked)
        {
            MessageBox.Show(this, "Select at least one item.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        if (_wsl.Checked)
        {
            if (!string.Equals(_confirm.Text.Trim(), "REMOVE", StringComparison.Ordinal))
            {
                MessageBox.Show(
                    this,
                    "WSL 2 is a Windows operating-system feature.\n\n"
                    + "Removing it deletes Linux distros on this PC and can break Docker, Android emulators, "
                    + "and other tools.\n\nType REMOVE in the box to confirm.",
                    "WSL 2 removal blocked",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning);
                return;
            }
            var wslAsk = MessageBox.Show(
                this,
                Prereqs.WslExplanation + "\n\nRemove WSL 2 from Windows now?",
                "Final warning — WSL 2",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button2);
            if (wslAsk != DialogResult.Yes)
                return;
        }
        if (_docker.Checked || _ollama.Checked)
        {
            var extra = MessageBox.Show(
                this,
                "Docker Desktop and/or Ollama may be used by other projects on this PC.\n\nContinue?",
                "Remove extra software",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question,
                MessageBoxDefaultButton.Button2);
            if (extra != DialogResult.Yes)
                return;
        }

        _go.Enabled = false;
        try
        {
            if (_civic.Checked)
                await Prereqs.UninstallCivicLedger(Log);
            if (_docker.Checked)
                await Prereqs.UninstallDocker(Log);
            if (_ollama.Checked)
                await Prereqs.UninstallOllama(Log);
            if (_wsl.Checked)
                Prereqs.UninstallWsl2(Log);
            Log("Done. If WSL 2 or Docker asked for a reboot, restart Windows.");
            MessageBox.Show(this, "Uninstall finished. See the log for details.", Text);
        }
        catch (Exception ex)
        {
            Log(ex.Message);
            MessageBox.Show(this, ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _go.Enabled = true;
        }
    }
}
