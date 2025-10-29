#!/bin/bash
# Script to create GitHub issues for Reflow v3.4.0
# Generated from docs/v3.4.0_GITHUB_ISSUES.md
#
# Usage: bash tools/create_github_issues.sh
#
# Prerequisites:
# - GitHub CLI installed: https://cli.github.com/
# - Authenticated: gh auth login
# - Repository: sligara7/reflow

set -e

REPO="sligara7/reflow"
MILESTONE="v3.4.0"

echo "Creating GitHub issues for Reflow v3.4.0..."
echo "Repository: $REPO"
echo "Milestone: $MILESTONE"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) is not installed."
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "ERROR: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

echo "Creating labels if they don't exist..."
gh label create "high-priority" -c "d73a4a" -d "High priority issue" -R "$REPO" 2>/dev/null || true
gh label create "medium-priority" -c "fbca04" -d "Medium priority issue" -R "$REPO" 2>/dev/null || true
gh label create "low-priority" -c "0e8a16" -d "Low priority issue" -R "$REPO" 2>/dev/null || true
gh label create "security" -c "d73a4a" -d "Security vulnerability" -R "$REPO" 2>/dev/null || true
gh label create "testing" -c "0052cc" -d "Testing related" -R "$REPO" 2>/dev/null || true
gh label create "quality" -c "5319e7" -d "Code quality" -R "$REPO" 2>/dev/null || true
gh label create "ci-cd" -c "d4c5f9" -d "CI/CD pipeline" -R "$REPO" 2>/dev/null || true
gh label create "schema" -c "006b75" -d "JSON schema" -R "$REPO" 2>/dev/null || true
gh label create "meta-analysis" -c "bfdadc" -d "Meta-analysis related" -R "$REPO" 2>/dev/null || true

echo "Labels created/verified."
echo ""

# =============================================================================
# HIGH PRIORITY ISSUES (8)
# =============================================================================

echo "Creating HIGH priority issues..."

# Issue #1: SV-01 - Path Traversal (COMPLETED)
gh issue create -R "$REPO" \
  --title "Fix Path Traversal Vulnerabilities in Tools (SV-01)" \
  --label "security,high-priority,bug" \
  --milestone "$MILESTONE" \
  --body "**Status**: ✅ COMPLETED

**Description**:
Fix path traversal security vulnerabilities in approximately 12 Reflow tools that accept user-provided file paths without validation.

**Vulnerability**:
Tools currently accept paths like \`../../../../etc/passwd\` without validation, allowing potential access to files outside system_root.

**Affected Tools** (14 files):
1. \`tools/system_of_systems_graph_v2.py\`
2. \`tools/validate_architecture.py\`
3. \`tools/validate_workflow_files.py\`
4. \`tools/validate_foundational_alignment.py\`
5. \`tools/generate_interface_contracts.py\`
6. \`tools/context_refresh.py\`
7. \`tools/detect_context_drift.py\`
8. \`tools/bootstrap_development_context.py\`
9. \`tools/verify_component_contract.py\`
10. \`tools/analyze_features.py\`
11-14. \`tools/generate_mermaid_*.py\` (4 files)

**Fix Implemented**:
Created \`tools/path_utils.py\` with \`sanitize_path()\` function and updated all tools.

**Acceptance Criteria**:
- [x] Create \`tools/path_utils.py\` with \`sanitize_path()\` function
- [x] Update all 14 tools to use \`sanitize_path()\`
- [x] Add unit tests for path traversal attacks
- [x] Verify tools reject paths outside system_root
- [x] Update TOOL_USAGE_SUMMARY.md with security notes

**Completion**: Multiple commits in October 2025
**Reference**: Commits 756791c, 9f6a8cb, 14c7093, and others"

echo "  ✓ Issue #1 created (SV-01)"

# Issue #2: SV-02 - JSON Validation (COMPLETED)
gh issue create -R "$REPO" \
  --title "Add JSON Schema Validation to All Tools (SV-02)" \
  --label "security,high-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ✅ COMPLETED

**Description**:
Add JSON schema validation to all tools that load JSON files. Currently tools use \`json.load()\` without validation, making them vulnerable to malformed JSON and injection attacks.

**Implementation**:
Created \`safe_load_json()\` utility with comprehensive error handling and schema validation.

**Affected Tools**: All 16 tools that load JSON files

**Dependencies**:
- Issue #8 (SCHEMAS-01: Create workflow_schema.json) - COMPLETED

**Acceptance Criteria**:
- [x] Add \`jsonschema\` to \`requirements.txt\`
- [x] Create \`tools/json_utils.py\` with \`safe_load_json()\`
- [x] Update all tools to use \`safe_load_json()\`
- [x] Add helpful error messages for validation failures
- [x] Add unit tests for malformed JSON
- [x] Document schema validation in TOOL_USAGE_SUMMARY.md

**Completion**: October 2025
**Reference**: Commits c3bec34, d76d592, a2bf267, 86ec69a, 2b68a6f, 7bb8b60"

echo "  ✓ Issue #2 created (SV-02)"

# Issue #3: TESTING-01 - Test Suite (IN PROGRESS)
gh issue create -R "$REPO" \
  --title "Create Comprehensive Test Suite (TESTING-01)" \
  --label "testing,high-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: 🔄 IN PROGRESS (80% complete for flagship tool)

**Description**:
Create comprehensive test suite for Reflow tools. Current coverage is ~6%, target is 60% minimum with 80% for critical tools.

**Current Progress** (as of October 26, 2025):
- ✅ \`system_of_systems_graph_v2.py\`: **113 tests, 80% coverage** (TARGET MET!)
- ⏳ Other 15 tools: Tests needed

**Target Coverage**:
| Tool | Estimated Tests | Coverage Target | Status |
|------|-----------------|-----------------|--------|
| system_of_systems_graph_v2.py | 113 | 80% | ✅ COMPLETE |
| validate_architecture.py | 50 | 80% | ⏳ Pending |
| validate_workflow_files.py | 30 | 80% | ⏳ Pending |
| validate_foundational_alignment.py | 20 | 70% | ⏳ Pending |
| generate_interface_contracts.py | 25 | 70% | ⏳ Pending |
| Other 11 tools | 75 | 50% | ⏳ Pending |
| **Total** | **300+** | **65% avg** | **🔄 38% complete** |

**Test Types**:
- **Unit tests** (200+): Individual function testing
- **Integration tests** (50): Tool interactions, workflow execution
- **Security tests** (20): Path traversal, JSON injection
- **Regression tests** (30): Verify v3.3.1 compatibility

**Acceptance Criteria**:
- [x] Create test infrastructure (pytest, pytest-cov, CI/CD pipeline)
- [x] Achieve 80% coverage for flagship tool (system_of_systems_graph_v2.py)
- [ ] Create unit tests for all 16 tools (minimum 200 tests)
- [ ] Create integration tests for workflow execution (50 tests)
- [ ] Create security tests for vulnerabilities (20 tests)
- [ ] Achieve 60% overall coverage minimum
- [ ] Achieve 80% coverage for critical tools (top 5)
- [ ] All tests passing in CI/CD
- [ ] Coverage report generated and committed

**Effort**: 10-15 days (estimated 5 days remaining)
**Risk**: MEDIUM - Tests may be flaky initially
**Mitigation**: Thorough review, stable fixtures, retry logic for flaky tests

**Next Steps**:
1. Move to \`validate_architecture.py\` (50 tests, 80% coverage target)
2. Then \`validate_workflow_files.py\` (30 tests)
3. Continue through critical tools
4. Add integration and security tests

**Reference**: Commits 3256574, ac71f80, b82fd83, 57748ab, 4f68a36"

echo "  ✓ Issue #3 created (TESTING-01) - IN PROGRESS"

# Issue #4: TESTING-02 - CI/CD Blocking
gh issue create -R "$REPO" \
  --title "Enable CI/CD Pipeline Blocking (TESTING-02)" \
  --label "ci-cd,high-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING (Blocked by Issue #3)

**Description**:
Remove \`continue-on-error: true\` from CI/CD pipeline to make tests a blocking quality gate.

**Current State**:
\`\`\`yaml
jobs:
  test:
    continue-on-error: true  # Tests can fail without blocking
\`\`\`

**Proposed State**:
\`\`\`yaml
jobs:
  test:
    # Tests MUST pass - no continue-on-error
\`\`\`

**Dependencies**:
- **Issue #3 (TESTING-01) MUST complete first** - Need stable test suite
- Test suite must have < 5% flaky test rate

**Acceptance Criteria**:
- [ ] Remove \`continue-on-error\` from all CI/CD jobs in \`.github/workflows/ci.yml\`
- [ ] Verify test suite is stable (< 5% flaky rate)
- [ ] Document CI/CD requirements in CONTRIBUTING.md
- [ ] Add CI/CD status badge to README.md
- [ ] Ensure all jobs pass consistently

**Effort**: 1 day (configuration change + validation)
**Risk**: HIGH - May block builds if tests unstable
**Mitigation**: Only proceed after TESTING-01 complete and verified

**Prerequisite**: Issue #3 must show 200+ tests with 60%+ coverage and < 5% flake rate"

echo "  ✓ Issue #4 created (TESTING-02)"

# Issue #5: CODE-QUAL-01 - Linting
gh issue create -R "$REPO" \
  --title "Add Linting and Type Checking (CODE-QUAL-01)" \
  --label "quality,high-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

**Description**:
Add ruff (linting), mypy (type checking), and pre-commit hooks to enforce code quality standards.

**New Files to Create**:
1. \`.pre-commit-config.yaml\` - Pre-commit hook configuration
2. \`pyproject.toml\` - Ruff and mypy configuration
3. \`.ruff.toml\` - Ruff-specific settings (optional)

**Dependencies to Add**:
\`\`\`txt
# requirements.txt additions
ruff>=0.1.0
mypy>=1.0.0
pre-commit>=3.0.0
\`\`\`

**Pre-commit Hooks**:
\`\`\`yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
  - repo: local
    hooks:
      - id: validate-workflows
        name: Validate workflow JSON files
        entry: python3 tools/validate_workflow_files.py workflows/
        language: system
        pass_filenames: false
\`\`\`

**Acceptance Criteria**:
- [ ] Create \`.pre-commit-config.yaml\` with ruff, mypy, workflow validation
- [ ] Create \`pyproject.toml\` with tool configurations
- [ ] Add dependencies to \`requirements.txt\`
- [ ] Run \`pre-commit install\` in documentation
- [ ] Add pre-commit usage to CONTRIBUTING.md
- [ ] Configure ruff to use Python 3.8+ compatibility
- [ ] Configure mypy for gradual typing

**Effort**: 2 days
**Risk**: LOW - Tools are opt-in via \`pre-commit install\`"

echo "  ✓ Issue #5 created (CODE-QUAL-01)"

# Issue #6: CODE-QUAL-02 - Fix Linting
gh issue create -R "$REPO" \
  --title "Fix Linting Issues from Ruff/Mypy (CODE-QUAL-02)" \
  --label "quality,high-priority,refactoring" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING (Blocked by Issue #5)

**Description**:
Fix all linting and type checking issues identified by ruff and mypy across 16 tools (~6,700 LOC).

**Dependencies**:
- **Issue #5 (CODE-QUAL-01) must complete first** - Need ruff/mypy installed

**Approach**:
1. Run \`ruff check tools/ --fix\` to auto-fix simple issues
2. Run \`ruff check tools/\` to identify remaining issues
3. Run \`mypy tools/\` to identify type errors
4. Manually fix complex issues
5. Re-run tests to ensure fixes don't break functionality

**Expected Issue Categories**:
- Unused imports
- Line length violations (PEP 8 - 88 char max with ruff)
- Missing type hints
- Inconsistent naming (snake_case vs camelCase)
- Docstring formatting (Google style recommended)

**Acceptance Criteria**:
- [ ] Run \`ruff check tools/ --fix\` and commit auto-fixes
- [ ] Fix all remaining ruff errors manually
- [ ] Add type hints to functions missing them
- [ ] Fix all mypy type errors
- [ ] Verify all tests still pass after fixes
- [ ] Document code style in CONTRIBUTING.md
- [ ] Ruff and mypy pass in CI/CD

**Effort**: 3 days
**Risk**: MEDIUM - Unknown number of issues until ruff runs
**Mitigation**: Auto-fix first, manual review of all changes"

echo "  ✓ Issue #6 created (CODE-QUAL-02)"

# Issue #7: DEV-OBS-02 - Tool Quality Analyzer
gh issue create -R "$REPO" \
  --title "Create analyze_tool_quality.py (DEV-OBS-02)" \
  --label "enhancement,high-priority,tooling" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

**Description**:
Create automated tool quality analysis script to support D-02 step in development workflow.

**Purpose**:
Automate code quality analysis that was manually performed during meta-analysis (see \`docs/TOOL_CODE_QUALITY_REPORT.md\`).

**Features**:
- Lines of code (LOC) count per tool
- Cyclomatic complexity analysis
- Maintainability index calculation
- Security vulnerability scan (using bandit)
- Test coverage analysis (from pytest-cov)
- Documentation coverage (docstring presence)
- Code duplication detection

**Output**:
JSON report with structure:
\`\`\`json
{
  \"timestamp\": \"2025-10-25T...\",
  \"tools_analyzed\": 16,
  \"summary\": {
    \"total_loc\": 6700,
    \"average_complexity\": 8.5,
    \"security_issues\": 0,
    \"test_coverage\": 65,
    \"doc_coverage\": 85
  },
  \"tools\": [
    {
      \"name\": \"system_of_systems_graph_v2.py\",
      \"loc\": 850,
      \"complexity\": 12,
      \"maintainability_index\": 72,
      \"security_issues\": [],
      \"test_coverage\": 80,
      \"doc_coverage\": 90
    }
  ]
}
\`\`\`

**Usage**:
\`\`\`bash
python3 tools/analyze_tool_quality.py <system_root>/tools --output quality_report.json
python3 tools/analyze_tool_quality.py tools/ --format markdown > TOOL_QUALITY_REPORT.md
\`\`\`

**Acceptance Criteria**:
- [ ] Create \`tools/analyze_tool_quality.py\`
- [ ] Support JSON and Markdown output formats
- [ ] Calculate LOC, complexity, maintainability for each tool
- [ ] Integrate with bandit for security scanning
- [ ] Integrate with pytest-cov for coverage data
- [ ] Add CLI arguments (--output, --format, --threshold)
- [ ] Add unit tests for the analyzer itself
- [ ] Document usage in TOOL_USAGE_SUMMARY.md

**Dependencies**:
\`\`\`txt
radon>=5.1.0  # Complexity and maintainability
bandit>=1.7.0  # Security scanning
\`\`\`

**Effort**: 2 days
**Risk**: LOW - Standalone tool, doesn't modify existing code"

echo "  ✓ Issue #7 created (DEV-OBS-02)"

# Issue #8: SCHEMAS-01 - Workflow Schema (COMPLETED)
gh issue create -R "$REPO" \
  --title "Create workflow_schema.json (SCHEMAS-01)" \
  --label "schema,high-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ✅ COMPLETED

**Description**:
Create JSON schema for validating workflow JSON files structure.

**Purpose**:
Enable \`validate_workflow_files.py\` and other tools to validate workflow structure programmatically, preventing malformed workflow files.

**Schema Location**: \`schemas/workflow_schema.json\`

**Implementation**:
Created comprehensive JSON schema enforcing workflow structure with required fields, validation gates, and metadata.

**Acceptance Criteria**:
- [x] Create \`schemas/workflow_schema.json\` with complete schema
- [x] Validate all 6 existing workflow files against schema
- [x] Update \`validate_workflow_files.py\` to use schema
- [x] Add schema validation examples to documentation
- [x] Add unit tests for schema validation
- [x] Document schema in \`docs/SCHEMA_DOCUMENTATION.md\`

**Completion**: October 2025
**Reference**: Commit 7d4e29f and related"

echo "  ✓ Issue #8 created (SCHEMAS-01)"

echo ""
echo "HIGH priority issues created (8 issues)"
echo ""

# =============================================================================
# MEDIUM PRIORITY ISSUES (11)
# =============================================================================

echo "Creating MEDIUM priority issues..."

# Issue #9: DEV-OBS-03 - Additional Schemas
gh issue create -R "$REPO" \
  --title "Create Additional JSON Schemas (DEV-OBS-03)" \
  --label "schema,medium-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

**Description**:
Create 7 additional JSON schemas for validating Reflow architecture and template files.

**Schemas to Create** (in priority order):
1. \`schemas/template_schema.json\` - Base schema for all templates
2. \`schemas/interface_registry_schema.json\` - Validates interface_registry.json
3. \`schemas/port_registry_schema.json\` - Validates port_registry.json
4. \`schemas/security_architecture_schema.json\` - Validates security_architecture.json
5. \`schemas/deployment_architecture_schema.json\` - Validates deployment_architecture.json
6. \`schemas/ux_api_design_schema.json\` - Validates ux_api_design.json
7. \`schemas/operational_environment_schema.json\` - Validates operational_environment.json

**Dependencies**:
- Issue #8 (workflow_schema.json) - ✅ COMPLETED (can be used as reference)

**Acceptance Criteria** (per schema):
- [ ] Create schema file with complete structure
- [ ] Validate against existing files (if any)
- [ ] Add validation to relevant tools
- [ ] Document schema in \`docs/SCHEMA_DOCUMENTATION.md\`
- [ ] Add unit tests for schema validation

**Effort**: 4 days (0.5 days per schema)
**Risk**: LOW - Validates existing structures"

echo "  ✓ Issue #9 created (DEV-OBS-03)"

# Issue #10: FU-OBS-01 - Path Flexibility
gh issue create -R "$REPO" \
  --title "Fix validate_foundational_alignment.py Path Flexibility (FU-OBS-01)" \
  --label "enhancement,medium-priority,bug" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

**Description**:
Fix rigid path expectations in \`validate_foundational_alignment.py\` to check multiple locations for foundational documents.

**Current Behavior**:
Expects \`SYSTEM_MISSION_STATEMENT.md\` in system root only.

**Proposed Behavior**:
Check multiple locations:
\`\`\`python
def find_foundational_doc(system_path, doc_name):
    \"\"\"Find foundational document in multiple locations.\"\"\"
    search_paths = [
        system_path / doc_name,
        system_path / \"docs\" / doc_name,
        system_path / \"documentation\" / doc_name
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None
\`\`\`

**Acceptance Criteria**:
- [ ] Update \`validate_foundational_alignment.py\` to search multiple paths
- [ ] Add meta-analysis scenario detection (relax some requirements for frameworks)
- [ ] Update error messages to suggest multiple locations
- [ ] Add unit tests for path search logic
- [ ] Update TOOL_USAGE_SUMMARY.md

**Effort**: 0.5 days
**Risk**: LOW - Backward compatible (existing paths still work)"

echo "  ✓ Issue #10 created (FU-OBS-01)"

# Issue #11: SE-OBS-03 - Terminology
gh issue create -R "$REPO" \
  --title "Standardize Terminology Across Workflows (SE-OBS-03)" \
  --label "documentation,medium-priority,enhancement" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

**Description**:
Standardize terminology across all 6 workflow files to improve consistency and clarity.

**Inconsistencies Identified**:
- \"component\" vs \"service\" (prefer \"service\" for UAF, \"component\" for other frameworks)
- \"artifact\" vs \"output\" (prefer \"output\")
- \"quality gate\" vs \"gate\" vs \"validation gate\" (prefer \"quality gate\")
- \"LLM agent\" vs \"agent\" vs \"AI assistant\" (prefer \"LLM agent\")

**Files to Update**:
- \`workflows/00-setup.json\`
- \`workflows/01-systems_engineering.json\`
- \`workflows/02-artifacts_visualization.json\`
- \`workflows/03-development.json\`
- \`workflows/04-testing_operations.json\`
- \`workflows/feature_update.json\`

**Approach**:
1. Create terminology standards document
2. Run scripted find/replace for common terms
3. Manual review of context-specific usage
4. Validate all workflows after changes

**Acceptance Criteria**:
- [ ] Create \`docs/TERMINOLOGY_STANDARDS.md\`
- [ ] Update all 6 workflow files with consistent terms
- [ ] Validate workflows after changes
- [ ] Update CLAUDE.md to reference standards
- [ ] No functional changes (terminology only)

**Effort**: 2 days
**Risk**: MEDIUM - Risk of incomplete standardization"

echo "  ✓ Issue #11 created (SE-OBS-03)"

# Issues #12-21: Create remaining medium priority issues (abbreviated)
echo "  Creating abbreviated medium priority issues #12-19..."

gh issue create -R "$REPO" \
  --title "Add Meta-Analysis Branch to Feature Update Workflow (FU-OBS-02)" \
  --label "enhancement,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Add explicit support for meta-analysis scenarios in \`feature_update.json\` workflow where Reflow analyzes itself.

**Effort**: 1 day
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #12 created (FU-OBS-02)"

gh issue create -R "$REPO" \
  --title "Create Workflow Improvement Observation Template (FU-OBS-03)" \
  --label "documentation,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Create template for documenting workflow improvement observations discovered during execution.

**Effort**: 0.5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #13 created (FU-OBS-03)"

gh issue create -R "$REPO" \
  --title "Add Schema Management Step to SE-02 (DEV-OBS-07)" \
  --label "enhancement,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Add step to systems engineering workflow for creating JSON schemas alongside architecture files.

**Effort**: 1 day
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #14 created (DEV-OBS-07)"

gh issue create -R "$REPO" \
  --title "Add File-Based System Guidance to D-03 (DEV-OBS-08)" \
  --label "documentation,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Add guidance for file-based systems (SQLite, JSON) vs traditional databases in development workflow.

**Effort**: 0.5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #15 created (DEV-OBS-08)"

gh issue create -R "$REPO" \
  --title "Create Testing Templates and Examples (DEV-OBS-10)" \
  --label "testing,medium-priority,documentation" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Create templates and examples for unit tests, integration tests, and security tests.

**Effort**: 2 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #16 created (DEV-OBS-10)"

gh issue create -R "$REPO" \
  --title "Add File Overwrite Confirmations (SV-03)" \
  --label "security,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Add confirmation prompts before overwriting existing files in all tools.

**Effort**: 1 day
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #17 created (SV-03)"

gh issue create -R "$REPO" \
  --title "Add Input Sanitization Across Tools (SV-04)" \
  --label "security,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Add input sanitization for user-provided strings to prevent injection attacks.

**Effort**: 2 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #18 created (SV-04)"

gh issue create -R "$REPO" \
  --title "Create CONTRIBUTING.md with Code Quality Guidelines" \
  --label "documentation,medium-priority" \
  --milestone "$MILESTONE" \
  --body "**Status**: ⏳ PENDING

Create comprehensive CONTRIBUTING.md documenting code quality standards, testing requirements, and development workflow.

**Effort**: 1 day
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #19 created (CONTRIBUTING.md)"

echo ""
echo "MEDIUM priority issues created (11 issues)"
echo ""

# =============================================================================
# LOW PRIORITY ISSUES (7)
# =============================================================================

echo "Creating LOW priority issues (deferred to v3.5.0)..."

gh issue create -R "$REPO" \
  --title "Create change_proposal_template.md (FU-OBS-04)" \
  --label "documentation,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Extract structure from \`CHANGE_PROPOSAL_20251025_v3.4.0.md\` to create reusable template for future feature updates.

**Effort**: 0.5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #20 created (FU-OBS-04)"

gh issue create -R "$REPO" \
  --title "Create delta_report_template.md (FU-OBS-05)" \
  --label "documentation,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Extract structure from \`DELTA_REPORT_v3.4.0_20251025.md\` to create reusable template.

**Effort**: 0.5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #21 created (FU-OBS-05)"

gh issue create -R "$REPO" \
  --title "Add Meta-Analysis Success Criteria to Development Workflow (DEV-OBS-12)" \
  --label "documentation,low-priority,meta-analysis" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Add explicit success criteria for meta-analysis scenarios in development workflow.

**Effort**: 0.5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #22 created (DEV-OBS-12)"

gh issue create -R "$REPO" \
  --title "Create Migration Scripts Tool (DEV-OBS-13)" \
  --label "enhancement,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v4.0.0

Create tool for generating database migration scripts during development.

**Effort**: 3 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #23 created (DEV-OBS-13)"

gh issue create -R "$REPO" \
  --title "Create Remaining 18-20 JSON Schemas (SCHEMAS-02)" \
  --label "schema,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Create remaining JSON schemas for all 36+ template files.

**Effort**: 10 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #24 created (SCHEMAS-02)"

# Add 2 more low priority placeholders
gh issue create -R "$REPO" \
  --title "Add Workflow Execution Metrics (DEV-OBS-14)" \
  --label "enhancement,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Add timing and metrics tracking to workflow execution.

**Effort**: 2 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #25 created (DEV-OBS-14)"

gh issue create -R "$REPO" \
  --title "Create Automated Workflow Testing Harness (TESTING-03)" \
  --label "testing,low-priority" \
  --body "**Status**: ⏳ DEFERRED to v3.5.0

Create automated testing harness for end-to-end workflow execution validation.

**Effort**: 5 days
**Reference**: \`docs/v3.4.0_GITHUB_ISSUES.md\`" \
  > /dev/null

echo "  ✓ Issue #26 created (TESTING-03)"

echo ""
echo "LOW priority issues created (7 issues)"
echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "=========================================="
echo "GitHub Issues Creation Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  HIGH priority:   8 issues (3 completed, 1 in progress, 4 pending)"
echo "  MEDIUM priority: 11 issues (all pending)"
echo "  LOW priority:    7 issues (all deferred to v3.5.0)"
echo "  TOTAL:           26 issues created"
echo ""
echo "Milestone: $MILESTONE"
echo "Repository: $REPO"
echo ""
echo "Current Progress:"
echo "  ✅ Issue #1 (SV-01): Path traversal - COMPLETED"
echo "  ✅ Issue #2 (SV-02): JSON validation - COMPLETED"
echo "  🔄 Issue #3 (TESTING-01): Test suite - IN PROGRESS (80% for flagship tool)"
echo "  ✅ Issue #8 (SCHEMAS-01): Workflow schema - COMPLETED"
echo ""
echo "Next Steps:"
echo "  1. Continue Issue #3: Add tests to other tools (validate_architecture.py next)"
echo "  2. After Issue #3 complete: Enable Issue #4 (CI/CD blocking)"
echo "  3. Start Issues #5-7: Code quality, linting, tool analyzer"
echo ""
echo "To view all issues:"
echo "  gh issue list -R $REPO --milestone $MILESTONE"
echo ""
echo "To view issue details:"
echo "  gh issue view <number> -R $REPO"
echo ""
