using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.Win32;

namespace CivicLedger;

enum WslState
{
    Missing,
    NeedsReboot,
    Version1,
    Ready,
}

static class Prereqs
{
    public const string DockerPage = "https://www.docker.com/products/docker-desktop/";
    public const string DockerInstaller =
        "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe";
    public const string OllamaPage = "https://ollama.com/download";
    public const string OllamaInstaller = "https://ollama.com/download/OllamaSetup.exe";
    public const string WslDocs = "https://learn.microsoft.com/windows/wsl/install";

    public const string WslExplanation =
        "WSL 2 (Windows Subsystem for Linux 2) is a major Windows feature, not a small plugin.\n\n"
        + "It adds a real Linux kernel that runs beside Windows using Microsoft’s virtualization "
        + "(Virtual Machine Platform). Docker Desktop uses WSL 2 to run Linux containers for Civic Ledger.\n\n"
        + "Turning it on will:\n"
        + "• Enable Windows optional features (WSL + Virtual Machine Platform)\n"
        + "• Usually require an administrator prompt and a full reboot\n"
        + "• Use extra RAM and disk while Docker is running\n"
        + "• Change how virtualization works on this PC\n\n"
        + "Other apps that use Hyper-V, Android emulators, or virtual machines can be affected.\n\n"
        + "You can uninstall Civic Ledger later without removing WSL 2. Removing WSL 2 is optional "
        + "and will delete Linux distributions stored on this computer.";

    public static string? DockerDesktopExe()
    {
        foreach (var candidate in new[]
                 {
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                         "Docker", "Docker", "Docker Desktop.exe"),
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                         "Docker", "Docker", "Docker Desktop.exe"),
                 })
        {
            if (File.Exists(candidate))
                return candidate;
        }
        return null;
    }

    public static string? OllamaExe()
    {
        foreach (var candidate in new[]
                 {
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                         "Programs", "Ollama", "ollama.exe"),
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                         "Ollama", "ollama.exe"),
                 })
        {
            if (File.Exists(candidate))
                return candidate;
        }
        return FindOnPath("ollama.exe");
    }

    public static bool DockerDesktopInstalled() => DockerDesktopExe() is not null;

    public static bool OllamaInstalled() => OllamaExe() is not null;

    public static async Task<bool> DockerEngineRunning()
    {
        var (code, output) = await Run("docker", "info", 8000);
        return code == 0 && output.Contains("Server Version", StringComparison.OrdinalIgnoreCase);
    }

    public static async Task<bool> OllamaResponding()
    {
        var exe = OllamaExe();
        if (exe is null) return false;
        var (code, _) = await Run(exe, "list", 8000);
        return code == 0;
    }

    public static async Task<WslState> DetectWsl()
    {
        var wsl = Path.Combine(Environment.SystemDirectory, "wsl.exe");
        if (!File.Exists(wsl))
            return WslState.Missing;

        var (code, output) = await Run(wsl, "--status", 8000);
        var text = output;
        if (ContainsAny(text, "not enabled", "not installed", "must be enabled", "n'est pas", "nicht aktiviert"))
            return WslState.Missing;
        if (ContainsAny(text, "Default Version: 2", "version: 2", "WSL 2", "WSL2"))
            return WslState.Ready;
        if (ContainsAny(text, "Default Version: 1", "version: 1"))
            return WslState.Version1;

        var list = await Run(wsl, "-l -v", 8000);
        if (Regex.IsMatch(list.Output, @"\s2(\s|$)"))
            return WslState.Ready;
        if (Regex.IsMatch(list.Output, @"\s1(\s|$)"))
            return WslState.Version1;
        if (code != 0)
            return WslState.NeedsReboot;

        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss");
            var ver = key?.GetValue("DefaultVersion");
            if (ver is int i && i == 2)
                return WslState.Ready;
        }
        catch
        {
            // ignore
        }
        return File.Exists(wsl) ? WslState.NeedsReboot : WslState.Missing;
    }

    public static string WslStatusText(WslState state) => state switch
    {
        WslState.Ready => "Ready (WSL 2)",
        WslState.Version1 => "WSL 1 only — WSL 2 required",
        WslState.NeedsReboot => "Enabled — reboot required",
        _ => "Missing",
    };

    public static void OpenUrl(string url)
    {
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }

    public static void StartDockerDesktop()
    {
        var exe = DockerDesktopExe();
        if (exe is null) return;
        Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true });
    }

    public static async Task InstallDocker()
    {
        if (await Winget("Docker.DockerDesktop"))
            return;
        OpenUrl(DockerInstaller);
    }

    public static async Task InstallOllama()
    {
        if (await Winget("Ollama.Ollama"))
            return;
        OpenUrl(OllamaInstaller);
    }

    public static void InstallWsl2()
    {
        var wsl = Path.Combine(Environment.SystemDirectory, "wsl.exe");
        RunElevated(wsl, "--install --no-distribution");
    }

    public static async Task UninstallCivicLedger(Action<string> log)
    {
        var root = CivicLedgerDir();
        if (Directory.Exists(root) && DockerDesktopInstalled())
        {
            log("Stopping Civic Ledger containers and volumes…");
            await Run("docker", "compose down -v", 120_000, root);
            await Run("docker", "volume rm -f cpl_data cpl_llm", 60_000, root);
        }
        log("Removing Civic Ledger application…");
        UninstallByDisplayName("Civic Ledger");
        UninstallByDisplayName("Canadian Political Leak");
        TryDelete(root);
        TryDelete(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Canadian Political Leak"));
        TryDelete(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Microsoft", "Windows", "Start Menu", "Programs", "Civic Ledger"));
        TryDelete(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Microsoft", "Windows", "Start Menu", "Programs", "Canadian Political Leak"));
        log("Civic Ledger app files removed.");
    }

    public static async Task UninstallDocker(Action<string> log)
    {
        log("Uninstalling Docker Desktop…");
        if (await WingetUninstall("Docker.DockerDesktop"))
        {
            log("Docker Desktop removed with winget.");
            return;
        }
        var installer = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "Docker", "Docker", "Docker Desktop Installer.exe");
        if (File.Exists(installer))
        {
            RunElevated(installer, "uninstall");
            log("Docker Desktop uninstaller started. Complete it if a window appears.");
            return;
        }
        log("Could not find Docker uninstaller. Remove Docker Desktop from Settings → Apps.");
    }

    public static async Task UninstallOllama(Action<string> log)
    {
        log("Uninstalling Ollama…");
        if (await WingetUninstall("Ollama.Ollama"))
        {
            log("Ollama removed with winget.");
            return;
        }
        UninstallByDisplayName("Ollama");
        TryDelete(Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Programs", "Ollama"));
        log("Ollama uninstall requested.");
    }

    public static void UninstallWsl2(Action<string> log)
    {
        log("Uninstalling WSL 2 (administrator prompt)…");
        var wsl = Path.Combine(Environment.SystemDirectory, "wsl.exe");
        if (!File.Exists(wsl))
        {
            log("wsl.exe not found.");
            return;
        }
        RunElevated(wsl, "--shutdown");
        RunElevated(wsl, "--uninstall");
        log("WSL uninstall started. Windows may ask to reboot. Linux distros on this PC will be deleted.");
    }

    public static string CivicLedgerDir() =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Civic Ledger");

    static bool ContainsAny(string text, params string[] parts) =>
        parts.Any(p => text.Contains(p, StringComparison.OrdinalIgnoreCase));

    static void UninstallByDisplayName(string displayName)
    {
        foreach (var hive in new[] { Registry.CurrentUser, Registry.LocalMachine })
        {
            foreach (var path in new[]
                     {
                         @"Software\Microsoft\Windows\CurrentVersion\Uninstall",
                         @"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
                     })
            {
                using var key = hive.OpenSubKey(path);
                if (key is null) continue;
                foreach (var sub in key.GetSubKeyNames())
                {
                    using var app = key.OpenSubKey(sub);
                    var name = app?.GetValue("DisplayName") as string;
                    if (!string.Equals(name, displayName, StringComparison.OrdinalIgnoreCase))
                        continue;
                    var cmd = app?.GetValue("UninstallString") as string;
                    if (string.IsNullOrWhiteSpace(cmd)) continue;
                    RunUninstallString(cmd);
                }
            }
        }
    }

    static void RunUninstallString(string cmd)
    {
        cmd = cmd.Trim();
        if (cmd.StartsWith("MsiExec", StringComparison.OrdinalIgnoreCase) ||
            cmd.StartsWith("msiexec", StringComparison.OrdinalIgnoreCase))
        {
            var args = cmd.Contains("/I", StringComparison.OrdinalIgnoreCase)
                ? cmd[cmd.IndexOf(' ')..].Replace("/I", "/x", StringComparison.OrdinalIgnoreCase) + " /qb"
                : cmd[cmd.IndexOf(' ')..] + " /qb";
            Process.Start(new ProcessStartInfo("msiexec", args.Trim()) { UseShellExecute = true });
            return;
        }
        Process.Start(new ProcessStartInfo(cmd) { UseShellExecute = true });
    }

    static void TryDelete(string path)
    {
        try
        {
            if (Directory.Exists(path))
                Directory.Delete(path, true);
        }
        catch
        {
            // files in use
        }
    }

    static void RunElevated(string file, string args)
    {
        Process.Start(new ProcessStartInfo
        {
            FileName = file,
            Arguments = args,
            UseShellExecute = true,
            Verb = "runas",
        });
    }

    static async Task<bool> Winget(string packageId)
    {
        try
        {
            var (code, _) = await Run(
                "winget",
                $"install -e --id {packageId} --accept-package-agreements --accept-source-agreements",
                600_000);
            return code == 0;
        }
        catch
        {
            return false;
        }
    }

    static async Task<bool> WingetUninstall(string packageId)
    {
        try
        {
            var (code, _) = await Run(
                "winget",
                $"uninstall -e --id {packageId} --accept-source-agreements",
                300_000);
            return code == 0;
        }
        catch
        {
            return false;
        }
    }

    static string? FindOnPath(string file)
    {
        var paths = (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator);
        foreach (var dir in paths)
        {
            try
            {
                var p = Path.Combine(dir.Trim(), file);
                if (File.Exists(p))
                    return p;
            }
            catch
            {
                // ignore bad PATH entries
            }
        }
        return null;
    }

    public static async Task<(int Code, string Output)> Run(
        string file, string args, int timeoutMs, string? cwd = null)
    {
        var psi = new ProcessStartInfo
        {
            FileName = file,
            Arguments = args,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        if (!string.IsNullOrWhiteSpace(cwd))
            psi.WorkingDirectory = cwd;
        using var proc = Process.Start(psi);
        if (proc is null)
            return (-1, "");
        var buf = new StringBuilder();
        buf.Append(await proc.StandardOutput.ReadToEndAsync());
        buf.Append(await proc.StandardError.ReadToEndAsync());
        var done = await Task.Run(() => proc.WaitForExit(timeoutMs));
        if (!done)
        {
            try { proc.Kill(true); } catch { /* ignore */ }
            return (-1, buf.ToString());
        }
        return (proc.ExitCode, buf.ToString());
    }
}
