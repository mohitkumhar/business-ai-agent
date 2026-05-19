# Release Process

Use this checklist when preparing a ProfitPilot release.

## Before Release

1. Confirm that the default branch is green in CI.
2. Review merged pull requests since the last release.
3. Update `CHANGELOG.md` by moving relevant `Unreleased` entries into a
   versioned section.
4. Update `VERSION` if the release changes the published version.
5. Verify Docker images build locally or in CI.
6. Confirm setup instructions in `README.md` still match the release.

## Versioning

Use semantic versioning when possible:

- Patch version for bug fixes and documentation-only releases.
- Minor version for backwards-compatible features.
- Major version for breaking changes.

## After Release

1. Create a Git tag for the release version.
2. Publish release notes from `CHANGELOG.md`.
3. Watch issues and CI for follow-up reports.
4. Move any unfinished changelog items back under `Unreleased`.
