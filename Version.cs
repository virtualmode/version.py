#!/usr/bin/env -S dotnet --

// File-based app to obtain source version.
// Author: https://github.com/virtualmode

#:property Version = 1.2.8
#:property ToolCommandName = version

#:package System.CommandLine@2.0.9

using System.CommandLine;
using System.Reflection;

// Get current assembly information.
Assembly assembly = Assembly.GetExecutingAssembly();
System.Version assemblyVersion = assembly.GetName().Version ?? new System.Version(1, 0, 0, 0);
string assemblyInformationalVersion = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "1.0.0";

// Log level option initialization.
Option<string> optionLogLevel = new("--log-level", ["-l"])
{
    Description = "Sets log severity level: t[race], d[ebug], i[nformation], w[arning], e[rror], c[ritical] and n[one]",
    DefaultValueFactory = parseResult => "n",
};

// CommandLine automatically treats Option<bool> targets as flags that do not require an attached value.
Option<bool> optionDebug = new("--debug", ["-d"])
{
    Description = "Show debug information alias for log level"
};

// Root command to parse arguments.
RootCommand commandRoot = new($"Version script {assemblyVersion.Major}.{assemblyVersion.Minor}.{assemblyVersion.Build} to get automatic source version of the commit.") // Commands already has help and version options by default.
{
    optionLogLevel,
    optionDebug,
};

// Add alias for the embedded version option.
commandRoot.Options.FirstOrDefault(o => o.Name == "--version")?.Aliases.Add("-v");

// Start program.
commandRoot.SetAction(OnVersioningStart);
ParseResult commandRootResult = commandRoot.Parse(args);
return commandRootResult.Invoke();

#region Declarations

/// <summary>
/// Versioning entry point.
/// </summary>
int OnVersioningStart(ParseResult parseResult)
{
    return 0;
}

/// <summary>
/// Assembly and SemVer versioning container class.
/// </summary>
public class Version
{
    public int Major;
    public int? Minor;
    public int? PatchOrBuild;
    public int? Revision;
    public string? Prerelease;
    public string? BuildMetadata;

    /// <summary>
    /// Convert to version string.
    /// </summary>
    /// <param name="noZeros">Do not show zeros if version numbers are not presented.</param>
    /// <param name="shortFormat">Use short version format.</param>
    /// <param name="assembly">Use assembly versioning.</param>
    /// <returns>Version string.</returns>
    public string ToVersion(bool noZeros, bool shortFormat, bool assembly)
    {
        return string.Format("{0}{1}{2}{3}{4}{5}",
            Major,
            Minor != null ? $".{Minor}" : noZeros && PatchOrBuild == null && (Revision == null || !assembly) ? string.Empty : ".0",
            PatchOrBuild != null ? $".{PatchOrBuild}" : noZeros && (Revision == null || !assembly) ? string.Empty : ".0",

            Revision != null && assembly ? $".{Revision}" : noZeros && !assembly ? string.Empty : ".0",
            //Revision == null && noZeros ? string.Empty : Revision != null && assembly ? $".{Revision}" : ".0",
            // assembly && !noZeros ? ".0" : string.Empty

            Prerelease != null && !shortFormat ? $"-{Prerelease}" : string.Empty,
            BuildMetadata != null && !shortFormat ? $"+{BuildMetadata}" : string.Empty);
    }
}

#endregion Declarations
