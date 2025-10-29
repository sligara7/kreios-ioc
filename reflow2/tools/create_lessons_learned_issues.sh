#!/bin/bash
# Script to create GitHub issues from Decision Flow Framework lessons learned
# Generated from meta-analysis of framework selection (UAF → Decision Flow switch)
#
# Usage: bash tools/create_lessons_learned_issues.sh
#
# Prerequisites:
# - GitHub CLI installed: https://cli.github.com/
# - Authenticated: gh auth login
# - Repository: sligara7/reflow

set -e

REPO="sligara7/reflow"
MILESTONE="v3.5.0"  # These are improvements for next release

echo "Creating GitHub issues for Decision Flow Framework lessons learned..."
echo "Repository: $REPO"
echo "Milestone: $MILESTONE (next release)"
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
gh label create "framework-selection" -c "0075ca" -d "Framework selection related" -R "$REPO" 2>/dev/null || true
gh label create "workflow-improvement" -c "1d76db" -d "Workflow improvement" -R "$REPO" 2>/dev/null || true
gh label create "user-experience" -c "d4c5f9" -d "User experience improvement" -R "$REPO" 2>/dev/null || true
gh label create "lessons-learned" -c "fbca04" -d "Lessons learned from meta-analysis" -R "$REPO" 2>/dev/null || true

echo "Labels created/verified."
echo ""

# =============================================================================
# LESSONS LEARNED FROM DECISION FLOW FRAMEWORK ANALYSIS
# =============================================================================

echo "Creating lessons learned issues..."

# Lesson #1: Framework selection is critical architectural decision (HIGH)
gh issue create -R "$REPO" \
  --title "Add Explicit Framework Selection Analysis Step (LESSON-01)" \
  --label "framework-selection,high-priority,workflow-improvement,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Reflow meta-analysis initially used UAF (default) which was wrong framework for workflow systems
**Impact**: Missed critical insights (decision logic, rework loops, path probabilities, flow analysis)

**Root Cause**:
Step S-01A (Framework Selection) exists but doesn't enforce critical analysis. LLM agents may default to UAF without deep consideration of:
1. What NetworkX analyses are enabled by framework choice
2. Whether system semantics match framework abstractions
3. What insights each framework reveals vs. misses

**Current S-01A Behavior**:
- Framework selection happens too quickly
- No explicit comparison of framework suitability
- No analysis of which NetworkX tools will be available
- User not presented with tradeoffs

**Lesson Learned**:
Framework selection is an **ARCHITECTURAL DECISION**, not a configuration choice. It determines:
- Which NetworkX analyses can be used (flow requires edge weights)
- What insights will be revealed (cycles in workflows = rework loops)
- System semantics (state machines vs. services vs. networks)

**Required Changes to S-01A**:

1. **Explicit Framework Analysis** (not just selection)
   - LLM must analyze system domain against ALL 7 frameworks
   - For each framework, list: what it reveals, what it misses
   - Consider: Are there decision points? Conditional paths? Rework loops?

2. **NetworkX Analysis Mapping**
   - Show which analyses each framework enables
   - Example: \"Flow analysis requires edge weights - only available if framework supports weighted edges\"
   - Highlight analyses that are HIGH priority for this system

3. **User Confirmation Required**
   - Present framework recommendation with rationale
   - Show comparison: recommended vs. alternatives
   - Require explicit user approval before proceeding

4. **Document Decision**
   - Record why framework was chosen in working_memory.json
   - List what analyses will be used and why
   - Note what insights framework will reveal

**Example S-01A Output** (what it should produce):
\`\`\`
System Analysis: Reflow Workflow System

Domain: Workflow/process system with decision points and conditional branching

Framework Analysis:
❌ UAF: Treats steps as services - WRONG ABSTRACTION
   Misses: Decision logic, rework loops, path probabilities
   Enables: DAG, SCC, centrality

❌ Systems Biology: For gene networks, not workflows

❌ Social Network: For relationships, not processes

✅ Decision Flow: RECOMMENDED
   Matches: State machine semantics, conditional transitions
   Reveals: Rework loops (cycles), path probabilities, critical paths
   Enables: Flow analysis, cycle detection with semantic meaning
   NetworkX: flow, cycles, paths, centrality, community

Recommendation: Use Decision Flow Framework
Rationale: Workflows are state machines with decision points, not services.
         Enables flow analysis to find bottlenecks and common paths.

[User Confirmation Required] Proceed with Decision Flow? (Y/N)
\`\`\`

**Acceptance Criteria**:
- [ ] Update workflow_steps/00-setup/S-01A.md with explicit framework analysis requirements
- [ ] Add framework comparison matrix to S-01A guidance
- [ ] Require LLM to analyze ALL frameworks, not just pick one
- [ ] Map NetworkX analyses to each framework
- [ ] Require user confirmation of framework selection
- [ ] Document decision rationale in working_memory.json
- [ ] Add framework selection quality gate (S-01A-QG)

**Affected Files**:
- \`workflow_steps/00-setup/S-01A.md\` - Add framework analysis requirements
- \`workflows/00-setup.json\` - Add framework selection quality gate
- \`definitions/framework_registry.json\` - Already has analysis mappings ✅
- \`templates/working_memory_template.json\` - Add framework_selection_rationale

**Effort**: 2 days
**Priority**: HIGH - Prevents wrong framework selection
**Risk**: LOW - Improves decision quality

**References**:
- Decision Flow Framework: \`docs/DECISION_FLOW_FRAMEWORK.md\`
- Framework Registry: \`definitions/framework_registry.json\`
- Meta-analysis findings: Commit 535654a"

echo "  ✓ Lesson #1 created (Framework Selection Analysis)"

# Lesson #2: Framework choice determines NetworkX analyses (HIGH)
gh issue create -R "$REPO" \
  --title "Document NetworkX Analysis Implications in Framework Selection (LESSON-02)" \
  --label "framework-selection,high-priority,documentation,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Framework choice determines which NetworkX analyses are available, but this isn't visible during selection

**Critical Insight**:
Different frameworks enable different analyses based on whether they support:
- **Edge weights** (required for flow analysis)
- **Directed edges** (required for DAG analysis)
- **Semantic cycles** (rework loops vs. circular dependencies)

**Example - Flow Analysis**:

| Framework | Edge Weights? | Flow Analysis? | What It Reveals |
|-----------|---------------|----------------|-----------------|
| UAF | ❌ No | ❌ Can't run | N/A |
| Decision Flow | ✅ Yes (probability) | ✅ Can run | Critical paths, bottlenecks |
| Ecological | ✅ Yes (energy flow) | ✅ Can run | Trophic efficiency |
| Systems Biology | ⚠️ Optional | ⚠️ If weights added | Metabolic flux |

**Problem**:
LLM agents don't see this during S-01A, so they might choose UAF unaware that flow analysis won't be available later.

**Solution**:
Add **Analysis Availability Matrix** to framework selection guidance.

**Required Documentation**:

1. **Framework Analysis Matrix** (add to S-01A guidance)
\`\`\`markdown
| Framework | Flow | Cycles | DAG | SCC | Centrality | Community |
|-----------|------|--------|-----|-----|------------|-----------|
| UAF | ❌ No weights | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Decision Flow | ✅ Probabilities | ✅ Semantic | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Systems Biology | ⚠️ Optional | ✅ Expected | ⚠️ If acyclic | ✅ Yes | ✅ Yes | ✅ Yes |
| Ecological | ✅ Energy flow | ✅ Nutrient | ⚠️ If hierarchical | ✅ Yes | ✅ Yes | ✅ Yes |
\`\`\`

2. **Analysis Requirement Guide**
\`\`\`
FLOW ANALYSIS requires:
  - Edge attribute: weight (capacity, probability, or flow rate)
  - Frameworks supporting this: Decision Flow, Ecological, CAS
  - Use case: Find bottlenecks, critical paths, throughput

CYCLE DETECTION works differently:
  - UAF: Cycles = BAD (circular dependencies)
  - Decision Flow: Cycles = rework loops (expected behavior)
  - Biology: Cycles = feedback loops (essential feature)
\`\`\`

3. **Decision Guidance**
\"If your system needs flow analysis → Choose framework with edge weights\"
\"If your system has expected cycles → Choose framework with semantic cycles\"

**Acceptance Criteria**:
- [ ] Add analysis availability matrix to \`docs/DECISION_FLOW_FRAMEWORK.md\`
- [ ] Update S-01A guidance with NetworkX implications
- [ ] Add \"What analyses will I need?\" decision tree
- [ ] Document edge weight semantics per framework
- [ ] Add warnings: \"UAF doesn't support flow analysis\"

**Effort**: 1 day
**Priority**: HIGH - Critical for informed framework selection

**Reference**: \`definitions/framework_registry.json\` → recommended_analyses"

echo "  ✓ Lesson #2 created (NetworkX Analysis Implications)"

# Lesson #3: Edge weights must be designed in from start (HIGH)
gh issue create -R "$REPO" \
  --title "Add Edge Weight Planning to Architecture Design (LESSON-03)" \
  --label "framework-selection,high-priority,enhancement,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Flow analysis requires edge weights, but these must be designed into architecture files from the start

**Current Problem**:
If LLM agent chooses framework with flow analysis (Decision Flow, Ecological), but doesn't add edge weights to architecture files, flow analysis will fail later.

**Example - Decision Flow**:
\`\`\`json
{
  \"transitions\": [
    {
      \"target_step\": \"SE-06\",
      \"condition\": \"validation_passed\",
      \"probability\": 0.6,  ← REQUIRED for flow analysis
      \"weight\": 6           ← REQUIRED for flow analysis
    }
  ]
}
\`\`\`

Without probability/weight → Flow analysis will fail with \"No capacity attribute\"

**Solution**:
Add edge weight planning to SE-02 (Architecture Design) workflow.

**Required Changes**:

1. **SE-02-A02: Add Edge Weight Planning**
   - After framework selection, check: Does framework use edge weights?
   - If YES, determine semantic meaning:
     - Decision Flow: probability (0.0-1.0)
     - Ecological: energy_transfer_rate (kcal/m²/year)
     - UAF (optional): request_rate (req/sec)
   - Add edge weight fields to architecture template

2. **SE-03 Validation: Check Edge Weights**
   - If framework requires edge weights, validate they exist
   - Check: All edges have weight/probability attribute
   - Validate: Weight values are in correct range (0.0-1.0 for probability)

3. **Template Updates**
   - Add edge weight examples to architecture templates
   - Show semantic meaning per framework
   - Provide default values if unknown (e.g., probability=0.5)

**Example Template Addition**:
\`\`\`json
{
  \"edge_weight_configuration\": {
    \"framework\": \"decision_flow\",
    \"weight_semantic\": \"transition_probability\",
    \"weight_field\": \"probability\",
    \"weight_range\": \"0.0-1.0\",
    \"examples\": {
      \"sequential_step\": 1.0,
      \"validation_pass\": 0.6,
      \"validation_fail\": 0.4
    }
  }
}
\`\`\`

**Acceptance Criteria**:
- [ ] Add edge weight planning to SE-02-A02 step
- [ ] Update architecture templates with weight examples
- [ ] Add SE-03 validation for required edge weights
- [ ] Document weight semantics per framework
- [ ] Add quality gate: \"Edge weights present if required\"

**Effort**: 1 day
**Priority**: HIGH - Prevents flow analysis failure

**Reference**:
- \`docs/DECISION_FLOW_FRAMEWORK.md\` → Edge Attributes
- \`definitions/framework_registry.json\` → edge_schema"

echo "  ✓ Lesson #3 created (Edge Weight Planning)"

# Lesson #4: Framework semantics must match system (MEDIUM)
gh issue create -R "$REPO" \
  --title "Add Framework Semantic Matching Guide (LESSON-04)" \
  --label "framework-selection,medium-priority,documentation,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Framework abstractions must match system semantics, not just domain

**Key Insight**:
Workflows are **state machines**, not **service architectures**, even though both could be modeled in \"engineered systems\" domain.

Wrong abstraction → Wrong insights:
- UAF: Steps as \"services\" → Misses decision logic
- Decision Flow: Steps as \"states\" → Reveals workflow dynamics

**Solution**: Add semantic matching guide to S-01A

**Semantic Matching Questions**:

1. **What are your nodes?**
   - Services that communicate? → UAF
   - States in a process? → Decision Flow
   - Agents with relationships? → Social Network
   - Species in an ecosystem? → Ecological

2. **What are your edges?**
   - Data/API calls? → UAF (interfaces)
   - State transitions? → Decision Flow (transitions)
   - Social connections? → Social Network (relationships)
   - Energy/matter flow? → Ecological (interactions)

3. **Do edges have conditions?**
   - If/else routing? → Decision Flow (conditional transitions)
   - Always connected? → UAF, Social Network

4. **Are cycles expected or errors?**
   - Expected (feedback loops)? → Biology, CAS, Decision Flow (rework)
   - Errors (circular deps)? → UAF, some DAG systems

5. **Do you need flow analysis?**
   - Yes (find bottlenecks)? → Choose framework with edge weights
   - No → Any framework works

**Acceptance Criteria**:
- [ ] Add semantic matching questionnaire to S-01A
- [ ] Create decision tree: Semantics → Framework
- [ ] Document: \"Match abstractions, not just domain\"
- [ ] Add examples: Workflows (Decision Flow) vs. Microservices (UAF)

**Effort**: 1 day
**Priority**: MEDIUM

**Reference**: \`docs/DECISION_FLOW_FRAMEWORK.md\` → Comparison with UAF"

echo "  ✓ Lesson #4 created (Semantic Matching Guide)"

# Lesson #5: User confirmation required for framework (HIGH)
gh issue create -R "$REPO" \
  --title "Require User Confirmation of Framework Selection (LESSON-05)" \
  --label "user-experience,high-priority,workflow-improvement,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Framework selection is too important to be automatic - user must confirm

**Why User Confirmation Matters**:
1. Framework choice determines entire analysis approach
2. Wrong framework wastes hours of work (had to switch UAF → Decision Flow)
3. User may have domain knowledge LLM lacks
4. Switching frameworks later requires re-doing all architecture files

**Current S-01A**: LLM selects framework, proceeds automatically (no user confirmation)

**Required S-01A-QG: Framework Selection Quality Gate**

\`\`\`markdown
Quality Gate: S-01A-QG (Framework Selection Confirmation)
Type: BLOCKING
Severity: CRITICAL

Checks:
1. Framework recommendation provided with rationale
2. Alternative frameworks considered and rejected with reasons
3. NetworkX analyses enabled by framework documented
4. Edge weight requirements explained (if applicable)
5. User explicitly confirms: \"Proceed with [framework]? (Y/N)\"

User Interaction:
┌─────────────────────────────────────────────┐
│ Framework Recommendation: Decision Flow      │
│                                              │
│ Rationale:                                   │
│ - System is a workflow with decision points │
│ - Requires flow analysis for bottlenecks   │
│ - Has expected cycles (rework loops)        │
│                                              │
│ Alternatives Considered:                     │
│ ❌ UAF - Wrong abstraction (services vs states) │
│ ❌ CAS - Overkill for deterministic workflow    │
│                                              │
│ Analyses Enabled:                            │
│ ✅ Flow (critical paths, bottlenecks)          │
│ ✅ Cycles (rework loops)                       │
│ ✅ Paths (architecture-only vs full dev)       │
│                                              │
│ Confirm: Proceed with Decision Flow? [Y/N]  │
└─────────────────────────────────────────────┘
\`\`\`

If user says NO:
- LLM asks: \"Which framework would you prefer?\"
- Re-analyzes with user's preferred framework
- Re-presents confirmation

If user says YES:
- Proceed to S-02
- Document confirmation in working_memory.json

**Acceptance Criteria**:
- [ ] Add S-01A-QG quality gate to \`workflows/00-setup.json\`
- [ ] Update S-01A to require user confirmation
- [ ] Add confirmation template with rationale
- [ ] Handle user rejection gracefully
- [ ] Document confirmation in working_memory.json
- [ ] Add to CLAUDE.md: \"User must confirm framework selection\"

**Effort**: 1 day
**Priority**: HIGH - Prevents wasted work from wrong framework

**Blocking**: If user doesn't confirm, workflow cannot proceed to SE-01"

echo "  ✓ Lesson #5 created (User Confirmation Required)"

# Lesson #6: Create framework suitability scoring system (MEDIUM)
gh issue create -R "$REPO" \
  --title "Create Framework Suitability Scoring Tool (LESSON-06)" \
  --label "enhancement,medium-priority,tooling,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: Framework selection is subjective - need objective scoring

**Solution**: Create \`tools/recommend_framework.py\`

**Features**:
1. **Input**: System description, domain, characteristics
2. **Output**: Scored framework recommendations

**Scoring Criteria**:
\`\`\`
For each framework, score 0-10 on:
- Domain match (engineered, biological, social, etc.)
- Semantic match (services, states, agents, species)
- Required analyses availability (flow, cycles, DAG)
- Edge weight requirements (can user provide?)
- Complexity (simpler frameworks preferred if equivalent)

Total score = weighted sum
\`\`\`

**Example Output**:
\`\`\`
System: Reflow Workflow System

Framework Recommendations (sorted by score):

1. Decision Flow (Score: 9.2/10) ✅ RECOMMENDED
   - Domain match: 10/10 (workflow system)
   - Semantic match: 10/10 (states, not services)
   - Analysis match: 9/10 (flow, cycles, paths all available)
   - Edge weights: 8/10 (can estimate probabilities)
   - Complexity: 8/10 (moderate)

2. Complex Adaptive Systems (Score: 6.5/10)
   - Domain match: 7/10 (emergent behavior)
   - Semantic match: 6/10 (adaptive agents)
   - Analysis match: 7/10 (cycles, SCC available)
   - Edge weights: 6/10 (interaction strength unclear)
   - Complexity: 5/10 (complex framework)

3. UAF (Score: 4.2/10) ❌ NOT RECOMMENDED
   - Domain match: 8/10 (engineered system)
   - Semantic match: 2/10 (services ≠ states)
   - Analysis match: 3/10 (DAG ok, but no flow)
   - Edge weights: 2/10 (no weight support)
   - Complexity: 8/10 (simple framework)
\`\`\`

**Usage**:
\`\`\`bash
python3 tools/recommend_framework.py --system \"workflow with decision points\" --domain \"process\"
\`\`\`

**Acceptance Criteria**:
- [ ] Create \`tools/recommend_framework.py\`
- [ ] Implement scoring algorithm
- [ ] Add CLI interface
- [ ] Integrate with S-01A step
- [ ] Add to TOOL_USAGE_SUMMARY.md

**Effort**: 3 days
**Priority**: MEDIUM - Nice to have, not critical"

echo "  ✓ Lesson #6 created (Framework Suitability Scoring)"

# Lesson #7: Update CLAUDE.md with framework selection importance (HIGH)
gh issue create -R "$REPO" \
  --title "Update CLAUDE.md to Emphasize Framework Selection Criticality (LESSON-07)" \
  --label "documentation,high-priority,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: CLAUDE.md doesn't emphasize how critical framework selection is

**Current CLAUDE.md**:
- Mentions framework selection exists
- Lists 7 frameworks
- Doesn't explain implications of choice

**Required Updates**:

1. **Add Warning Section** (top of Framework section)
\`\`\`markdown
⚠️ **CRITICAL: Framework Selection is an Architectural Decision**

DO NOT default to UAF! Framework choice determines:
- Which NetworkX analyses you can run (flow requires edge weights)
- What insights you'll discover (cycles = rework loops or circular deps?)
- System semantics (state machines vs. services vs. networks)

**Wrong framework = Wrong insights** (example: UAF on workflows misses decision logic)

**ALWAYS**:
1. Analyze system semantics (states? services? agents? species?)
2. Consider required analyses (need flow analysis? choose framework with edge weights)
3. Compare all 7 frameworks against system characteristics
4. Get user confirmation before proceeding

**Time investment**: 10-15 min framework analysis saves hours of rework later
\`\`\`

2. **Add Framework Decision Tree**
\`\`\`markdown
## Framework Selection Decision Tree

Is your system a workflow/process with decision points?
  → YES: Decision Flow Framework
  → NO: Continue...

Is your system engineered software/hardware?
  → YES: UAF (if services) or Custom (if hybrid)
  → NO: Continue...

[... rest of decision tree ...]
\`\`\`

3. **Add Examples Section**
\`\`\`markdown
## Framework Selection Examples

✅ CORRECT:
- Microservices system → UAF (services communicating via APIs)
- Reflow workflows → Decision Flow (states with conditional transitions)
- Gene regulatory network → Systems Biology (molecular interactions)

❌ INCORRECT:
- Reflow workflows → UAF (wrong: steps ≠ services, misses decision logic)
- Social network → UAF (wrong: relationships ≠ interfaces)
\`\`\`

**Acceptance Criteria**:
- [ ] Add WARNING section to CLAUDE.md framework section
- [ ] Add framework decision tree
- [ ] Add correct/incorrect examples
- [ ] Emphasize: \"Get user confirmation\"
- [ ] Document: \"10-15 min analysis saves hours later\"
- [ ] Link to: \`docs/DECISION_FLOW_FRAMEWORK.md\`

**Effort**: 0.5 days
**Priority**: HIGH - Prevents future wrong framework selections

**Files to Update**:
- \`CLAUDE.md\` (Framework section)
- \`README.md\` (Quick start - mention framework importance)"

echo "  ✓ Lesson #7 created (CLAUDE.md Updates)"

# Lesson #8: Allow post-hoc framework switching (LOW)
gh issue create -R "$REPO" \
  --title "Add Framework Switching Capability (LESSON-08)" \
  --label "enhancement,low-priority,lessons-learned" \
  --milestone "$MILESTONE" \
  --body "**Lesson Learned From**: Decision Flow Framework analysis (Oct 2025)
**Problem**: If wrong framework chosen, must manually re-do all architecture files

**What Happened**:
- Initially chose UAF for Reflow
- Discovered it was wrong framework
- Had to manually switch to Decision Flow
- All architecture files had to be recreated

**Solution**: Create framework migration tool

**Tool**: \`tools/migrate_framework.py\`

**Usage**:
\`\`\`bash
python3 tools/migrate_framework.py \\
  --from uaf \\
  --to decision_flow \\
  --system-root /path/to/system \\
  --output-dir specs/machine/migrated/
\`\`\`

**Features**:
1. Read existing architecture files (old framework)
2. Map fields: old framework → new framework
3. Generate architecture files in new framework
4. Update working_memory.json
5. Preserve data where possible, flag manual review needed

**Field Mapping Example**:
\`\`\`
UAF → Decision Flow:
  service_id → step_id
  service_name → step_name
  interfaces → transitions
  dependencies → prerequisites

Add fields:
  node_type (default: process_step, manual review)
  transitions.probability (default: 1.0, manual review)
  transitions.condition (default: \"always\", manual review)
\`\`\`

**Limitations**:
- Can't auto-generate edge weights (requires domain knowledge)
- Can't determine node types (decision_node vs. process_step)
- User must review and refine migrated files

**Output**:
\`\`\`
Migration Report:
- Migrated: 8 architecture files
- Auto-mapped: 45 fields
- Manual review needed: 12 decisions
  * node_type for 8 steps (decision_node vs. process_step?)
  * transition probabilities for 4 conditional edges

Next steps:
1. Review migrated files in specs/machine/migrated/
2. Add edge probabilities where needed
3. Set correct node types
4. Run validate_architecture.py
\`\`\`

**Acceptance Criteria**:
- [ ] Create \`tools/migrate_framework.py\`
- [ ] Support UAF ↔ Decision Flow migration
- [ ] Add field mapping logic
- [ ] Generate migration report
- [ ] Flag manual review items
- [ ] Add validation after migration

**Effort**: 5 days
**Priority**: LOW - Nice to have, not essential
**Deferred**: v4.0.0 (not critical for v3.5.0)"

echo "  ✓ Lesson #8 created (Framework Switching Tool)"

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "=========================================="
echo "Lessons Learned Issues Created!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  Lessons created: 8 issues"
echo "  HIGH priority:   5 issues (#1, #2, #3, #5, #7)"
echo "  MEDIUM priority: 2 issues (#4, #6)"
echo "  LOW priority:    1 issue (#8)"
echo ""
echo "Milestone: $MILESTONE (v3.5.0)"
echo "Repository: $REPO"
echo ""
echo "Issues Created:"
echo "  LESSON-01: Add Explicit Framework Selection Analysis Step"
echo "  LESSON-02: Document NetworkX Analysis Implications"
echo "  LESSON-03: Add Edge Weight Planning to Architecture Design"
echo "  LESSON-04: Add Framework Semantic Matching Guide"
echo "  LESSON-05: Require User Confirmation of Framework Selection"
echo "  LESSON-06: Create Framework Suitability Scoring Tool"
echo "  LESSON-07: Update CLAUDE.md to Emphasize Framework Criticality"
echo "  LESSON-08: Add Framework Switching Capability (deferred v4.0)"
echo ""
echo "Key Lesson: Framework selection is ARCHITECTURAL DECISION, not config choice"
echo ""
echo "Next Steps:"
echo "  1. Implement LESSON-01 (S-01A framework analysis step)"
echo "  2. Implement LESSON-05 (user confirmation required)"
echo "  3. Update LESSON-07 (CLAUDE.md warnings)"
echo "  4. Implement LESSON-02 (analysis implications doc)"
echo "  5. Implement LESSON-03 (edge weight planning)"
echo ""
echo "To view all lessons learned issues:"
echo "  gh issue list -R $REPO --label lessons-learned"
echo ""
echo "To view high priority lessons:"
echo "  gh issue list -R $REPO --label lessons-learned,high-priority"
echo ""
