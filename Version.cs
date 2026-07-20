#!/usr/bin/env -S dotnet --

// File-based app to obtain source version.
// Author: https://github.com/virtualmode

#:property Version = 1.2.8
#:property ToolCommandName = version
//#:property WarningLevel = 0

#:package System.CommandLine@2.0.10

using System.CommandLine;
using System.Diagnostics;
using System.Reflection;
using System.Text.RegularExpressions;

// Get current assembly information.
Assembly assembly = Assembly.GetExecutingAssembly();
System.Version assemblyVersion = assembly.GetName().Version ?? new System.Version(1, 0, 0, 0);
string assemblyInformationalVersion = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "1.0.0";

// Log level option initialization.
Option<string> optionLogLevel = new("--log-level", ["-l"])
{
    HelpName = "LEVEL",
    Description = "Sets log severity level: t[race], d[ebug], i[nformation], w[arning], e[rror], c[ritical] and n[one]",
    DefaultValueFactory = parseResult => "n",
};

// CommandLine automatically treats Option<bool> targets as flags that do not require an attached value.
Option<bool> optionDebug = new("--debug", ["-d"])
{
    Description = "Show debug information alias for log level"
};

// Compare multiple versions.
Option<string[]> optionCompare = new("--compare")
{
    HelpName = "VERSION",
    Description = "compare multiple versions with each other: left is less than right if < sign is output, equal if =, greater if >",
    AllowMultipleArgumentsPerToken = true,
};

// Root command to parse arguments.
RootCommand commandRoot = new($"Version script {assemblyVersion.Major}.{assemblyVersion.Minor}.{assemblyVersion.Build} to get automatic source version of the commit.") // Commands already has help and version options by default.
{
    optionLogLevel,
    optionDebug,
    optionCompare,
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
bool Info(string? message, bool newLine = true, bool force = false) => Log(message, newLine, 'i', force);
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

/// <summary>
/// Run system command and get result.
/// </summary>
/// <param name="fileName">Process file name.</param>
/// <param name="arguments">Startup arguments.</param>
/// <param name="errorValue">Fail return value.</param>
/// <returns>Process standard output.</returns>
string? Run(string fileName, string? arguments, string? errorValue = null)
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
/// Versioning entry point.
/// </summary>
int OnVersioningStart(ParseResult parseResult)
{
    //# Initialize variables to compute a version.
    //scriptFileName = __file__
    //scriptPath = dirname(scriptFileName)
    //pythonVersion = Version(sys.version)
    //BUILD_METADATA_REGEX = args.b if args.b else BUILD_METADATA_REGEX
    //VERSION_FILE_NAME = args.f if args.f else VERSION_FILE_NAME
    //ITERATIONS_NUMBER = int(args.n) if args.n else ITERATIONS_NUMBER
    //Log(basename(scriptFileName) + " " + VERSION)

    //# Show script version.
    //if args.version:
    //    version = Version()
    //    version.Parse(VERSION)
    //    ExitResult(version)

    // Version comparison.
    string[] compareValues = parseResult.GetValue(optionCompare) ?? [];
    if (compareValues.Length == 1)
        return ExitError("Too few arguments to compare.");

    // if args.compare:
    //     versions = [Version(i) for i in args.compare]
    //     if len(versions) <= 1: ExitError("Too few arguments to compare.")
    //     for j in range(len(versions) - 1): result = versions[j].Compare(versions[j + 1]); stdout.write("{0} ".format("=" if result == 0 else "<" if result < 0 else ">"))
    //     ExitResult("")

    // # Validate version from argument.
    // if args.validate: # Use 'echo $?' to obtain result.
    //     version = Version()
    //     valid = version.Parse(args.validate)
    //     ExitResult(version, 0 if valid else 1) # Print parsed version and exit.

    // # Try to read version file.
    // versionFile = None
    // if args.f or args.update: # Relative to the current directory.
    //     fileName = VERSION_FILE_NAME
    //     fileData = ReadFile(fileName)
    //     if not fileData and not isabs(fileName): # Relative to the script directory.
    //         fileData = ReadFile(join(scriptPath, fileName))
    //     # Get version from a file or update it.
    //     if fileData: # Count the number of commits since a file was changed and add them to the contained version.
    //         versionFile = Version()
    //         if versionFile.Parse(fileData):
    //             lastBump = Run("git -c log.showSignature=false log -n 1 --format=format:" + GIT_SHORT_SHA_FORMAT + " -- \"" + fileName + "\"", GIT_COMMIT_EMPTY_SHA)
    //             if lastBump == GIT_COMMIT_EMPTY_SHA or IsNoneOrWhiteSpace(lastBump): Log(Warn("Could not retrieve last commit for '" + fileName + "' file. The patch or revision will not be incremented."))
    //             else: versionFile.Add(GetCommits(lastBump, "HEAD"))
    //             if not args.update: ExitResult(versionFile)
    //         elif not args.update: ExitError("Unable to parse version file content: " + fileData.strip())
    //     else: Log(Warn("Can't read version file: " + fileName))

    // # Compute properties before obtain version.
    // gitVersion = Version(Run("git --version"))
    // if gitVersion < Version(GIT_MIN_VERSION):
    //     ExitError("Unsupported Git version: " + gitVersion + "\nMinimal Git version: " + GIT_MIN_VERSION)

    // # Check .git folder existence.
    // currentDir = getcwd()
    // gitRoot = Run("git rev-parse --show-toplevel")
    // if not gitRoot:
    //     ExitError("Not a git repository: " + currentDir)

    // # Read info.
    // gitCommit = Run("git -c log.showSignature=false log --format=format:" + GIT_SHORT_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)

    // # Get a user-friendly reference name.
    // gitRef = Run("git rev-parse --abbrev-ref HEAD", "HEAD")
    // if gitRef == "HEAD":
    //     gitRefs = Run("git tag --points-at HEAD", "").splitlines()
    //     if len(gitRefs) > 0: gitRef = gitRefs[0]

    // # Get versions range.
    // versionMin = Version(); versionMax = None
    // refValid = versionMin.Parse(gitRef)
    // if not args.ignore_refs and refValid:
    //     versionMax = Version(versionMin.ToString(True, True, args.assembly, None, None, None, None, None, None))
    //     if versionMax.Minor == None: versionMax.Major += 1
    //     elif versionMax.PatchBuild == None: versionMax.Minor += 1
    //     elif versionMax.Revision == None: versionMax.PatchBuild += 1
    //     else: versionMax.Revision += 1

    // # Iterate tags.
    // i = 0; tagHash = "HEAD"; tagName = None; tagValid = False; version = Version()
    // while (not tagValid and tagHash and i < ITERATIONS_NUMBER):
    //     tagName = Run("git describe --tags --match=* --abbrev=0 " + tagHash)
    //     tagHash = Run("git rev-list \"" + tagName + "\" -n 1") if tagName else None # Alternative: git log -1 --format=format:" + GIT_LONG_SHA_FORMAT + " " + tagName
    //     tagValid = version.Parse(tagName)
    //     if tagValid:
    //         if args.ignore_refs or not refValid or versionMin <= version < versionMax: break # Use tag version.
    //         elif versionMin > version: tagValid = False; break # No matching tag: not args.ignore_refs and refValid and (versionMin > version or version >= versionMax)
    //         else: tagValid = False # It makes sense to look for the next tag.
    //     i += 1; tagHash = tagHash + "~1" if tagHash else None # Iterate to the next tagged commit.

    // # Read version.
    // if tagValid: version = version.Add(GetCommits(tagHash, gitCommit)) # Tag detected successfully.
    // elif gitCommit != GIT_COMMIT_EMPTY_SHA and (not tagHash or args.ignore_tags): version = Version().Add(GetCommits(gitCommit)) # Expand the range of valid values.
    // else: ExitError("Unable to obtain valid version.")

    // # Update build information.
    // version.UpdateMetadata(0 if version.Build == None else version.Build, ToId(args.i), ToId(gitRef), gitCommit)
    // if args.update:
    //     version.UpdateMetadata(versionFile.Build + 1 if versionFile and version == versionFile and version.Id == versionFile.Id and version.Ref == versionFile.Ref and version.Commit == versionFile.Commit else 0) # Rebuild the same commit or it's first build.
    //     WriteFile(VERSION_FILE_NAME, version.ToString(False, False, args.assembly, None, None, None, None, None, None)) # Always save full version information.

    // # Print result version.
    // ExitResult(version)

    Version version = new("2.3.1-alpha+0.id.ref.f5f8b1f");
    Log("Test", true, 'e');
    Run("git", "--version");

    return ExitResult("Result");
}

/// <summary>
/// Assembly and SemVer versioning container class.
/// </summary>
public class Version
{
    public const string REGEX = @"v?(?<Major>0|[1-9]\d*)\.(?<Minor>0|[1-9]\d*)(\.(?<PatchOrBuild>0|[1-9]\d*))?(\.(?<Revision>0|[1-9]\d*))?(?:-(?<Prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?<BuildMetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?";
    public const string BUILD_METADATA_REGEX = @"(?:(?<Build>[0-9]+)\.)?(?:(?<Id>[0-9a-zA-Z-]+)\.)?(?<Ref>[0-9a-zA-Z-]+)\.(?<Commit>[0-9a-fA-F-]+)";

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
    public void UpdateMetadata(uint? build, string? id, string? reference, string? commit)
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
}

#endregion Declarations
