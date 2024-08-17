# Script to obtain project version.
# Author: https://github.com/virtualmode
# Bad Python link on Linux? sudo ln -s /usr/bin/python3.10 /usr/bin/python
VERSION = "1.2.1"

# Import packages.
import argparse
from sys import argv, exit, version, version_info
from os import chdir, devnull, environ, getcwd, makedirs
from os.path import abspath, isabs, isdir, dirname, exists, join
from re import findall, match, search #, sub
from subprocess import call, check_output
try: from subprocess import DEVNULL # Support null device for Python 2.7 and higher.
except ImportError: DEVNULL = open(devnull, 'wb')

# Default properties.
GIT_MIN_VERSION = "2.5.0"
GIT_LONG_SHA_FORMAT = "%H"
GIT_SHORT_SHA_FORMAT = "%h"
GIT_COMMIT_EMPTY_SHA = "0000000"
GIT_PARENT_BRANCH = "main"
GIT_TAG_REGEX = "*"
BUILD_METADATA_REGEX = r"(?:(?P<BUILD>[0-9]+)\.)?(?P<ID>[0-9a-zA-Z-]+)\.(?P<BRANCH>[0-9a-zA-Z-]+)\.(?P<COMMIT>[0-9a-fA-F-]+)"
VERSION_REGEX = r"v?(?P<MAJOR>0|[1-9]\d*)\.(?P<MINOR>0|[1-9]\d*)(\.(?P<PATCH_BUILD>0|[1-9]\d*))?(\.(?P<REVISION>0|[1-9]\d*))?(?:-(?P<PRERELEASE>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<BUILD_METADATA>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
VERSION_FILE_NAME = ".version"

# Define script arguments.
parser = argparse.ArgumentParser(prog = "py version.py", description = "Script to get an automatic version of a code for the current commit.")
parser.add_argument("-v", "--version", action="store_true", help = "show script version")
parser.add_argument("-d", "--debug", action="store_true", help = "show debug information")
parser.add_argument("-s", "--short", action="store_true", help = "show short version instead of long")
parser.add_argument("-a", "--assembly", action="store_true", help = "show assembly version instead of semantic version")
parser.add_argument("-u", "--update", action="store_true", help = "update version file")
parser.add_argument("-m", "--ignore-merges", action="store_true", help = "ignore merges")
parser.add_argument("-t", "--ignore-tag", action="store_true", help = "ignore tag version")
parser.add_argument("-b", "--ignore-branch", action="store_true", help = "ignore version in branch name")
parser.add_argument("-p", "--parent", metavar = "BRANCH", nargs = "?", const = GIT_PARENT_BRANCH, help = "parent branch name from which others are forked (default: " + GIT_PARENT_BRANCH + ")")
parser.add_argument("-r", "--regex", metavar = "BUILDMETADATA", nargs = "?", const = BUILD_METADATA_REGEX, help = "strict group-based regular expression for formatting and parsing build metadata (default: " + BUILD_METADATA_REGEX + ")")
parser.add_argument("-i", "--identifier", metavar = "ID", nargs = "?", const = None, help = "set build metadata custom identifier value")
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
        if filePath and not filePath.isspace() and not exists(filePath): makedirs(filePath)
        with open(fileName, "w") as writeFile: writeFile.write(text); return True # Create file and write.
    except: return False

# Container class for version.
class Version:
    Major = 0
    Minor = 0
    PatchBuild = 0
    Revision = 0
    Prerelease = None
    BuildMetadata = None

    # Get version weight for comparison.
    def Compare(self, other):
        def CmpObj(a, b): return -1 if a < b else 1 if a > b else 0
        def CmpStr(a, b): return -1 if a != None and b == None else 1 if a == None and b != None else 0 if a == None and b == None else CmpObj(a, b)
        return (10000 * CmpObj(self.Major, other.Major) +
            1000 * CmpObj(self.Minor, other.Minor) +
            100 * CmpObj(self.PatchBuild, other.PatchBuild) +
            10 * CmpObj(self.Revision, other.Revision) +
            CmpStr(self.Prerelease, other.Prerelease)) # Build metadata MUST be ignored when determining version precedence.

    def __lt__(self, other): return self.Compare(other) < 0
    def __gt__(self, other): return self.Compare(other) > 0
    def __le__(self, other): return self.Compare(other) <= 0
    def __ge__(self, other): return self.Compare(other) >= 0
    def __eq__(self, other): return self.Compare(other) == 0
    def __ne__(self, other): return self.Compare(other) != 0

    # Get version object from string or regex match.
    def __init__(self, match = None):
        if isinstance(match, str if version_info[0] > 2 else basestring): match = search(VERSION_REGEX, match)
        if not match: return
        major = match.group("MAJOR"); self.Major = int(major) if major else 0
        minor = match.group("MINOR"); self.Minor = int(minor) if minor else 0
        patchBuild = match.group("PATCH_BUILD"); self.PatchBuild = int(patchBuild) if patchBuild else 0 # SemVer patch or assembly versioning build.
        revision = match.group("REVISION"); self.Revision = int(revision) if revision else 0
        self.Prerelease = match.group("PRERELEASE")
        self.BuildMetadata = match.group("BUILD_METADATA")

    def ToString(version, short = False, assembly = False):
        result = "{0}.{1}.{2}".format(version.Major, version.Minor, version.PatchBuild)
        if assembly: result += ".{0}".format(version.Revision)
        if not short: result += ("-" + version.Prerelease if version.Prerelease else "") + ("+" + version.BuildMetadata if version.BuildMetadata else "")
        return result

    def __str__(self): return self.ToString()
    def __radd__(self, other): return other + self.ToString()

    def Add(self, patchRevision):
        if args.assembly: self.Revision += patchRevision
        else: self.PatchBuild += patchRevision

def GetCommits(fromCommit, toCommit = None):
    return int(Run("git rev-list --count --full-history " + ignoreMerges + " " + fromCommit + (".." + toCommit if toCommit else ""), 0))

# Show script version.
if args.version:
    print(VERSION)
    exit(0)

# Compute properties before obtain version.
gitVersion = Version(Run("git --version"))
if gitVersion < Version(GIT_MIN_VERSION):
    print(Error("Unsupported Git version: " + gitVersion + "\nMinimal Git version: " + GIT_MIN_VERSION))
    exit(1)

# Check .git folder existence.
gitRoot = Run("git rev-parse --show-toplevel")
if not gitRoot:
    print("Not a git repository: " + currentDir)
    exit(1)

currentDir = getcwd()
scriptFileName = __file__
scriptPath = dirname(scriptFileName)
pythonVersion = Version(version)
GIT_PARENT_BRANCH = args.parent if args.parent else GIT_PARENT_BRANCH
ignoreMerges = "--no-merges" if args.ignore_merges else ""

if args.file:
    VERSION_FILE_NAME = args.file
    versionFileName = VERSION_FILE_NAME
    versionFile = ReadFile(versionFileName) # Try read version file from current directory.
    if not versionFile and not isabs(versionFileName):
        versionFileName = join(scriptPath, versionFileName)
        versionFile = ReadFile(versionFileName) # Try to find version file in script directory.

    # File read successfully.
    if versionFile:
        # Count the number of commits since a file was changed and add them to the contained version.
        lastBump = Run("git -c log.showSignature=false log -n 1 --format=format:" + GIT_SHORT_SHA_FORMAT + " -- \"" + versionFileName + "\"", GIT_COMMIT_EMPTY_SHA)
        if lastBump == GIT_COMMIT_EMPTY_SHA or not lastBump.strip(): Log(Warn("Could not retrieve last commit for '" + versionFileName + "' file. The patch or revision will not be incremented automatically."))
        versionFileCommits = GetCommits(lastBump, "HEAD") if lastBump != GIT_COMMIT_EMPTY_SHA else 0
        fileVersion = Version(versionFile)
        fileVersion.Add(versionFileCommits)

        # Get commits from version file.
        #if args.update:
        #    print("")
        #else:
        #    print(fileVersion)

gitSha = Run("git -c log.showSignature=false log --format=format:" + GIT_LONG_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)
gitCommit = Run("git -c log.showSignature=false log --format=format:" + GIT_SHORT_SHA_FORMAT + " -n 1", GIT_COMMIT_EMPTY_SHA)
gitTag = Run("git describe --tags --match=" + GIT_TAG_REGEX + " --abbrev=0")
gitTagCommit = Run("git rev-list \"" + gitTag + "\" -n 1", GIT_COMMIT_EMPTY_SHA)
# Obsolete branch detection method.
gitBranch = Run("git rev-parse --abbrev-ref HEAD", Run("git name-rev --name-only --refs=refs/heads/* --no-undefined --always HEAD", GIT_PARENT_BRANCH))
gitForkPoint = Run("git merge-base --fork-point \"" + GIT_PARENT_BRANCH + "\"", Run("git merge-base \"" + gitBranch + "\" \"origin/" + GIT_PARENT_BRANCH + "\""))
# Check the parent branch is selected correctly.
if not gitForkPoint:
    Log(Error("Could not retrieve first commit where branch '" + gitBranch + "' forked from parent '" + GIT_PARENT_BRANCH + "' branch. Use script -p argument to setup default branch of your repository."))
    exit(1) # RETURN VERSION
gitIsAncestor = False if gitForkPoint == gitSha else (True if Run("git merge-base --is-ancestor " + gitForkPoint + " " + gitTag, False) == "" else False) # Check the branch's parent is before the tag.

# Tag
if not args.ignore_tag and not gitTag:
    tagVersion = Version(gitTag)
    if tagVersion:
        gitCommits = GetCommits(gitTagCommit, gitCommit)

# Branch
elif not args.ignore_branch and not gitBranch:
    branchVersion = Version(gitBranch)
    if branchVersion:
        gitCommits = GetCommits(gitForkPoint, "HEAD")

# Commits from start
else:
    gitCommits = GetCommits(gitCommit)

# TODO
# Сделать возможность сравнивать версии переданные через параметр.
# Сделать возможность проверить является ли переданный параметр версией.
