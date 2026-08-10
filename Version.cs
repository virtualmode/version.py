#!/usr/bin/env -S dotnet --

// File-based app to obtain source version.
// Author: https://github.com/virtualmode

#:property Version = 1.2.8
#:property ToolCommandName = version
#:property NuGetAudit = false
#:property RunAnalyzers = false
//#:property WarningLevel = 0

#:package System.CommandLine@2.0.10

using System.CommandLine;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;

const uint ITERATIONS_NUMBER = 3;
const string GIT_MIN_VERSION = "2.5.0";
const string GIT_SHA_FORMAT = "%h";
const string GIT_COMMIT_EMPTY_SHA = "0000000";
const string VERSION_FILE_NAME = ".version";

// Get current assembly information.
Assembly assembly = Assembly.GetExecutingAssembly();
System.Version assemblyVersion = assembly.GetName().Version ?? new System.Version(1, 0, 0, 0);
//string assemblyInformationalVersion = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "1.0.0";

// Log level option initialization.
Option<string> optionLogLevel = new("--log-level", ["-l"])
{
    HelpName = "LEVEL",
    Description = "Sets log severity level: t[race], d[ebug], i[nformation], w[arning], e[rror], c[ritical] and n[one]",
    DefaultValueFactory = parseResult => "n",
};

Option<bool> optionDebug = new("--debug", ["-d"])
{
    Description = "Show debug information (alias for log level)"
};

Option<bool> optionShort = new("--short", ["-s"])
{
    Description = "Show short version instead of long"
};

Option<bool> optionAssembly = new("--assembly", ["-a"])
{
    Description = "Show assembly version instead of semantic version"
};

Option<bool> optionNoZeros = new("--no-zeros", ["-z"])
{
    Description = "Show no zeros if version numbers are not presented"
};

Option<bool> optionUpdate = new("--update", ["-u"])
{
    Description = "Update version file"
};

Option<bool> optionIgnoreMerges = new("--ignore-merges", ["-m"])
{
    Description = "Ignore merges in version increment"
};

Option<bool> optionIgnoreTags = new("--ignore-tags", ["-t"])
{
    Description = "Ignore tags with invalid versions"
};

Option<bool> optionIgnoreRefs = new("--ignore-refs", ["-r"])
{
    Description = "Ignore detached state and branch versions"
};

Option<string> optionId = new("-i")
{
    HelpName = "ID",
    Description = "Set build metadata custom identifier value",
    //DefaultValueFactory = parseResult => null,
};

Option<string> optionFile = new("-f")
{
    HelpName = "FILE",
    Description = "Use version file",
    DefaultValueFactory = parseResult => VERSION_FILE_NAME,
};

Option<string> optionRegex = new("-b")
{
    HelpName = "REGEX",
    Description = "Strict group-based regular expression for formatting and parsing build metadata",
    DefaultValueFactory = parseResult => Version.BUILD_METADATA_REGEX,
};

Option<uint> optionNumber = new("-n")
{
    HelpName = "NUMBER",
    Description = "Limit script iterations",
    DefaultValueFactory = parseResult => ITERATIONS_NUMBER,
};

Option<bool> optionMajor = new("--major")
{
    Description = "Show major version",
};

Option<bool> optionMinor = new("--minor")
{
    Description = "Show minor version",
};

Option<bool> optionPatchOrBuild = new("--patch-build")
{
    Description = "Show patch for semantic versioning or build number for assembly versioning",
};

Option<bool> optionRevision = new("--revision")
{
    Description = "Show revision for assembly versioning",
};

Option<bool> optionPrerelease = new("--pre-release")
{
    Description = "Show pre-release labels",
};

Option<bool> optionBuildMetadata = new("--build-metadata")
{
    Description = "Show build metadata",
};

// Compare multiple versions.
Option<string[]> optionCompare = new("--compare")
{
    HelpName = "VERSIONS",
    Description = "Compare multiple versions with each other: left is less than right if < sign is output, equal if =, greater if >",
    AllowMultipleArgumentsPerToken = true,
};

Option<string[]> optionValidate = new("--validate")
{
    HelpName = "VERSION",
    Description = "Validate version is correct (echo $? is 0 if valid and not valid in other cases)",
};

// Root command to parse arguments.
RootCommand commandRoot = new($"Version script {assemblyVersion.Major}.{assemblyVersion.Minor}.{assemblyVersion.Build} to get automatic source version of the commit.") // Commands already has help and version options by default.
{
    // Script arguments.
    optionLogLevel,
    optionDebug,
    optionShort,
    optionAssembly,
    optionNoZeros,
    optionUpdate,
    optionIgnoreMerges,
    optionIgnoreTags,
    optionIgnoreRefs,
    optionId,
    optionFile,
    optionRegex,
    optionNumber,
    // Version components flags.
    optionMajor,
    optionMinor,
    optionPatchOrBuild,
    optionRevision,
    optionPrerelease,
    optionBuildMetadata,
    // Additional functions.
    optionCompare,
    optionValidate,
};

// Add alias for the embedded version option.
commandRoot.Options.FirstOrDefault(o => o.Name == "--version")?.Aliases.Add("-v");

// Start program.
ParseResult commandRootResult = commandRoot.Parse(args);
commandRoot.SetAction(OnVersioningStart);
return commandRootResult.Invoke();

#region Declarations

/// <summary>
/// Console log function for debug purposes.
/// </summary>
/// <param name="message">Message to log.</param>
/// <param name="newLine">Use new line.</param>
/// <param name="logLevel">Message log level.</param>
/// <param name="force">Ignore log level and show message.</param>
/// <returns>Flag that the message was output.</returns>
bool Log(string? message, bool newLine = true, char logLevel = 't', bool force = false)
{
    char[] logLevels = {'t', 'd', 'i', 'w', 'e', 'c', 'n'};

    // Check message and app log levels.
    if (!force &&
        logLevels.IndexOf(logLevel) < logLevels.IndexOf(commandRootResult.GetValue(optionDebug) ? "d" : commandRootResult.GetValue(optionLogLevel)) ||
        message == null)
        return false;

    Console.Write(
        logLevel == 'd' ? $"\e[0;37m{message}\e[0;0m" : // Debug.
            logLevel == 'i' ? $"\e[0;32m{message}\e[0;0m" : // Success.
                logLevel == 'w' ? $"\e[0;33m{message}\e[0;0m" : // Warning.
                    logLevel == 'e' | logLevel == 'c' ? $"\e[0;31m{message}\e[0;0m" : // Error.
                        message); // Trace and None.

    if (newLine)
        Console.WriteLine();

    return true;
}

bool Debug(string? message, bool newLine = true, bool force = false) => Log(message, newLine, 'd', force);
//bool Info(string? message, bool newLine = true, bool force = false) => Log(message, newLine, 'i', force);
bool Warn(string? message, bool newLine = true, bool force = false) => Log(message, newLine, 'w', force);
bool Error(string? message, bool newLine = true, bool force = false) => Log(message, newLine, 'e', force);

int ExitError(string? message, int code = 1)
{
    Error(message, true, true);
    Error("Run with -h argument to help.", true, true);
    return code;
}

int ExitResult(string? message, int code = 0)
{
    Log(message, true, 'n', true);
    return code;
}

string? ToId(string? value) => string.IsNullOrWhiteSpace(value) ? null : Regex.Replace(value, "[^0-9A-Za-z-]", "-");

/// <summary>
/// Run system command and get result if success.
/// </summary>
/// <param name="fileName">Process file name.</param>
/// <param name="arguments">Startup arguments.</param>
/// <param name="errorValue">Fail return value.</param>
/// <returns>Process standard output or null if error.</returns>
string? TryRun(string fileName, string? arguments, string? errorValue = null)
{
    int exitCode = 0;
    string? output = null, error = null, result = null;

    try
    {
        using (Process process = new())
        {
            process.StartInfo.FileName = fileName;
            process.StartInfo.Arguments = arguments ?? string.Empty;
            process.StartInfo.UseShellExecute = false;
            process.StartInfo.CreateNoWindow = true;
            process.StartInfo.RedirectStandardOutput = true;
            process.StartInfo.RedirectStandardError = true;
            process.ErrorDataReceived += (sender, e) => error += e.Data;

            process.Start();
            process.BeginErrorReadLine();
            output = process.StandardOutput.ReadToEnd().Trim();
            process.WaitForExit();

            exitCode = process.ExitCode;
        }
    }
    catch
    {
        exitCode = 1;
    }

    result = exitCode == 0 ? output : errorValue;
    Debug($"# {result ??  "None"}", true, Log($"{fileName} {arguments} ", false, exitCode == 0 ? 'i' : 'e'));
    Error(exitCode == 0 ? null : error);

    return result;
}

/// <summary>
/// Run system command and get result.
/// </summary>
string Run(string fileName, string? arguments, string errorValue) => TryRun(fileName, arguments, errorValue) ?? errorValue;

string? ReadFile(string fileName)
{
    try
    {
        return File.ReadAllText(fileName, Encoding.UTF8);
    }
    catch
    {
        return null;
    }
}

bool WriteFile(string fileName, string? text)
{
    try
    {
        string? path = Path.GetDirectoryName(fileName)?.Trim();
        if (path != null) // Make directories first.
            Directory.CreateDirectory(path);
        File.WriteAllText(fileName, text, Encoding.UTF8);
        return true;
    }
    catch
    {
        return false;
    }
}

/// <summary>
/// Count the number of commits.
/// </summary>
uint GetCommits(string fromRef, string? toRef = null) => uint.TryParse(Run("git", $"rev-list --count --full-history {(commandRootResult.GetValue(optionIgnoreMerges) ? "--no-merges" : string.Empty)} {fromRef}{(string.IsNullOrWhiteSpace(toRef) ? $"..{toRef}" : string.Empty)}", "0"), out uint result) ? result : 0;

/// <summary>
/// Versioning entry point.
/// </summary>
int OnVersioningStart(ParseResult parseResult)
{
    // Initialize variables to compute a version.
    string? result = null;
    Version version = new();
    //scriptFileName = __file__
    //scriptPath = dirname(scriptFileName)
    string scriptPath = AppContext.BaseDirectory;
    //pythonVersion = Version(sys.version)
    //BUILD_METADATA_REGEX = args.b if args.b else BUILD_METADATA_REGEX
    //VERSION_FILE_NAME = args.f if args.f else VERSION_FILE_NAME
    //ITERATIONS_NUMBER = int(args.n) if args.n else ITERATIONS_NUMBER
    //Log(basename(scriptFileName) + " " + VERSION)

    // Version comparison.
    var versions = (parseResult.GetValue(optionCompare) ?? []).Select(v => new Version(v)).ToArray();
    if (versions.Length == 1)
        return ExitError("Too few arguments to compare.");
    else if (versions.Length > 1)
    {
        for (int compare, i = 0; i < versions.Length - 1; i++)
        {
            compare = versions[i].Compare(versions[i + 1], parseResult.GetValue(optionAssembly));
            result += $"{(compare == 0 ? "=" : compare < 0 ? "<" : ">")} ";
        }
        return ExitResult(result);
    }

    // Validate version from argument.
    if (parseResult.GetValue(optionValidate)?.Length == 1) // Use 'echo $?' to obtain result.
    {
        bool valid = version.Parse(parseResult.GetValue(optionValidate)?[0] ?? string.Empty);
        return ExitResult(version.ToString(), valid ? 0 : 1); // Print parsed version and exit.
    }

    // Try to read version file.
    Version? versionFile = null;
    if (parseResult.GetValue(optionFile) != null || parseResult.GetValue(optionUpdate)) // Relative to the current directory.
    {
        string? fileName = VERSION_FILE_NAME, fileData = ReadFile(fileName);
        if (fileData == null && !Path.IsPathFullyQualified(fileName)) // Relative to the script directory.
            fileData = ReadFile(Path.Combine(scriptPath, fileName));
        // Get version from a file or update it.
        if (fileData != null) // Count the number of commits since a file was changed and add them to the contained version.
        {
            if ((versionFile = new()).Parse(fileData))
            {
                string lastBump = Run("git", $"-c log.showSignature=false log -n 1 --format=format:{GIT_SHA_FORMAT} -- \"{fileName}\"", GIT_COMMIT_EMPTY_SHA);
                if (lastBump == GIT_COMMIT_EMPTY_SHA || string.IsNullOrWhiteSpace(lastBump))
                    Warn($"Could not retrieve last commit for '{fileName}' file. The patch or revision will not be incremented.");
                else
                    versionFile.Add(GetCommits(lastBump, "HEAD"), parseResult.GetValue(optionAssembly));
                
                if (!parseResult.GetValue(optionUpdate))
                    return ExitResult(versionFile.ToString()); // TODO format to string.
            }
            else if (!parseResult.GetValue(optionUpdate))
                return ExitError($"Unable to parse version file content: {fileData}");
        }
        else
            Warn($"Can't read version file: {fileName}");
    }

    // Compute properties before obtain version.
    var gitVersion = new Version(Run("git", "--version", Version.MIN));
    if (gitVersion < new Version(GIT_MIN_VERSION))
        return ExitError($"Unsupported Git version: {gitVersion}{Environment.NewLine}Minimal Git version: {GIT_MIN_VERSION}");

    // Check .git folder existence.
    if (TryRun("git", "rev-parse --show-toplevel") == null)
        return ExitError("Not a git repository: " + Directory.GetCurrentDirectory());

    // Read info.
    string gitCommit = Run("git", $"-c log.showSignature=false log --format=format:{GIT_SHA_FORMAT} -n 1", GIT_COMMIT_EMPTY_SHA);

    // Get a user-friendly reference name.
    string gitRef = Run("git", "rev-parse --abbrev-ref HEAD", "HEAD");
    gitRef = gitRef == "HEAD" ? Run("git", "tag --points-at HEAD", string.Empty)
        .ReplaceLineEndings()
        .Split(Environment.NewLine, StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
        .FirstOrDefault() ?? gitRef : gitRef;

    // Get versions range.
    Version? versionMin = new(), versionMax = null;
    bool refValid = versionMin.Parse(gitRef);
    if (!parseResult.GetValue(optionIgnoreRefs) && refValid)
    {
        versionMax = new(versionMin.ToString(true, true, parseResult.GetValue(optionAssembly)));
        if (versionMax.Minor == null) versionMax.Major++;
        else if (versionMax.PatchOrBuild == null) versionMax.Minor++;
        else if (versionMax.Revision == null) versionMax.PatchOrBuild++;
        else versionMax.Revision++;
    }

    // Iterate tags.
    int j = 0;
    string? tagHash = "HEAD", tagName;
    bool tagValid = false;

    while (!tagValid && tagHash != null && j < ITERATIONS_NUMBER)
    {
        tagName = TryRun("git", $"describe --tags --match=* --abbrev=0 {tagHash}");
        tagHash = tagName != null ? TryRun("git", $"rev-list \"{tagName}\" -n 1") : null; // Alternative: git log -1 --format=format:" + GIT_LONG_SHA_FORMAT + " " + tagName
        if (tagName != null && (tagValid = version.Parse(tagName)))
        {
            if (parseResult.GetValue(optionIgnoreRefs) || !refValid || (versionMin <= version && version < (versionMax ?? Version.Max)))
            {
                break; // Use tag version.
            }
            else
            {
                tagValid = false; // It makes sense to look for the next tag.
                if (versionMin > version) break; // No matching tag: !optionIgnoreRefs && refValid and (versionMin > version || version >= versionMax).
            }
        }
        j++;
        tagHash = tagHash != null ? tagHash + "~1" : null; // Iterate to the next tagged commit.
    }

    // Read version.
    if (tagValid)
        version.Add(GetCommits(tagHash, gitCommit), parseResult.GetValue(optionAssembly)); // Tag detected successfully.
    else if (gitCommit != GIT_COMMIT_EMPTY_SHA && (string.IsNullOrWhiteSpace(tagHash) || parseResult.GetValue(optionIgnoreTags))) version = new Version().Add(GetCommits(gitCommit), parseResult.GetValue(optionAssembly)); // Expand the range of valid values.
    else return ExitError("Unable to obtain valid version.");

    // Update build information.
    version.UpdateMetadata(version.Build == null ? 0 : version.Build, ToId(parseResult.GetValue(optionId)), ToId(gitRef), gitCommit);
    if (parseResult.GetValue(optionUpdate))
    {
        version.UpdateMetadata(versionFile != null && version == versionFile && version.Id == versionFile.Id && version.Ref == versionFile.Ref && version.Commit == versionFile.Commit ? versionFile.Build + 1 : 0); // Rebuild the same commit or it's first build.
        WriteFile(VERSION_FILE_NAME, version.ToString(false, false, parseResult.GetValue(optionAssembly))); // Always save full version information.
    }

    // Print result version.
    return ExitResult(version.ToString());
}

/// <summary>
/// Assembly and SemVer versioning container class.
/// </summary>
public class Version
{
    public const string REGEX = @"v?(?<Major>0|[1-9]\d*)\.(?<Minor>0|[1-9]\d*)(\.(?<PatchOrBuild>0|[1-9]\d*))?(\.(?<Revision>0|[1-9]\d*))?(?:-(?<Prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?<BuildMetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?";
    public const string BUILD_METADATA_REGEX = @"(?:(?<Build>[0-9]+)\.)?(?:(?<Id>[0-9a-zA-Z-]+)\.)?(?<Ref>[0-9a-zA-Z-]+)\.(?<Commit>[0-9a-fA-F-]+)";

    public static readonly string MIN = $"{uint.MinValue}.{uint.MinValue}.{uint.MinValue}";
    public static readonly string MAX = $"{uint.MaxValue}.{uint.MaxValue}.{uint.MaxValue}";
    public static readonly Version Min = new(MIN);
    public static readonly Version Max = new(MAX);

    /// <summary>
    /// Major version.
    /// </summary>
    public uint Major;

    /// <summary>
    /// Minor version.
    /// </summary>
    public uint? Minor;

    /// <summary>
    /// Patch number for semantic versioning or build number for assembly versioning.
    /// </summary>
    public uint? PatchOrBuild;

    /// <summary>
    /// Revision number for assembly versioning.
    /// </summary>
    public uint? Revision;

    /// <summary>
    /// Prerelease label.
    /// </summary>
    public string? Prerelease;

    /// <summary>
    /// Build metadata.
    /// </summary>
    public string? BuildMetadata;

    /// <summary>
    /// Build metadata build identifier.
    /// </summary>
    public uint? Build;

    /// <summary>
    /// Build metadata custom identifier.
    /// </summary>
    public string? Id;

    /// <summary>
    /// Build metadata ref identifier.
    /// </summary>
    public string? Ref;

    /// <summary>
    /// Build metadata commit identifier.
    /// </summary>
    public string? Commit;

    /// <summary>
    /// Default ctor.
    /// </summary>
    public Version() {}

    /// <summary>
    /// Ctor with main fields.
    /// </summary>
    /// <param name="major">Major version.</param>
    /// <param name="minor">Minor version.</param>
    /// <param name="patchOrBuild">Patch number for semantic versioning or build number for assembly versioning.</param>
    /// <param name="revision">Revision number for assembly versioning.</param>
    /// <param name="prerelease">Prerelease version.</param>
    /// <param name="buildMetadata">Build metadata.</param>
    public Version(
        uint major,
        uint? minor = null,
        uint? patchOrBuild = null,
        uint? revision = null,
        string? prerelease = null,
        string? buildMetadata = null)
    {
        Major = major;
        Minor = minor;
        PatchOrBuild = patchOrBuild;
        Revision = revision;
        Prerelease = prerelease;
        BuildMetadata = buildMetadata;
    }

    /// <summary>
    /// Get version object from string.
    /// </summary>
    /// <param name="value">Version string representation.</param>
    public Version(string value) => Parse(value);

    /// <summary>
    /// Get version weight for comparison.
    /// </summary>
    /// <param name="other">Right operand to compare.</param>
    /// <param name="assembly">Use assembly versioning.</param>
    /// <returns>Integer weight of the comparison.</returns>
    public int Compare(Version other, bool assembly)
    {
        int Integer(uint a, uint b) => a < b ? -1 : a > b ? 1 : 0;
        int Identifier(string? a, string? b) => a != null && b == null ? -1 : a == null && b != null ? 1 : a == null && b == null ? 0 : a!.CompareTo(b);

        return 10000 * Integer(Major, other.Major) +
            1000 * Integer(Minor ?? 0, other.Minor ?? 0) +
            100 * Integer(PatchOrBuild ?? 0, other.PatchOrBuild ?? 0) +
            (assembly ? 10 * Integer(Revision ?? 0, other.Revision ?? 0) : 0) +
            // TODO Implement numeric identifier comparison for prerelease version.
            Identifier(Prerelease, other.Prerelease); // Build metadata MUST be ignored when determining version precedence.
    }

    /// <summary>
    /// Update build metadata string and fields from arguments.
    /// </summary>
    /// <param name="build"></param>
    /// <param name="id"></param>
    /// <param name="reference"></param>
    /// <param name="commit"></param>
    public void UpdateMetadata(uint? build = null, string? id = null, string? reference = null, string? commit = null)
    {
        Build = build ?? Build;
        Id = string.IsNullOrWhiteSpace(id) ? Id : id;
        Ref = string.IsNullOrWhiteSpace(reference) ? Ref : reference;
        Commit = string.IsNullOrWhiteSpace(commit) ? Commit : commit;
        // regex, i, type, value, empty, self.BuildMetadata = self.Generate(BUILD_METADATA_REGEX, 0, 1, None, False, "")
    }

    /// <summary>
    /// Parse version from string or regex.
    /// </summary>
    /// <param name="value">Value to parse.</param>
    /// <returns>Parsing result.</returns>
    public bool Parse(string value)
    {
        var match = Regex.Match(value, REGEX);
        // The parsing is considered successful if the major version was parsed.
        if (!match.Success) return false; // Nothing to parse.
        Major = uint.TryParse(match.Groups[nameof(Major)].Value, out uint number) ? number : 1;
        // Parse the remaining fields.
        Minor = uint.TryParse(match.Groups[nameof(Minor)].Value, out number) ? number : null;
        PatchOrBuild = uint.TryParse(match.Groups[nameof(PatchOrBuild)].Value, out number) ? number : null; // SemVer patch or assembly versioning build.
        Revision = uint.TryParse(match.Groups[nameof(Revision)].Value, out number) ? number : null;
        Prerelease = string.IsNullOrWhiteSpace(Prerelease = match.Groups[nameof(Prerelease)].Value) ? null : Prerelease;
        BuildMetadata = string.IsNullOrWhiteSpace(BuildMetadata = match.Groups[nameof(BuildMetadata)].Value) ? null : BuildMetadata;
        // Parse the build metadata.
        if (BuildMetadata == null) return true; // Build metadata is always optional.
        match = Regex.Match(BuildMetadata, BUILD_METADATA_REGEX);
        if (!match.Success) return false; // But strict if presented.
        UpdateMetadata(uint.TryParse(match.Groups[nameof(Build)].Value, out number) ? number : null,
            match.Groups[nameof(Id)].Value,
            match.Groups[nameof(Ref)].Value,
            match.Groups[nameof(Commit)].Value);
        return true;
    }

    /// <summary>
    /// Add a number to version.
    /// </summary>
    /// <param name="value">Integer increment.</param>
    /// <param name="assembly">Use assembly versioning.</param>
    /// <returns>Version instance.</returns>
    public Version Add(uint value, bool assembly)
    {
        if (assembly)
            Revision = value + Revision ?? 0;
        else
            PatchOrBuild = value + PatchOrBuild ?? 0;

        return this;
    }

    /// <summary>
    /// Convert to version string.
    /// </summary>
    /// <param name="noZeros">Do not show zeros if version numbers are not presented.</param>
    /// <param name="shortFormat">Use short version format.</param>
    /// <param name="assembly">Use assembly versioning.</param>
    /// <returns>Version string.</returns>
    public string ToString(bool noZeros, bool shortFormat, bool assembly) => string.Format("{0}{1}{2}{3}{4}{5}",
        Major, // The minimum version should contain at least major number.
        Minor != null ? $".{Minor}" : noZeros && PatchOrBuild == null && (Revision == null || !assembly) ? string.Empty : ".0",
        PatchOrBuild != null ? $".{PatchOrBuild}" : noZeros && (Revision == null || !assembly) ? string.Empty : ".0",
        Revision != null && assembly ? $".{Revision}" : noZeros || !assembly ? string.Empty : ".0",
        Prerelease != null && !shortFormat ? $"-{Prerelease}" : string.Empty,
        BuildMetadata != null && !shortFormat ? $"+{BuildMetadata}" : string.Empty);

    /// <summary>
    /// Convert version to components string.
    /// </summary>
    /// <returns>Space-separated version identifiers.</returns>
    public string ToString(uint? major, uint? minor, uint? patchOrBuild, uint? revision, string? prerelease, string? buildMetadata) => string.Format("{0}{1}{2}{3}{4}{5}",
        major != null ? $"{major} " : string.Empty,
        minor != null ? $"{minor} " : string.Empty,
        patchOrBuild != null ? $"{patchOrBuild} " : string.Empty,
        revision != null ? $"{revision} " : string.Empty,
        prerelease != null ? $"{prerelease} " : string.Empty,
        buildMetadata != null ? $"{buildMetadata} " : string.Empty);

    /// <summary>
    /// Default string representation.
    /// </summary>
    /// <returns></returns>
    public override string ToString() => ToString(false, false, false);

    public bool Equals(Version? obj) => obj != null && Compare(obj, true) == 0;
    public override bool Equals(object? obj) => obj is Version value && Equals(value);
    public override int GetHashCode() => HashCode.Combine(Major, Minor, PatchOrBuild, Revision, Prerelease, BuildMetadata);

    public static bool operator ==(Version? left, Version? right) => Equals(left, null) ? Equals(right, null) : left.Compare(right ?? Min, true) == 0;
    public static bool operator !=(Version? left, Version? right) => !(left == right);
    public static bool operator <=(Version? left, Version? right) => left == null ? right == null : left.Compare(right ?? Min, true) <= 0;
    public static bool operator >=(Version? left, Version? right) => left == null ? right == null : left.Compare(right ?? Min, true) >= 0;
    public static bool operator <(Version? left, Version? right) => left == null ? right != null : left.Compare(right ?? Min, true) < 0;
    public static bool operator >(Version? left, Version? right) => left == null ? false : left.Compare(right ?? Min, true) > 0;
}

#endregion Declarations
