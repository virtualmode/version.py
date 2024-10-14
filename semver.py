# Script to obtain project version.
# Author: https://github.com/virtualmode
# Bad Python link on Linux? sudo ln -s /usr/bin/python3.10 /usr/bin/python
VERSION = "1.2.1"

# Import packages.
import argparse, sys
from sys import argv, exit, stdout, version_info
from os import chdir, devnull, environ, getcwd, makedirs
from os.path import abspath, isabs, isdir, dirname, exists, join
from re import findall, match, search, sub
from subprocess import call, check_output
try: from subprocess import DEVNULL # Support null device for Python 2.7 and higher.
except ImportError: DEVNULL = open(devnull, "wb")

# Default properties.
GIT_MIN_VERSION = "2.5.0"
GIT_LONG_SHA_FORMAT = "%H"
GIT_SHORT_SHA_FORMAT = "%h"
GIT_COMMIT_EMPTY_SHA = "0000000"
GIT_COMMIT_EMPTY_VERSION = "0.0.0.0" # General value for SemVer and assembly versions regex.
GIT_PARENT_BRANCH = "main"
GIT_TAG_REGEX = "*"
BUILD_METADATA_REGEX = r"(?:(?P<Build>[0-9]+)\.)?(?:(?P<Id>[0-9a-zA-Z-]+)\.)?(?P<Branch>[0-9a-zA-Z-]+)\.(?P<Commit>[0-9a-fA-F-]+)"
VERSION_REGEX = r"v?(?P<Major>0|[1-9]\d*)\.(?P<Minor>0|[1-9]\d*)(\.(?P<PatchBuild>0|[1-9]\d*))?(\.(?P<Revision>0|[1-9]\d*))?(?:-(?P<Prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<BuildMetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
VERSION_FILE_NAME = ".version"

# Define script arguments.
parser = argparse.ArgumentParser(prog = "py version.py", description = "Script to get an automatic version of a code for the current commit.")
parser.add_argument("-v", "--version", action="store_true", help = "show script version")
parser.add_argument("-d", "--debug", action="store_true", help = "show debug information")
parser.add_argument("-s", "--short", action="store_true", help = "show short version instead of long")
parser.add_argument("-a", "--assembly", action="store_true", help = "show assembly version instead of semantic version")
parser.add_argument("-z", "--no-zeros", action="store_true", help = "show no zeros if version numbers are not presented")
parser.add_argument("-u", "--update", action="store_true", help = "update version file")
parser.add_argument("-m", "--ignore-merges", action="store_true", help = "ignore merges in version increment")
parser.add_argument("-t", "--ignore-tag", action="store_true", help = "ignore version in tag name")
parser.add_argument("-b", "--ignore-branch", action="store_true", help = "ignore version in branch name")
parser.add_argument("--compare", metavar = "VERSION", nargs="+", help = "compare multiple versions with each other: left is less than right if < 0, equal if 0, greater if > 0")
parser.add_argument("--validate", metavar = "VERSION", nargs = "?", const = None, help = "validate version is correct (echo $? is 0 if valid and not valid in other cases)")
parser.add_argument("-p", "--parent", metavar = "BRANCH", nargs = "?", const = GIT_PARENT_BRANCH, help = "parent branch name from which others are forked (default: " + GIT_PARENT_BRANCH + ")")
parser.add_argument("-r", "--regex", metavar = "BUILDMETADATA", nargs = "?", const = BUILD_METADATA_REGEX, help = "strict group-based regular expression for formatting and parsing build metadata (default: " + BUILD_METADATA_REGEX + ")")
parser.add_argument("-i", "--id", metavar = "ID", nargs = "?", const = None, help = "set build metadata custom identifier value")
parser.add_argument("-f", "--file", metavar = "FILE", nargs = "?", const = VERSION_FILE_NAME, help = "use version file (default: " + VERSION_FILE_NAME + ")")
args = parser.parse_args()
if len(argv) <= 1:
    parser.print_help()
    exit(1)

# Functions for debug purposes.
def Info(message): return "\033[0;90m" + message + "\033[0;0m"
def Warn(message): return "\033[0;33m" + message + "\033[0;0m"
def Error(message): return "\033[0;31m" + message + "\033[0;0m"
def Success(message): return "\033[0;32m" + message + "\033[0;0m"
def Log(message):
    if args.debug:
        print(message)

# Check if string is not empty.
def IsNoneOrWhiteSpace(value):
    return not value or value.isspace()

# Run system command and get result.
def Run(command, errorValue = None):
    def Split(command): return ["".join(tuples) for tuples in findall(r"(:?[^\"\'\s]\S*)|[\"\'](:?.*?)[\"\']", command)]
    try: error = False; result = check_output(Split(command), shell = False, stderr = None if args.debug else DEVNULL).decode().strip()
    except: error = True; result = errorValue
    Log((Error(command) if error else Success(command)) + Info(" # " + ("None" if result == None else "\"" + str(result) + "\"")))
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

# Container class for version.
class Version:
    Major = Minor = 0 # Required fields when parsing a version.
    PatchBuild = Revision = Prerelease = BuildMetadata = None # Optional fields.
    Build = Id = Branch = Commit = None # Parsed build metadata fields.

    # Get version weight for comparison.
    def Compare(self, other):
        def CmpObj(a, b): return -1 if a < b else 1 if a > b else 0
        def CmpStr(a, b): return -1 if a != None and b == None else 1 if a == None and b != None else 0 if a == None and b == None else CmpObj(a, b)
        return (10000 * CmpObj(self.Major, other.Major) +
            1000 * CmpObj(self.Minor, other.Minor) +
            100 * CmpObj(self.PatchBuild if self.PatchBuild else 0, other.PatchBuild if other.PatchBuild else 0) +
            10 * CmpObj(self.Revision if self.Revision else 0, other.Revision if other.Revision else 0) +
            CmpStr(self.Prerelease, other.Prerelease)) # Build metadata MUST be ignored when determining version precedence.

    def __lt__(self, other): return self.Compare(other) < 0
    def __gt__(self, other): return self.Compare(other) > 0
    def __le__(self, other): return self.Compare(other) <= 0
    def __ge__(self, other): return self.Compare(other) >= 0
    def __eq__(self, other): return self.Compare(other) == 0
    def __ne__(self, other): return self.Compare(other) != 0

    def __getitem__(self, key): return self.__dict__[key] if key in self.__dict__.keys() else None
    def __setitem__(self, key, value): self.__dict__[key] = value

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

        name = value # Save current group name.
        while (type != TYPE_EOF):
            regex, i, type, value = Next(regex, i, type, value)
            if type == TYPE_GROUP or type == TYPE_NAMED_GROUP: regex, i, type, value, empty1, result1 = self.Generate(regex, i, type, value, empty, ""); empty |= empty1; result += result1
            elif type == TYPE_GROUP_END or type == TYPE_LAZY_END:
                if name: return (regex, i, type, value, name == None, name)
                else: return (regex, i, type, value, False, "" if empty else result)
            elif type == TYPE_CHAR and not name: result += value
        return (regex, i, type, value, empty, result)

    def UpdateMetadata(self, build = None, id = None, branch = None, commit = None):
        # TODO Redesign this function to generate result from build metadata regular expression.
        def Id(field, dot = True): result = str(field if field != None else ""); result += "." if dot and not IsNoneOrWhiteSpace(result) else ""; return result
        self.Build = self.Build if build == None else int(build); self.Id = self.Id if id == None else id; self.Branch = self.Branch if branch == None else branch; self.Commit = self.Commit if commit == None else commit
        self.BuildMetadata = Id(self.Build) + Id(self.Id) + Id(self.Branch) + Id(self.Commit, False)

    # Get version object from string or regex match.
    def __init__(self, value = None):
        if isinstance(value, str if version_info[0] > 2 else basestring): value = search(VERSION_REGEX, value)
        if not value: return
        major = value.group("Major"); self.Major = int(major) if major else 0
        minor = value.group("Minor"); self.Minor = int(minor) if minor else 0
        patchBuild = value.group("PatchBuild"); self.PatchBuild = int(patchBuild) if patchBuild else None # SemVer patch or assembly versioning build.
        revision = value.group("Revision"); self.Revision = int(revision) if revision else None
        self.Prerelease = value.group("Prerelease")
        self.BuildMetadata = value.group("BuildMetadata")
        if not self.BuildMetadata: return
        value = match(BUILD_METADATA_REGEX, self.BuildMetadata)
        self.UpdateMetadata(value.group("Build"), value.group("Id"), value.group("Branch"), value.group("Commit"))

    def ToString(self, noZeros = args.no_zeros, short = args.short, assembly = args.assembly):
        return "{0}.{1}{2}{3}{4}{5}".format(self.Major, self.Minor,
            "" if noZeros and self.PatchBuild == None and self.Revision == None else ".{0}".format(self.PatchBuild if self.PatchBuild else 0),
            "" if noZeros and self.Revision == None or not assembly else ".{0}".format(self.Revision if self.Revision else 0),
            "" if short or not self.Prerelease else "-{0}".format(self.Prerelease),
            "" if short or not self.BuildMetadata else "+{0}".format(self.BuildMetadata))

    def __str__(self): return self.ToString()
    def __radd__(self, other): return other + self.ToString()

    def Add(self, value):
        if args.assembly: self.Revision = value + self.Revision if self.Revision else value
        else: self.PatchBuild = value + self.PatchBuild if self.PatchBuild else value
        return self

def GetCommits(fromCommit, toCommit = None):
    return int(Run("git rev-list --count --full-history " + ignoreMerges + " " + fromCommit + (".." + toCommit if toCommit else ""), 0))

# Show script version.
if args.version:
    print(VERSION)
    exit(0)

# Version comparsion.
if args.compare:
    versions = [Version(i) for i in args.compare]
    if len(versions) <= 1: print(Error("Too few arguments to compare.")); exit(1)
    for j in range(len(versions) - 1): result = versions[j].Compare(versions[j + 1]); stdout.write("{0} ".format("=" if result == 0 else "<" if result < 0 else ">"))
    print("")
    exit(0)

# Validate version from argument.
if args.validate:
    Log(Version(args.validate)) # Log parsed version if you want additional information about result.
    exit(1 if Version(args.validate) == Version() else 0) # Use 'echo $?' to obtain result.

# Compute properties before obtain version.
gitVersion = Version(Run("git --version"))
if gitVersion < Version(GIT_MIN_VERSION):
    print(Error("Unsupported Git version: " + gitVersion + "\nMinimal Git version: " + GIT_MIN_VERSION))
    exit(1)

currentDir = getcwd()
scriptFileName = __file__
scriptPath = dirname(scriptFileName)
pythonVersion = Version(sys.version)

# Check .git folder existence.
gitRoot = Run("git rev-parse --show-toplevel")
if not gitRoot:
    print(Error("Not a git repository: " + currentDir))
    exit(1)

GIT_PARENT_BRANCH = args.parent if args.parent else GIT_PARENT_BRANCH
BUILD_METADATA_REGEX = args.regex if args.regex else BUILD_METADATA_REGEX
VERSION_FILE_NAME = args.file if args.file else VERSION_FILE_NAME
ignoreMerges = "--no-merges" if args.ignore_merges else ""
version = fileVersion = None

if args.file or args.update:
    fileName = VERSION_FILE_NAME
    fileData = ReadFile(fileName)
    if fileData: # Count the number of commits since a file was changed and add them to the contained version.
        lastBump = Run("git -c log.showSignature=false log -n 1 --format=format:" + GIT_SHORT_SHA_FORMAT + " -- \"" + fileName + "\"", GIT_COMMIT_EMPTY_SHA)
        if lastBump == GIT_COMMIT_EMPTY_SHA or not lastBump.strip(): Log(Warn("Could not retrieve last commit for '" + fileName + "' file. The patch or revision will not be incremented automatically."))
        fileVersion = Version(fileData).Add(GetCommits(lastBump, "HEAD") if lastBump != GIT_COMMIT_EMPTY_SHA else 0)

# Read info.
gitSha = Run("git -c log.showSignature=false log --format=format:" + GIT_LONG_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)
gitCommit = Run("git -c log.showSignature=false log --format=format:" + GIT_SHORT_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)
gitTag = Run("git describe --tags --match=" + GIT_TAG_REGEX + " --abbrev=0")
gitTagCommit = Run("git rev-list \"" + gitTag + "\" -n 1", GIT_COMMIT_EMPTY_SHA)
# Obsolete branch detection method.
gitBranch = Run("git rev-parse --abbrev-ref HEAD", Run("git name-rev --name-only --refs=refs/heads/* --no-undefined --always HEAD", GIT_PARENT_BRANCH))
gitForkPoint = Run("git merge-base --fork-point \"" + GIT_PARENT_BRANCH + "\"", Run("git merge-base \"" + gitBranch + "\" \"origin/" + GIT_PARENT_BRANCH + "\"")) # Check the parent branch is selected correctly.
if not gitForkPoint: Log(Error("Could not retrieve first commit where branch '" + gitBranch + "' forked from parent '" + GIT_PARENT_BRANCH + "' branch. Use script -p argument to setup default branch of your repository.")); exit(1)
gitIsAncestor = False if gitForkPoint == gitSha else (True if Run("git merge-base --is-ancestor " + gitForkPoint + " " + gitTag, False) == "" else False) # Check the branch's parent is before the tag.
# Read version.
if not args.ignore_tag and gitTag: version = Version(gitTag).Add(GetCommits(gitTagCommit, gitCommit)) # Read tag version.
elif not args.ignore_branch and gitBranch: version = Version(gitBranch).Add(GetCommits(gitForkPoint, "HEAD")) # Read branch version.
else: version = Version(GIT_COMMIT_EMPTY_VERSION).Add(GetCommits(gitCommit)) # Read default version.
# Update build information.
version.UpdateMetadata(0 if version.Build == None else version.Build, args.id, sub(r"[^0-9A-Za-z-]", "-", gitBranch), gitCommit)
if args.update:
    version.UpdateMetadata(fileVersion.Build + 1 if fileVersion and version == fileVersion and version.Id == fileVersion.Id and version.Branch == fileVersion.Branch and version.Commit == fileVersion.Commit else 0) # Rebuild the same commit or it's first build.
    WriteFile(VERSION_FILE_NAME, version.ToString(False, False)) # Always save full version information.
# Print result version.
print(fileVersion if args.file and not args.update else version)

# DEBUG:
regex, i, type, value, empty, result = version.Generate(BUILD_METADATA_REGEX, 0, 2, None, False, "")
print(result)
print(version.__dict__["Minor"])
version.__dict__["Test"] = 10
print(version.Test)
