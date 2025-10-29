# Git Automation Configuration

**Status**: {enabled_or_disabled}
**Configured**: {timestamp}
**Remote**: {git_remote_url}
**Branch**: {git_branch}
**Author**: {git_author}

---

## Overview

This system has automatic git commits **{ENABLED or DISABLED}** during workflow execution.

{if_enabled}
Automatic commits will be created at key workflow milestones to:
- ✅ **Backup** architecture and code automatically
- ✅ **Track** progress through workflow steps
- ✅ **Version** control all artifacts
- ✅ **Collaborate** by pushing to remote repository
- ✅ **Recover** from failures with git history

{if_disabled}
You are managing git commits manually. The workflow will not create automatic commits.

---

## Automatic Commit Schedule

{if_enabled}
Commits occur automatically at these milestones:

### 00-setup Workflow
- ✅ **S-03-A06**: After setup complete (initial commit)
  - Commits: directory structure, foundational documents, workflow tracking files

### 01-systems-engineering Workflow
- ✅ **SE-02**: After each service architecture completed
  - Commits: `specs/machine/service_arch/{service}/service_architecture_v{version}.json`
  - Message: "Architecture: Completed {service_name} service architecture"

- ✅ **SE-06**: After system graph generated and validated
  - Commits: `specs/machine/graphs/system_of_systems_graph.json`, `architecture_issues.json`
  - Message: "Architecture: System graph and validation complete"

### 02-artifacts-visualization Workflow
- ✅ **AV-03**: After human documentation generated
  - Commits: `specs/human/service_arch/{service}/system_description*.md`
  - Message: "Documentation: Human-readable docs for all services"

- ✅ **AV-04**: After visualizations created
  - Commits: `specs/human/visualizations/*.mmd` (Mermaid diagrams)
  - Message: "Visualization: Architecture diagrams generated"

### 03-development Workflow
- ✅ **D-03**: After each service foundation code completed
  - Commits: `services/{service}/src/` (foundation code)
  - Message: "Development: {service_name} foundation code complete"

- ✅ **D-03**: After each service implementation and tests pass
  - Commits: `services/{service}/` (full implementation + tests)
  - Message: "Development: {service_name} implementation complete with passing tests"

### 04-testing-operations Workflow
- ✅ **TO-02**: After CI/CD pipeline configured
  - Commits: `.github/workflows/`, `docker-compose.yml`, `Dockerfile`
  - Message: "Operations: CI/CD pipeline configured"

- ✅ **TO-04**: After successful deployment
  - Commits: deployment configurations
  - Message: "Operations: Deployment configuration complete"

---

## Commit Message Format

All automatic commits follow this pattern:

```
{Category}: {Brief description}

{Detailed description with bullet points}
- Item 1
- Item 2
- Item 3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: {git_author}
```

**Categories**: Architecture, Documentation, Visualization, Development, Operations, Testing

---

## Git Commands Used

### Standard Commit Pattern
```bash
cd {system_root}
git add {files_or_directories}
git commit -m "$(cat <<'EOF'
{commit_message}
EOF
)"
git push origin {git_branch}
```

### Error Handling
- If `git push` fails: Warning shown but workflow continues
- Common issues: Authentication required, branch protection, network errors
- Solution: Configure git credentials or SSH keys externally

---

## How to Disable Git Automation

If you want to disable automatic commits:

1. **During workflow execution**:
   - Edit `{system_root}/context/working_memory.json`
   - Set `"git_automation_enabled": false`
   - Save and reload working memory

2. **Permanently**:
   - Delete or rename `{system_root}/context/git_config.json`
   - Set `git_automation_enabled: false` in working_memory.json

3. **Temporarily skip one commit**:
   - Not currently supported - all milestones auto-commit when enabled
   - Disable then re-enable if needed

---

## How to Re-Enable Git Automation

If git automation was disabled and you want to enable it:

1. Run setup workflow again with git configuration
2. Or manually create/update `context/git_config.json`:
   ```json
   {
     "git_automation_enabled": true,
     "git_remote_url": "https://github.com/username/repo.git",
     "git_branch": "main",
     "git_author": "Claude Code <noreply@anthropic.com>"
   }
   ```
3. Update `context/working_memory.json` to include git configuration fields

---

## Git Credential Setup

### For HTTPS URLs
```bash
# Store credentials (prompted once, then cached)
git config --global credential.helper store

# Or use credential manager
git config --global credential.helper manager
```

### For SSH URLs
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Add public key to GitHub/GitLab
cat ~/.ssh/id_ed25519.pub
# Copy and paste into GitHub Settings > SSH Keys
```

---

## Checking Git Status

To see git automation status:

```bash
# Check if enabled
cat {system_root}/context/working_memory.json | grep git_automation

# See last commit
git log -1 --oneline

# See all workflow commits
git log --grep="🤖 Generated with" --oneline

# View commit history
git log --graph --oneline --all
```

---

## Manual Git Commands (If Automation Disabled)

If you disabled automation, here are useful manual commands:

```bash
# See what's changed
git status
git diff

# Commit architecture changes
git add specs/
git commit -m "Architecture: Updated service architectures"

# Commit code changes
git add services/
git commit -m "Development: Implemented character_service"

# Push to remote
git push origin {git_branch}

# Create a tag at milestone
git tag -a v1.0.0-architecture -m "Architecture phase complete"
git push origin v1.0.0-architecture
```

---

## Troubleshooting

### Push Fails with Authentication Error
**Problem**: `git push` fails with 403 or authentication error

**Solution**:
- HTTPS: Run `git config --global credential.helper store` and try again
- SSH: Set up SSH keys and add to GitHub/GitLab

### Push Fails with Branch Protection
**Problem**: `git push` fails because branch is protected

**Solution**:
- Push to different branch: Update git_branch in git_config.json
- Or disable branch protection temporarily
- Or create pull request workflow instead of direct push

### Commits Include Unwanted Files
**Problem**: `.gitignore` not excluding certain files

**Solution**:
- Edit `.gitignore` to add patterns
- Run `git rm --cached {file}` to un-track files
- Commit the updated .gitignore

### Merge Conflicts
**Problem**: Auto-push fails due to conflicts with remote

**Solution**:
- Pull changes first: `git pull origin {branch}`
- Resolve conflicts manually
- Continue workflow - next auto-commit will push

---

## Configuration Files

**Location**: `{system_root}/context/git_config.json`

**Fields**:
- `git_automation_enabled`: true/false
- `git_remote_url`: Remote repository URL
- `git_branch`: Branch to push to (usually "main")
- `git_author`: Commit author attribution

**Also stored in**: `context/working_memory.json` (duplicated for convenience)

---

## Benefits of Git Automation

✅ **Never lose work**: All progress backed up to remote
✅ **Clear history**: See exactly when each milestone completed
✅ **Collaboration**: Team members can track progress
✅ **Recovery**: Roll back to any workflow stage
✅ **Audit trail**: Complete record of system evolution
✅ **Meaningful commits**: Descriptive messages at logical points
✅ **Hands-free**: No need to remember to commit

---

## When NOT to Use Git Automation

❌ **Experimental/throwaway work**: Quick prototypes you'll delete
❌ **Sensitive projects**: If you can't push to remote repositories
❌ **Learning**: When you want to learn git commands manually
❌ **Complex git workflows**: If you need manual control (rebasing, squashing, etc.)
❌ **Branch strategies**: If you have specific branching requirements

---

**For more information**: See `/home/ajs7/project/reflow/docs/GIT_AUTOMATION_GUIDE.md`

**Last Updated**: {timestamp}
