# Release Automation Setup

This repository includes automated release processing when the `dev` branch is merged into `master`. This document explains how to set up the required configuration.

## GitHub Environment Setup

The release workflow requires a `production` environment with manual approval. To set this up:

1. Go to **Settings** → **Environments** in your GitHub repository
2. Click **New environment**
3. Name it: `production`
4. Under **Protection rules**:
   - ✅ Check **Required reviewers**
   - Add repository owners/administrators who can approve releases
   - Set **1** required reviewer minimum
5. Click **Save protection rules**

## Required Secrets

Add these secrets in **Settings** → **Secrets and variables** → **Actions**:

### Repository Secrets
- `QUAY_USERNAME` - Username for quay.io container registry  
- `QUAY_PASSWORD` - Password/token for quay.io container registry

### PyPI Publishing (Trusted Publishers)

This repository uses **PyPI Trusted Publishers** for secure, token-free publishing to PyPI. No `PYPI_API_TOKEN` secret is required.

#### PyPI Trusted Publisher Setup
1. Go to [PyPI Project Management](https://pypi.org/manage/project/gxabm/settings/publishing/) 
2. Add a new **Trusted Publisher**:
   - **Repository name**: `galaxyproject/gxabm`
   - **Workflow filename**: `release.yml`  
   - **Environment name**: (leave empty)
3. The workflow automatically authenticates using OIDC tokens from GitHub Actions

### How to get container registry tokens:

#### Quay.io Credentials
1. Log in to [quay.io](https://quay.io/)
2. Go to **Account Settings** → **Robot Accounts**
3. Create a new robot account for `galaxyproject/abm` repository
4. Grant **Write** permissions
5. Use the robot account credentials

## Release Process

### Automatic Trigger
The release process automatically triggers when:
1. A pull request from `dev` is merged into `master`
2. The merge is detected by the workflow
3. A repository owner approves the release in the `production` environment

### Manual Steps Required
1. **Create PR**: `dev` → `master`
2. **Review & Merge** the PR
3. **Approve Release**: When the workflow pauses, a repository owner must approve it
4. **Monitor**: Watch the workflow execution for any failures

### What Happens Automatically
1. ✅ Version cleaned (removes `-dev0`, `-rc1` suffixes)
2. ✅ Git tag created (`v2.12.0`)
3. ✅ GitHub release created with auto-generated notes
4. ✅ Python package built and published to PyPI (via Trusted Publishers - no tokens required)
5. ✅ Docker image built and pushed to `quay.io/galaxyproject/abm`
6. ✅ Version bumped for next development (`2.12.0` → `2.13.0-dev0`)
7. ✅ Master merged back into `dev`

### Rollback on Failure
If any step fails:
- Git tag is deleted
- GitHub release is deleted  
- Version file is restored
- Process can be retried after fixing issues

### Manual Recovery (New in 2026-05)

The workflow now supports **selective publishing** for recovery from failed releases:

#### Manual Workflow Dispatch Options
1. Go to **Actions** → **Release Process** → **Run workflow**
2. Configure publishing options:
   - `force_release`: Allow release from any branch (not just dev merges)
   - `publish_pypi`: Enable/disable PyPI publishing
   - `publish_docker`: Enable/disable Docker image publishing  
   - `create_github_release`: Enable/disable GitHub release creation
   - `merge_back_to_dev`: Enable/disable automatic merge back to dev

#### Recovery Scenarios
- **Docker build failed**: Run with `publish_docker=true`, others `false`
- **PyPI published, others failed**: Run with `publish_pypi=false`, others `true`
- **Complete retry**: Set all options to `true` with `force_release=true`

## Testing the Workflow

Before using in production:

1. **Test with a fork** or feature branch first
2. **Verify all secrets** are correctly configured
3. **Test the approval process** with the production environment
4. **Ensure branch protection rules** allow the workflow to push to `master` and `dev`

## Branch Protection Rules

Consider setting up branch protection for `master`:
- Require pull request reviews
- Restrict pushes to GitHub Actions (for version commits)
- Allow specified users/teams to bypass restrictions

## Troubleshooting

### Common Issues
- **Approval timeout**: Default timeout is 30 days, but can be configured
- **Permission errors**: Ensure GitHub Actions has write permissions to repository
- **Docker build failures**: 
  - Check platform compatibility and Dockerfile
  - Python 3.12 compatibility issues resolved (bgzip dependencies removed)
  - Build tools and compression libraries included in container
- **PyPI upload errors**: Verify trusted publisher configuration and package name availability
- **Dependency conflicts**: Use selective publishing to isolate and fix specific issues

### Logs and Monitoring
- Check **Actions** tab for detailed workflow logs
- Monitor **Releases** page for successful publications
- Verify packages appear on [PyPI](https://pypi.org/project/gxabm/) and [Quay.io](https://quay.io/repository/galaxyproject/abm)

## Security Considerations

- **Trusted Publishers**: No long-lived tokens required for PyPI publishing
- Use robot accounts for container registry access (Quay.io)  
- Monitor release activity for unauthorized publications
- Review all code changes before approving releases
- PyPI publishing is automatically authenticated via GitHub OIDC tokens