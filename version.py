# Task to obtain project version.
# Author: https://github.com/virtualmode
# Bad Python link on Linux? sudo ln -s /usr/bin/python3.10 /usr/bin/python
Version = "1.2.0"

# Default properties.
GitMinVersion = "2.5.0"
GitRemote = "origin"
GitDefaultBranch = "main"
GitDefaultCommit = "0000000"
GitDefaultVersion = "0.0.0.0" # General value for SemVer and assembly versions regex.
GitVersionFile = ".version"
GitTagRegex = "*"
# Original regex = r"v?(?P<MAJOR>0|[1-9]\d*)\.(?P<MINOR>0|[1-9]\d*)(\.(?P<PATCH_BUILD>0|[1-9]\d*))?(\.(?P<REVISION>0|[1-9]\d*))?(?:-(?P<PRERELEASE>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<BUILDMETADATA>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
GitBaseVersionRegex = r"v?(?P<MAJOR>0|[1-9]\d*)\.(?P<MINOR>0|[1-9]\d*)(\.(?P<PATCH_BUILD>0|[1-9]\d*))?(\.(?P<REVISION>0|[1-9]\d*))?(?:-(?P<PRERELEASE>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?:(?P<BUILD>[0-9]+)\.)?(?P<BUILDMETADATA>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
GitShortShaFormat = "%h"
GitLongShaFormat = "%H"

# Import packages.
import argparse, os, re, subprocess, sys
from os import environ, chdir, makedirs
from os.path import abspath, isabs, dirname, isdir, join, exists
from re import search, sub, match
from subprocess import call, CalledProcessError, check_output

# Support Python 2.7 and higher.
try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

# Get script path.
ScriptPath = dirname(sys.argv[0])

# Read script arguments.
parser = argparse.ArgumentParser(prog = "py version.py", description = "Script to get an automatic version of a code for the current commit.")
parser.add_argument("-d", "--debug", action="store_true", help = "show debug information")
parser.add_argument("-s", "--semver", action="store_true", help = "show project SemVer instead assembly version")
parser.add_argument("-l", "--long", action="store_true", help = "show project long version instead short")
parser.add_argument("-u", "--update", action="store_true", help = "update version file first")
parser.add_argument("-m", "--ignore-merges", action="store_true", help = "ignore merges")
parser.add_argument("-t", "--ignore-tag", action="store_true", help = "ignore tag version")
parser.add_argument("-n", "--not-ignore-branch", action="store_true", help = "don't ignore version in branch name")
parser.add_argument("-a", "--add", metavar = "BUILDMETADATA", nargs = "?", const = None, help = "add additional info in SemVer metadata format")
parser.add_argument("-b", "--branch", metavar = "NAME", nargs = "?", const = GitDefaultBranch, help = "repository default branch name (default: " + GitDefaultBranch + ")")
parser.add_argument("-f", "--file", metavar = "FILE", nargs = "?", const = GitVersionFile, help = "use version file (if exists) instead a tag (default: " + GitVersionFile + ")")
args = parser.parse_args()
if len(sys.argv) <= 1:
    print("Auto versioning script " + Version)
    parser.print_help()
    sys.exit(1)

# Calculate some properties from arguments.
GitCommits = None
GitVersionMatch = None
GitFileVersionMatch = None
GitDefaultBranch = args.branch if args.branch else GitDefaultBranch
GitCommitsIgnoreMerges = "--no-merges" if args.ignore_merges else ""
GitVersionFile = args.file if args.file else GitVersionFile
GitNotIgnoreBranchVersion = args.not_ignore_branch if args.not_ignore_branch else False
GitIgnoreTagVersion = args.ignore_tag if args.ignore_tag else False
GitUpdateVersionFile = args.update if args.update else False
GitCommit = GitDefaultCommit
GitBranch = GitDefaultBranch

# Container class for version.
class Version:
    Major = 0
    Minor = 0
    PatchBuild = 0
    Revision = 0
    Prerelease = None
    Build = 0
    BuildMetadata = None

# Function for debug purposes.
def log(message):
    if (args.debug):
        print(message)

# Run system command and get result.
def proc(command, errorValue = type(None), errorMessage = None):
    procResult = None
    try:
        procResult = check_output(command, shell = True).decode().strip() if args.debug else check_output(command, shell = True, stderr=DEVNULL).decode().strip()
        log("> " + command + " # " + str(procResult))
        return procResult
    except CalledProcessError:
        log("> " + command + " # " + str(procResult) + " -> " + str(errorValue))
        if errorMessage != None:
            log(errorMessage)
        if errorValue != type(None):
            return errorValue
        else:
            sys.exit(1)

# Read file and return its content.
def readFile(fileName):
    result = None
    if exists(fileName):
        try:
            with open(fileName) as readFile:
                result = readFile.read()
        except:
            result = None
    return result

# Write content to file.
def writeFile(fileName, text):
    # Make directories first.
    filePath = dirname(fileName)
    if filePath and not filePath.isspace() and not exists(filePath):
        makedirs(filePath)
    # Create file and write.
    with open(fileName, "w") as writeFile:
        writeFile.write(text)

# Get version object with regex.
def getVersion(versionMatch):
    # Match default regex version if required.
    if versionMatch == None:
        versionMatch = match(GitBaseVersionRegex, GitDefaultVersion)
    # Read properties.
    major = versionMatch.group("MAJOR")
    minor = versionMatch.group("MINOR")
    patchBuild = versionMatch.group("PATCH_BUILD") # Assembly versioning build or SemVer patch.
    revision = versionMatch.group("REVISION")
    prerelease = versionMatch.group("PRERELEASE")
    build = versionMatch.group("BUILD") # SemVer build information from build metadata.
    buildMetadata = versionMatch.group("BUILDMETADATA")
    # Calculate properties.
    version = Version()
    version.Major = int(major) if major else 0
    version.Minor = int(minor) if minor else 0
    version.PatchBuild = int(patchBuild) if patchBuild else 0
    version.Revision = int(revision) if revision else 0
    version.Prerelease = prerelease
    version.Build = int(build) if build else 0
    version.BuildMetadata = buildMetadata if buildMetadata else (args.add + "." if args.add else "") + sub(r"[^0-9A-Za-z-]", "-", GitBranch) + "." + GitCommit
    return version

# Calculate version from obtained properties.
def returnVersion():
    version = getVersion(GitVersionMatch)
    fileVersion = getVersion(GitFileVersionMatch)
    commits = int(GitCommits) if GitCommits else 0
    # Compute dynamic version part.
    if args.semver:
        version.PatchBuild += commits
    else:
        version.Revision += commits
    # Compute build number.
    if GitUpdateVersionFile:
        if (version.Major == fileVersion.Major and
            version.Minor == fileVersion.Minor and
            version.PatchBuild == fileVersion.PatchBuild and
            version.Revision == fileVersion.Revision and
            version.Prerelease == fileVersion.Prerelease and
            version.BuildMetadata == fileVersion.BuildMetadata):
            version.Build = fileVersion.Build + 1 # Rebuild the same commit.
        else:
            version.Build = 0 # First build for new changes.
    # Create short version string.
    shortResult = str(version.Major) + "." + str(version.Minor) + "." + str(version.PatchBuild)
    if not args.semver:
        shortResult += "." + str(version.Revision)
    # Append long version string.
    longResult = shortResult + ("-" + version.Prerelease if version.Prerelease else "")
    longResult += "+" + (str(version.Build) + "." + version.BuildMetadata if version.Build >= 0 else version.BuildMetadata)
    # Update version file.
    if GitUpdateVersionFile:
        writeFile(GitVersionFile, longResult) # Always save full version information.
    # Output result version.
    print(longResult if args.long else shortResult)
    sys.exit(0)

# Check .git folder existence.
GitRoot = proc("git rev-parse --show-toplevel", "", "Cannot determine Git repository root.")
if GitRoot == "":
    returnVersion()

GitDir = join(GitRoot, ".git")
GitCurrentVersion = search(r"\d+\.\d+\.\d+", proc("git --version", GitMinVersion, "Could not determine git version from output. Required minimum git version is " + GitMinVersion + ".")).group(0)
IsGitWorkTree = proc("git rev-parse --is-inside-work-tree", False)
GitIsDirty = proc("git diff --quiet HEAD", 0)
GitRepositoryUrl = sub(r"://[^/]*@", "://", proc("git config --get remote." + GitRemote + ".url", "")) # Get origin address without user and password.

if IsGitWorkTree:
    GitCommonDir = proc("git rev-parse --git-common-dir")

# Get branch and commit information.
GitSha = proc("git -c log.showSignature=false log --format=format:" + GitLongShaFormat + " -n 1", GitDefaultCommit)
GitCommit = proc("git -c log.showSignature=false log --format=format:" + GitShortShaFormat + " -n 1", GitDefaultCommit)
GitCommitDate = proc("git -c log.showSignature=false show --format=%cI -s", "1987-12-24T11:00:00+07:00")
#GitDefaultBranch = proc('git remote show -n origin | sed -n "/HEAD branch/s/.*: /origin\//p"') # Slow way to use remote connection to obtain real default branch.
GitBranch = proc("git rev-parse --abbrev-ref HEAD", proc("git name-rev --name-only --refs=refs/heads/* --no-undefined --always HEAD", GitDefaultBranch))
GitBaseTag = proc("git describe --tags --match=" + GitTagRegex + " --abbrev=0", GitDefaultVersion)
GitBaseTagCommit = proc("git rev-list \"" + GitBaseTag + "\" -n 1", GitDefaultCommit)
GitTag = proc("git describe --match=" + GitTagRegex + " --tags", GitDefaultVersion)

# Calculate base version from branch name.
indexOfSlash = GitBranch.rfind("/")
GitBaseBranch = GitBranch if indexOfSlash < 0 else GitBranch[indexOfSlash + 1:]
GitForkPoint = proc("git merge-base --fork-point \"" + GitDefaultBranch + "\"",
    proc("git merge-base \"" + GitBranch + "\" \"origin/" + GitDefaultBranch + "\"", None))

# Check that the parent branch is selected correctly.
if GitForkPoint == None:
    log("Could not retrieve first commit where branch '" + GitBranch + "' forked from default '" + GitDefaultBranch + "' branch. Use script -b argument to setup default branch of your repository.")
    returnVersion()

# Check if the branch's parent is before the tag.
GitIsAncestor = False if GitForkPoint == GitSha else (True if proc("git merge-base --is-ancestor " + GitForkPoint + " " + GitBaseTag, False) == "" else False)

# Try to read version from the file.
versionFile = GitVersionFile
GitBaseFile = readFile(versionFile) # Try to read version file relative to the current directory.
if not GitBaseFile and not isabs(GitVersionFile):
    versionFile = ScriptPath + "/" + GitVersionFile
    GitBaseFile = readFile(versionFile) # Try to find default version file in script directory.

# File read successfully.
if GitBaseFile:
    GitFileVersionMatch = match(GitBaseVersionRegex, GitBaseFile)
    # Get commits from version file.
    if not GitUpdateVersionFile:
        GitVersionMatch = GitFileVersionMatch
        # Count the number of commits since a file was changed.
        GitLastBump = proc("git -c log.showSignature=false log -n 1 --format=format:" + GitShortShaFormat + " -- \"" + versionFile + "\"", GitDefaultCommit, "Could not retrieve last commit for " + versionFile + ". Defaulting to its declared version \"" + GitBaseFile + "\" and no additional commits.")
        # Always zero if the file is not present in the repository.
        GitCommits = proc("git rev-list --count --full-history " + GitCommitsIgnoreMerges + " \"" + GitLastBump + "\"..HEAD " + GitRoot, None) if GitLastBump != GitDefaultCommit else None # If there is an error, try searching through the tag.

# Get commits from tag.
GitBranchMatch = match(GitBaseVersionRegex, GitBaseBranch)
if GitCommits == None and not GitIgnoreTagVersion:
    GitVersionMatch = match(GitBaseVersionRegex, GitBaseTag)
    GitCommits = proc("git rev-list --count " + GitCommitsIgnoreMerges + " \"" + GitBaseTagCommit + "\"..\"" + GitCommit + "\"", None) if GitIsAncestor or not GitNotIgnoreBranchVersion or GitBranchMatch == None else None

# Git commits from branch.
if GitCommits == None and GitNotIgnoreBranchVersion and GitBranchMatch:
    GitVersionMatch = GitBranchMatch
    GitCommits = proc("git rev-list --count " + GitCommitsIgnoreMerges + " \"" + GitForkPoint + "\"..HEAD", None)

# Get fallback commits from default version.
if GitCommits == None:
    GitVersionMatch = match(GitBaseVersionRegex, GitDefaultVersion)
    GitCommits = proc("git rev-list --count " + GitCommitsIgnoreMerges + " \"" + GitCommit + "\"", None)

# Write results with versions.
returnVersion()
