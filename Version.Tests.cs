#!/usr/bin/env -S dotnet --

// File-based unit tests for the version script.
// Author: https://github.com/virtualmode

#:property StartupObject = Program
#:property ExperimentalFileBasedProgramEnableTransitiveDirectives = true

#:package Microsoft.NET.Test.Sdk@18.8.1
#:package NUnit@4.6.1
#:package NUnitLite@4.6.1

#:include Version.cs

using NUnit.Framework;
using NUnitLite;

/// <summary>
/// Startup object with entry point.
/// </summary>
partial class Program
{
    static int Main(string[] args)
    {
        // This invokes the NUnit lite runner programmatically inside the script environment.
        return new AutoRun().Execute(args); // Returns exit code.
    }
}

[TestFixture]
public class VersionTests
{
    [TestCase(0U, null, null, null, null, null, true, false, false, "0")]
    [TestCase(1U, null, null, null, null, null, false, false, false, "1.0.0")]
    [TestCase(2U, null, null, null, null, null, false, false, true, "2.0.0.0")]
    [TestCase(3U, null, null, null, null, null, true, false, false, "3")]
    [TestCase(4U, null, null, null, null, null, true, false, true, "4")]
    [TestCase(5U, null, null, 0U, null, null, true, false, false, "5")]
    [TestCase(6U, null, null, 0U, null, null, true, false, true, "6.0.0.0")]
    [TestCase(7U, 1U, 2U, 3U, "rc.1", null, false, false, false, "7.1.2-rc.1")]
    [TestCase(8U, 1U, 2U, null, null, "build", true, false, true, "8.1.2+build")]
    [TestCase(9U, 1U, null, null, "rc.2", "build", true, false, true, "9.1-rc.2+build")]
    public void ToStringFormat(
        uint major,
        uint? minor,
        uint? patchOrBuild,
        uint? revision,
        string? prerelease,
        string? buildMetadata,
        bool noZeros,
        bool shortFormat,
        bool assembly,
        string expected)
    {
        // Arrange.
        Version version = new(major, minor, patchOrBuild, revision, prerelease, buildMetadata);

        // Act.
        string result = version.ToString(noZeros, shortFormat, assembly);

        // Assert.
        Assert.That(result, Is.EqualTo(expected));
    }

    [TestCase(false, 1U, 2U, 3U)]
    [TestCase(true, 4U, 5U, 9U)]
    public void Add(bool assembly, uint patchOrRevision, uint increment, uint expected)
    {
        // Arrange.
        Version version = new(1, 0, patchOrRevision, patchOrRevision, null, null);

        // Act.
        Version result = version.Add(increment, assembly);

        // Assert.
        Assert.That(result, Is.SameAs(version));
        Assert.That(assembly ? result.Revision : result.PatchOrBuild, Is.EqualTo(expected));
    }

    [Test]
    public void Compare()
    {
        // Arrange.
        Version? alpha = new(1, 0, 0, null, "alpha"),
            alpha1 = new(1, 0, 0, null, "alpha.1"),
            alphaBeta = new(1, 0, 0, null, "alpha.beta"),
            beta = new(1, 0, 0, null, "beta"),
            beta2 = new(1, 0, 0, null, "beta.2"),
            beta11 = new(1, 0, 0, null, "beta.11"),
            rc1 = new(1, 0, 0, null, "rc.1"),
            first = new(1, 0, 0),
            second = new(2, 0, 0),
            secondMinor = new(2, 1, 0),
            secondPatch = new(2, 1, 1),
            assembly = new(1, 2, 3, 4, "gamma"),
            nullVersion = null;

        // Act.
        // Assert.
        Assert.That(alpha.Compare(alpha1, false), Is.EqualTo(-1));
        Assert.That(alpha1.Compare(alphaBeta, false), Is.EqualTo(-1));
        Assert.That(alphaBeta.Compare(beta, false), Is.EqualTo(-1));
        Assert.That(beta.Compare(beta2, false), Is.EqualTo(-1));
        // TODO Implement numeric identifier comparison for prerelease version.
        //Assert.That(beta2.Compare(beta11, false), Is.EqualTo(-1));
        Assert.That(beta11.Compare(rc1, false), Is.EqualTo(-1));
        Assert.That(rc1.Compare(first, false), Is.EqualTo(-1));
        Assert.That(first.Compare(second, false), Is.EqualTo(-10000));
        Assert.That(second.Compare(secondMinor, false), Is.EqualTo(-1000));
        Assert.That(secondMinor.Compare(secondPatch, false), Is.EqualTo(-100));
        Assert.That(secondPatch.Compare(assembly, true), Is.EqualTo(8891));
        // Null checks.
        Assert.That(nullVersion == null, Is.True);
        Assert.That(nullVersion != null, Is.False);
        Assert.That(nullVersion <= null, Is.True);
        Assert.That(nullVersion >= null, Is.True);
        Assert.That(nullVersion < null, Is.False);
        Assert.That(nullVersion > null, Is.False);
        // Min version checks.
        Assert.That(Version.Min == nullVersion, Is.True);
        Assert.That(Version.Min != nullVersion, Is.False);
        Assert.That(Version.Min <= nullVersion, Is.True);
        Assert.That(Version.Min >= nullVersion, Is.True);
        Assert.That(Version.Min < nullVersion, Is.False);
        Assert.That(Version.Min > nullVersion, Is.False);
    }

    [Test]
    public void Parse()
    {
        // Arrange.
        Version version = new();

        // Act.
        bool result = version.Parse("2.3.1-alpha+0.id.ref.f5f8b1f");

        // Assert.
        Assert.That(result, Is.EqualTo(true));
        Assert.That(version.Major, Is.EqualTo(2));
        Assert.That(version.Minor, Is.EqualTo(3));
        Assert.That(version.PatchOrBuild, Is.EqualTo(1));
        Assert.That(version.Prerelease, Is.EqualTo("alpha"));
        Assert.That(version.BuildMetadata, Is.EqualTo("0.id.ref.f5f8b1f"));
        Assert.That(version.Build, Is.EqualTo(0));
        Assert.That(version.Id, Is.EqualTo("id"));
        Assert.That(version.Ref, Is.EqualTo("ref"));
        Assert.That(version.Commit, Is.EqualTo("f5f8b1f"));

        // Act.
        result = version.Parse(string.Empty);

        // Assert.
        Assert.That(result, Is.EqualTo(false));
    }
}
