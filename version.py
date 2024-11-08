# Script to obtain project version.
# Author: https://github.com/virtualmode
VERSION = "1.2.3"
GIT_MIN_VERSION = "2.5.0"
GIT_LONG_SHA_FORMAT = "%H"
GIT_SHORT_SHA_FORMAT = "%h"
GIT_COMMIT_EMPTY_SHA = "0000000"
BUILD_METADATA_REGEX = r"(?:(?P<Build>[0-9]+)\.)?(?:(?P<Id>[0-9a-zA-Z-]+)\.)?(?P<Ref>[0-9a-zA-Z-]+)\.(?P<Commit>[0-9a-fA-F-]+)"
VERSION_REGEX = r"v?(?P<Major>0|[1-9]\d*)\.(?P<Minor>0|[1-9]\d*)(\.(?P<PatchBuild>0|[1-9]\d*))?(\.(?P<Revision>0|[1-9]\d*))?(?:-(?P<Prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<BuildMetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
VERSION_FILE_NAME = ".version"
ITERATIONS_NUMBER = 3

# Import packages.
import argparse, sys
from sys import exit, stdout, version_info
from os import devnull, getcwd, makedirs
from os.path import dirname, exists, isabs, join
from re import findall, match, search, sub
from subprocess import check_output
try: from subprocess import DEVNULL # Support null device for Python 2.7 and higher.
except ImportError: DEVNULL = open(devnull, "wb")

# Define script arguments.
parser = argparse.ArgumentParser(prog = "py version.py", description = "Script to get an automatic version of a code for the current commit.")
parser.add_argument("-v", "--version", action="store_true", help = "show script version")
parser.add_argument("-d", "--debug", action="store_true", help = "show debug information")
parser.add_argument("-s", "--short", action="store_true", help = "show short version instead of long")
parser.add_argument("-a", "--assembly", action="store_true", help = "show assembly version instead of semantic version")
parser.add_argument("-z", "--no-zeros", action="store_true", help = "show no zeros if version numbers are not presented")
parser.add_argument("-u", "--update", action="store_true", help = "update version file")
parser.add_argument("-m", "--ignore-merges", action="store_true", help = "ignore merges in version increment")
parser.add_argument("-t", "--ignore-tags", action="store_true", help = "ignore tags with invalid versions")
parser.add_argument("-r", "--ignore-refs", action="store_true", help = "ignore detached state and branch versions")
parser.add_argument("-i", metavar = "ID", nargs = "?", const = None, help = "set build metadata custom identifier value")
parser.add_argument("-f", metavar = "FILE", nargs = "?", const = VERSION_FILE_NAME, help = "use version file (default: \"" + VERSION_FILE_NAME + "\")")
parser.add_argument("-b", metavar = "REGEX", nargs = "?", const = BUILD_METADATA_REGEX, help = "strict group-based regular expression for formatting and parsing build metadata (default: \"" + BUILD_METADATA_REGEX + "\")")
parser.add_argument("-n", metavar = "NUMBER", nargs = "?", const = ITERATIONS_NUMBER, help = "Limit script iterations (default: " + str(ITERATIONS_NUMBER) + ")")
parser.add_argument("--compare", metavar = "VERSION", nargs="+", help = "compare multiple versions with each other: left is less than right if < sign is output, equal if =, greater if >")
parser.add_argument("--validate", metavar = "VERSION", nargs = "?", const = None, help = "validate version is correct (echo $? is 0 if valid and not valid in other cases)")
args = parser.parse_args()

# Functions for debug purposes.
def Info(message): return "\033[0;37m" + message + "\033[0;0m"
def Warn(message): return "\033[0;33m" + message + "\033[0;0m"
def Error(message): return "\033[0;31m" + message + "\033[0;0m"
def Success(message): return "\033[0;32m" + message + "\033[0;0m"
def ExitError(message, code = 1): print(Error(message)); print(Error("Run with -h argument to help.")); exit(code)
def Log(message):
    if args.debug:
        print(message)

# String functions.
def IsString(value): return isinstance(value, str if version_info[0] > 2 else basestring)
def IsNoneOrWhiteSpace(value): return value == None or value == "" or value.isspace()

# Run system command and get result.
def Run(command, errorValue = None):
    def Split(command): return ["".join(tuples) for tuples in findall(r"(:?[^\"\'\s]\S*)|[\"\'](:?.*?)[\"\']", command)]
    try: error = False; result = check_output(Split(command), shell = False, stderr = None if args.debug else DEVNULL).decode().strip()
    except: error = True; result = errorValue
    Log((Warn(command) if error else Success(command)) + Info(" # " + ("None" if result == None else "\"" + str(result) + "\"")))
    return result

# Read file and return its content.
def ReadFile(fileName):
    try:
        with open(fileName) as readFile: return readFile.read()
    except: return None

# Write content to file.
def WriteFile(fileName, text):
    try:
        filePath = dirname(fileName) # Make directories first.
        if not IsNoneOrWhiteSpace(filePath) and not exists(filePath): makedirs(filePath)
        with open(fileName, "w") as writeFile: writeFile.write(text); return True # Create file and write.
    except: return False

# Count the number of commits.
def GetCommits(fromRef, toRef = None):
    return int(Run("git rev-list --count --full-history " + ("--no-merges " if args.ignore_merges else "") + fromRef + (".." + toRef if toRef else ""), 0))

# Container class for version.
class Version:
    Major = Minor = 0 # Required fields when parsing a version.
    PatchBuild = Revision = Prerelease = BuildMetadata = None # Optional fields.
    Build = Id = Ref = Commit = None # Parsed build metadata fields.

    # Get version weight for comparison.
    def Compare(self, other):
        def CmpObj(a, b): return -1 if a < b else 1 if a > b else 0
        def CmpStr(a, b): return -1 if a != None and b == None else 1 if a == None and b != None else 0 if a == None and b == None else CmpObj(a, b)
        return (10000 * CmpObj(self.Major, other.Major) +
            1000 * CmpObj(self.Minor, other.Minor) +
            100 * CmpObj(self.PatchBuild if self.PatchBuild else 0, other.PatchBuild if other.PatchBuild else 0) +
            10 * CmpObj(self.Revision if self.Revision else 0, other.Revision if other.Revision else 0) +
            CmpStr(self.Prerelease, other.Prerelease)) # Build metadata MUST be ignored when determining version precedence.

    # Regex generator for customizing output.
    def Generate(self, regex, i, type, value, empty, result):
        TYPE_EOF = 0; TYPE_ERROR = 1; TYPE_CHAR = 2; TYPE_GROUP = 3; TYPE_NAMED_GROUP = 4; TYPE_GROUP_END = 5; TYPE_LAZY_END = 6
        def Next(regex, i, type, value): # Regex simple lexer.
            while i < len(regex):
                if i + 3 < len(regex) and regex[i] == "(" and regex[i + 1] == "?":
                    j = i = i + 3 if regex[i + 2] == "P" else i + 2 # Skip P syntax.
                    if regex[i] not in {"<", "'"}: return (regex, i, TYPE_GROUP, None)
                    while i < len(regex):
                        i += 1
                        if regex[i] in {">", "'"}: return (regex, i + 1, TYPE_NAMED_GROUP, regex[j + 1:i])
                    return (regex, i, TYPE_ERROR, None)
                elif regex[i] == ")":
                    if i + 1 < len(regex) and regex[i + 1] == "?": return (regex, i + 2, TYPE_LAZY_END, None) # It's not right name for the lexeme.
                    else: return (regex, i + 1, TYPE_GROUP_END, None)
                elif i + 1 < len(regex) and regex[i] == "\\": return (regex, i + 2, TYPE_CHAR, regex[i + 1])
                elif regex[i].isalnum() or regex[i] in {" ", "-", "_"}: return (regex, i + 1, TYPE_CHAR, regex[i])
                i += 1 # Other regex features are not supported.
            return (regex, i, TYPE_EOF, None)
        # Syntax parser with generator.
        name = value # Save current group name.
        while (type != TYPE_EOF):
            regex, i, type, value = Next(regex, i, type, value)
            if type == TYPE_GROUP or type == TYPE_NAMED_GROUP: regex, i, type, value, empty1, result1 = self.Generate(regex, i, type, value, empty, ""); empty |= empty1; result += result1
            elif type == TYPE_GROUP_END or type == TYPE_LAZY_END:
                if name: field = "" if self[name] == None else str(self[name]); return (regex, i, type, value, IsNoneOrWhiteSpace(field), field)
                else: return (regex, i, type, value, False, "" if empty and type == TYPE_LAZY_END else result)
            elif type == TYPE_CHAR and not name: result += value
        return (regex, i, type, value, empty, result)

    # Update build metadata string and fields from arguments.
    def UpdateMetadata(self, build = None, id = None, ref = None, commit = None):
        self.Build = self.Build if build == None else int(build)
        self.Id = self.Id if id == None else id
        self.Ref = self.Ref if ref == None else ref
        self.Commit = self.Commit if commit == None else commit
        regex, i, type, value, empty, self.BuildMetadata = self.Generate(BUILD_METADATA_REGEX, 0, 1, None, False, "")

    # Parse version from string or regex.
    def Parse(self, value = None):
        # Determine the value type and choose action.
        if IsString(value): value = search(VERSION_REGEX, value)
        if value == None: return False # Nothing to parse.
        # The parsing is considered successful if the major version was parsed.
        major = value.group("Major")
        if major == None: return False
        self.Major = int(major)
        # Parse the remaining fields.
        minor = value.group("Minor"); self.Minor = None if minor == None else int(minor)
        patchBuild = value.group("PatchBuild"); self.PatchBuild = None if patchBuild == None else int(patchBuild) # SemVer patch or assembly versioning build.
        revision = value.group("Revision"); self.Revision = None if revision == None else int(revision)
        self.Prerelease = value.group("Prerelease")
        self.BuildMetadata = value.group("BuildMetadata")
        # Parse the build metadata.
        if not self.BuildMetadata: return True
        value = match(BUILD_METADATA_REGEX, self.BuildMetadata)
        self.UpdateMetadata(value.group("Build"), value.group("Id"), value.group("Ref"), value.group("Commit"))
        return True

    # Convert version to string.
    def ToString(self, noZeros = args.no_zeros, short = args.short, assembly = args.assembly):
        return "{0}.{1}{2}{3}{4}{5}".format(self.Major, self.Minor,
            "" if noZeros and self.PatchBuild == None and self.Revision == None else ".{0}".format(self.PatchBuild if self.PatchBuild else 0),
            "" if noZeros and self.Revision == None or not assembly else ".{0}".format(self.Revision if self.Revision else 0),
            "" if short or not self.Prerelease else "-{0}".format(self.Prerelease),
            "" if short or not self.BuildMetadata else "+{0}".format(self.BuildMetadata))

    # Add a number to version.
    def Add(self, value):
        if args.assembly: self.Revision = value + self.Revision if self.Revision else value
        else: self.PatchBuild = value + self.PatchBuild if self.PatchBuild else value
        return self

    # Operator overloading.
    def __init__(self, value = None): self.Parse(value) # Get version object from string or regex match.
    def __str__(self): return self.ToString()
    def __radd__(self, other): return other + self.ToString()
    def __setitem__(self, key, value): self.__dict__[key] = value
    def __getitem__(self, key): return self.__dict__[key] if key in self.__dict__.keys() else None
    def __lt__(self, other): return self.Compare(other) < 0
    def __gt__(self, other): return self.Compare(other) > 0
    def __le__(self, other): return self.Compare(other) <= 0
    def __ge__(self, other): return self.Compare(other) >= 0
    def __eq__(self, other): return self.Compare(other) == 0
    def __ne__(self, other): return self.Compare(other) != 0

# Show script version.
if args.version:
    print(VERSION)
    exit(0)

# Version comparsion.
if args.compare:
    versions = [Version(i) for i in args.compare]
    if len(versions) <= 1: ExitError("Too few arguments to compare.")
    for j in range(len(versions) - 1): result = versions[j].Compare(versions[j + 1]); stdout.write("{0} ".format("=" if result == 0 else "<" if result < 0 else ">"))
    print("")
    exit(0)

# Validate version from argument.
if args.validate:
    version = Version(); valid = version.Parse(args.validate)
    Log(version) # Log parsed version if you want additional information about result.
    exit(0 if valid else 1) # Use 'echo $?' to obtain result.

# Compute properties before obtain version.
gitVersion = Version(Run("git --version"))
if gitVersion < Version(GIT_MIN_VERSION):
    ExitError("Unsupported Git version: " + gitVersion + "\nMinimal Git version: " + GIT_MIN_VERSION)

# Check .git folder existence.
currentDir = getcwd()
gitRoot = Run("git rev-parse --show-toplevel")
if not gitRoot:
    ExitError("Not a git repository: " + currentDir)

# Initialize variables to compute a version.
scriptFileName = __file__
scriptPath = dirname(scriptFileName)
pythonVersion = Version(sys.version)
BUILD_METADATA_REGEX = args.b if args.b else BUILD_METADATA_REGEX
VERSION_FILE_NAME = args.f if args.f else VERSION_FILE_NAME
ITERATIONS_NUMBER = int(args.n) if args.n else ITERATIONS_NUMBER

# Try to read version file.
versionFile = None
if args.f or args.update: # Relative to the current directory.
    fileName = VERSION_FILE_NAME
    fileData = ReadFile(fileName)
    if not fileData and not isabs(fileName): # Relative to the script directory.
        fileData = ReadFile(join(scriptPath, fileName))
    # Get version from a file or update it.
    if fileData: # Count the number of commits since a file was changed and add them to the contained version.
        lastBump = Run("git -c log.showSignature=false log -n 1 --format=format:" + GIT_SHORT_SHA_FORMAT + " -- \"" + fileName + "\"", GIT_COMMIT_EMPTY_SHA)
        if lastBump == GIT_COMMIT_EMPTY_SHA or not lastBump.strip(): Log(Warn("Could not retrieve last commit for '" + fileName + "' file. The patch or revision will not be incremented automatically."))
        versionFile = Version(fileData).Add(GetCommits(lastBump, "HEAD") if lastBump != GIT_COMMIT_EMPTY_SHA else 0)
    else: Log(Warn("Can't read version file: " + fileName))

# Read info.
gitCommit = Run("git -c log.showSignature=false log --format=format:" + GIT_SHORT_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)

# Get a user-friendly reference name.
gitRef = Run("git rev-parse --abbrev-ref HEAD", "HEAD")
if gitRef == "HEAD":
    gitRefs = Run("git tag --points-at HEAD", "").splitlines()
    if len(gitRefs) > 0: gitRef = gitRefs[0]

# Get versions range.
versionMin = Version(); versionMax = None
refValid = versionMin.Parse(gitRef)
if not args.ignore_refs and refValid:
    versionMax = Version(versionMin.ToString(True, True, args.assembly))
    if versionMax.Minor == None: versionMax.Major += 1
    elif versionMax.PatchBuild == None: versionMax.Minor += 1
    elif versionMax.Revision == None: versionMax.PatchBuild += 1
    else: versionMax.Revision += 1

# Iterate tags.
i = 0; tagHash = "HEAD"; tagName = None; tagValid = False; version = Version()
while (not tagValid and tagHash and i < ITERATIONS_NUMBER):
    tagName = Run("git describe --tags --match=* --abbrev=0 " + tagHash)
    tagHash = Run("git rev-list \"" + tagName + "\" -n 1") if tagName else None # Alternative: git log -1 --format=format:" + GIT_LONG_SHA_FORMAT + " " + tagName
    tagValid = version.Parse(tagName)
    if tagValid:
        if args.ignore_refs or not refValid or versionMin <= version < versionMax: break # Use tag version.
        elif versionMin > version: tagValid = False; break # No matching tag: not args.ignore_refs and refValid and (versionMin > version or version >= versionMax)
        else: tagValid = False # It makes sense to look for the next tag.
    i += 1; tagHash = tagHash + "~1" if tagHash else None # Iterate to the next tagged commit.

# Read version.
if tagValid: version = version.Add(GetCommits(tagHash, gitCommit)) # Tag detected successfully.
elif gitCommit != GIT_COMMIT_EMPTY_SHA and (not tagHash or args.ignore_tags): version = Version().Add(GetCommits(gitCommit)) # Expand the range of valid values.
else: ExitError("Unable to obtain valid version.")

# Update build information.
version.UpdateMetadata(0 if version.Build == None else version.Build, args.i, sub(r"[^0-9A-Za-z-]", "-", gitRef), gitCommit)
if args.update:
    version.UpdateMetadata(versionFile.Build + 1 if versionFile and version == versionFile and version.Id == versionFile.Id and version.Ref == versionFile.Ref and version.Commit == versionFile.Commit else 0) # Rebuild the same commit or it's first build.
    WriteFile(VERSION_FILE_NAME, version.ToString(False, False)) # Always save full version information.

# Print result version.
print(versionFile if not args.update and args.f and versionFile else version)
