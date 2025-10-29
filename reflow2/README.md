# Reflow - Systems Engineering Workflow

**Version 3.9.1** | Framework-agnostic systems engineering for LLM agents

## What is Reflow?

Reflow is a structured workflow that guides LLM agents (Claude, GPT-4, etc.) through designing, architecting, and building complex systems. It provides step-by-step workflows, automated validation, and comprehensive tooling for creating production-ready architectures.

**Key capabilities:**
- Framework-agnostic: Works with software (UAF), biology, social networks, ecosystems, workflows, and custom frameworks
- Automatic approach detection: Bottom-up (existing components) or top-down (greenfield)
- Production-ready: Designs for real operational conditions from day one
- Modular: 6 separate workflows - use what you need, skip what you don't

## Quick Start

### Web-Based Usage (Recommended)

**GitHub Codespaces** (Most accessible - free tier available):
```
1. Create your system repo on GitHub
2. Open repo → Code → Codespaces → Create codespace
3. Clone reflow: git clone https://github.com/sligara7/reflow
4. Say: "Implement workflow in /workspaces/reflow/workflows/00-setup.json
   on system in /workspaces/my_system"
   (Note: Use 00a-basic_setup.json for faster setup)
```

**Claude Code** (https://claude.ai/code - requires Pro/Max):
```
1. Install Claude GitHub app in your repositories (required for private repos)
2. Say: "Implement workflow in github.com/sligara7/reflow/workflows/00-setup.json
   on system in github.com/yourname/my_system"
```

**Resuming work** (next day/session):
```
"Continue workflow from context/working_memory.json in github.com/yourname/my_system"
```

### Local Machine Usage

```bash
# Clone Reflow
git clone https://github.com/sligara7/reflow
mkdir ~/projects/my_system

# Start workflow
"Implement workflow in /path/to/reflow/workflows/00-setup.json on system in ~/projects/my_system"

# Resume work
"Continue workflow from context/working_memory.json in ~/projects/my_system"
```

## The Workflows (v3.7.0 - Modular Architecture)

**NEW in v3.7.0**: Workflows split for **60-95% LLM context reduction**. Load only what you need!

### 1a. Basic Setup (`00a-basic_setup.json`) - 5-10 minutes
- Configure paths (reflow_root, system_root)
- Create directory structure
- Initialize foundational documents
- Optional: Enable automatic git commits
- **Next**: 00b (optional) OR 01a (start architecture)

### 1b. Framework Selection (`00b-framework_selection.json`) - 5-10 minutes [OPTIONAL]
- Detailed framework questionnaire and scoring
- Select architectural framework (UAF, Biology, Social, Ecological, CAS, Decision Flow, Custom)
- **Context Reduction**: 55% - Skip if framework already known
- **Next**: 01a (approach detection)

### 2a. Approach Detection (`01a-approach_detection.json`) - <5 minutes
- **NEW: Automatic approach detection** - LLM scans system directory
- Routes to: 01b (bottom-up) OR 01c (top-down)
- **Context Reduction**: 95% - Lightweight routing step
- **Next**: 01b OR 01c (auto-selected)

### 2b. Bottom-Up Integration (`01b-bottom_up_integration.json`) - 2-3 hours
- For **existing components** - Steps BU-01 through BU-06
- Component inventory, gap analysis (9 gap types), exact code-level deltas
- Integration architecture, validation
- **Context Reduction**: 60% - Only loads bottom-up logic (not top-down)
- **Next**: 02 (artifacts)

### 2c. Top-Down Design (`01c-top_down_design.json`) - 2-4 hours
- For **greenfield** systems - Steps SE-01 through SE-06
- Service identification, architecture design, validation
- Create versioned architecture files, system_of_systems_graph.json
- **Context Reduction**: 60% - Only loads top-down logic (not bottom-up)
- **Next**: 02 (artifacts)

### 3. Artifacts & Visualization (`02-artifacts_visualization.json`) - 1-2 hours
- Generate Interface Contract Documents (ICDs)
- Create Mermaid diagrams
- Generate versioned documentation
- Optional: Skip if architecture-only
- **Next**: 03a (if building) OR END (if architecture-only)

### 4a. Development Implementation (`03a-development_implementation.json`) - Days to weeks
- Optional: Research current development best practices
- Implement services
- Observability instrumentation
- **Context Reduction**: 58% - Coding phase separated from validation
- **Next**: 03b (validation)

### 4b. Development Validation (`03b-development_validation.json`) - 1-2 days
- 80% test coverage validation
- Pre-deployment validation (D-07) with 3 new tools
- Dependency validation, module structure checks, config consistency
- **Context Reduction**: 43% - Testing phase separated from coding
- **Next**: 04a (testing)

### 5a. Testing (`04a-testing.json`) - 1 week
- CI/CD pipeline setup
- Automated testing workflows
- **Context Reduction**: 55% - Testing separated from operations
- **Next**: 04b (operations)

### 5b. Operations (`04b-operations.json`) - 1 week
- Docker Compose validation
- Operational testing
- Deployment and monitoring setup
- **Context Reduction**: 42% - Operations separated from testing
- **Next**: END

### 6. Feature Update (`feature_update.json`) - Variable
- Update existing systems with versioning and backward compatibility tracking

## Workflow Usage Patterns

### New System (Greenfield) - v3.7.0 Flow
```
00a-basic_setup → [optional: 00b-framework_selection] → 01a-approach_detection
→ 01c-top_down_design (auto-selected for empty dir) → 02-artifacts
→ 03a-development_implementation → 03b-development_validation
→ 04a-testing → 04b-operations
```

**Context Savings**: LLM loads only 01c (top-down), skipping 01b (bottom-up) = **60% reduction**

### Existing Components (Bottom-Up Integration) - v3.7.0 Flow
```
00a-basic_setup → [optional: 00b-framework_selection] → 01a-approach_detection
→ 01b-bottom_up_integration (auto-selected for existing code) → 02-artifacts
→ 03a-development_implementation → 03b-development_validation
→ 04a-testing → 04b-operations
```

Example: Integrating 10 Python packages
- LLM scans directory, finds packages, manifests, code
- Routes to 01b (BU-01): Creates component inventory
- BU-02: Defines integration requirements
- BU-03: Detects 9 gap types (missing interfaces, protocol mismatches, etc.)
- BU-04: Generates exact code-level deltas (function signatures, file locations)
- BU-05: Designs integration architecture
- BU-06: Validates and merges with top-down at common validation steps

**Context Savings**: LLM loads only 01b (bottom-up), skipping 01c (top-down) = **60% reduction**

### Fast Setup (Skip Framework Selection) - v3.7.0 Flow
```
00a-basic_setup → 01a-approach_detection → ...
```

**Context Savings**: Skip 00b entirely = **55% additional reduction**

### Architecture Only (No Code)
```
00a-basic_setup → [optional: 00b-framework_selection] → 01a-approach_detection
→ 01b or 01c → 02-artifacts (minimal) → END

Result: Architecture specs, diagrams, ICDs - no service implementation
```

### Feature Update (Existing System)
```
feature_update.json

Process: Read existing architecture → Propose changes → Validate impact →
Update with versioning → Generate updated artifacts
```

## Supported Frameworks

**Framework selection happens in step S-01A with user confirmation required.**

- **UAF 1.2** - Software/hardware systems (microservices, IoT)
- **Systems Biology** - Gene networks, metabolic pathways
- **Social Network Analysis** - Organizations, communities, influence networks
- **Ecological Systems** - Food webs, species interactions
- **Complex Adaptive Systems** - Markets, emergent systems
- **Decision Flow** - Workflows, state machines, decision processes
- **Custom** - LLM-generated for novel domains

**Important**: Framework choice determines which NetworkX analyses you can run. See `docs/NETWORKX_ANALYSIS_GUIDE.md` for detailed guidance.

## What You Get

**Machine-readable artifacts:**
- Component/service architecture files (versioned)
- System of systems graph with NetworkX analysis
- Interface Contract Documents (ICDs)
- Port registry (prevents deployment conflicts)
- Version manifest

**Human-readable artifacts:**
- Mermaid diagrams (system, service, sequence, deployment)
- Architecture documentation
- Architecture Decision Records (ADRs)

**Implementation & operations:**
- Fully implemented services with 80%+ test coverage
- CI/CD pipelines configured
- Docker Compose for deployment
- Monitoring and alerting

**Quality assurance:**
- 10 quality gates (7 blocking)
- Automated validation
- Contract compliance verification

## Bottom-Up Integration (NEW in v3.4.0)

Reflow now supports **bottom-up integration** for existing components:

**Use cases:**
- Integrating 10+ Python packages into a cohesive system
- Integrating legacy systems not designed to work together
- Need exact component-level deltas (function/module changes)

**Process:**
1. **Component Inventory (BU-01)**: Catalog existing components, interfaces, dependencies
2. **Integration Requirements (BU-02)**: Define how components should work together
3. **Gap Analysis (BU-03)**: Detect 9 gap types using production-ready tool:
   - missing_interface, protocol_mismatch, data_model_incompatibility, missing_mediator
   - circular_dependency, conflicting_requirements, version_incompatibility
   - performance_gap, security_gap
4. **Component Deltas (BU-04)**: Generate exact code changes at function/class/module level
   - Example: "Add function get_user_permissions(user_id: str) -> List[str] to src/auth.py"
   - Includes: Function signatures, dependencies to add, configuration changes
   - Automatic semantic versioning (1.0.0 → 2.0.0 if breaking changes)
5. **Integration Architecture (BU-05)**: Design multi-tier nested architecture
6. **Validation (BU-06)**: Validate deltas, architecture, dependencies

**Tools provided:**
- `analyze_integration_gaps.py` (850+ lines) - Detects all 9 gap types
- `generate_component_deltas.py` (690+ lines) - Generates exact code-level changes
- `validate_component_deltas.py` (580+ lines) - Validates delta feasibility

## Directory Structure

**Reflow tooling (read-only reference):**
```
reflow/
├── workflows/           # 15 workflow files (9 modular + 4 deprecated + 2 special)
├── workflow_steps/      # Detailed step definitions
├── tools/              # 32 Python tools (v3.8.0: +3 human documentation tools)
├── templates/          # 36+ templates
└── definitions/        # Framework definitions
```

**Your system (where you work):**
```
<your_system>/
├── context/            # LLM tracking (working_memory.json)
├── specs/
│   ├── machine/       # Architecture JSONs, ICDs, graphs
│   └── human/         # Diagrams, docs
├── services/          # Service implementations
└── docs/              # Foundational documents
```

## Key Features

**Automatic Approach Detection (NEW):**
- LLM automatically detects bottom-up vs top-down by scanning system directory
- No human intervention required
- Evidence-based decision with transparent reasoning
- Fallback to user confirmation if ambiguous

**Production-Ready from Day One:**
- 10 IT considerations: Service decomposition, containerization, IaC, CI/CD, scalability, security, monitoring, networking, cost, testing
- Design for real operational conditions: failures, attacks, load spikes, network partitions
- Testing strategy defined upfront (systems engineering phase)
- Prevents costly retrofitting (10-100x savings)

**Enterprise Requirements Built-In (UAF/IT systems):**
- Security: Authentication, authorization, API gateway, rate limiting, encryption, audit logging
- Deployment: One-command deployment, automated rollback, health checks
- UX: Intuitive APIs, clear error messages, comprehensive documentation

**Human Documentation & Bidirectional Translation (NEW v3.8.0):**
- Auto-generate human-readable markdown from machine specs
- Bidirectional translation: Edit markdown → Propagate to JSON with validation
- Safe component swapping with interface compatibility checking
- PNG/SVG diagram rendering for stakeholder presentations
- Version-controlled architecture evolution tracking
- Non-technical stakeholders can review and propose architecture changes

**Architecture Lifecycle Tracking (NEW v3.5.0):**
- Track architecture evolution: designed → as-built → as-fielded
- Compare implementation vs design to identify drift
- Delta reports with similarity scores and change classification
- Document rationale for deviations, feed insights back to design

**Architecture Versioning:**
- Semantic versioning for all architecture files
- Complete history preserved
- Rollback support via symlinks

## Requirements

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.8+ | Core runtime |
| networkx | latest | Graph operations |
| LLM Agent | Claude/GPT-4 | Workflow execution |
| Docker | optional | Deployment validation |

## Documentation

**Tool Reference:**
- [TOOL_USAGE_SUMMARY.md](docs/TOOL_USAGE_SUMMARY.md) - Comprehensive guide to all 32 tools
- [TOOL_VERSION_MANIFEST.md](docs/TOOL_VERSION_MANIFEST.md) - Tool version history

**Workflow & Features:**
- [NETWORKX_ANALYSIS_GUIDE.md](docs/NETWORKX_ANALYSIS_GUIDE.md) - Framework-specific NetworkX analysis guidance (400+ lines)
- [DECISION_FLOW_FRAMEWORK.md](docs/DECISION_FLOW_FRAMEWORK.md) - Decision Flow Framework documentation (500+ lines)
- [HUMAN_DOCUMENTATION_WORKFLOW_ANALYSIS.md](docs/HUMAN_DOCUMENTATION_WORKFLOW_ANALYSIS.md) - Human documentation workflow (973 lines)
- [BOTTOM_UP_INTEGRATION_DESIGN.md](docs/BOTTOM_UP_INTEGRATION_DESIGN.md) - Bottom-up integration design
- [GIT_AUTOMATION_GUIDE.md](docs/GIT_AUTOMATION_GUIDE.md) - Automatic git commits setup
- [NEW_STRUCTURE_README.md](docs/restructuring/NEW_STRUCTURE_README.md) - Workflow structure reference

## Version History

**v3.9.1 (2025-10-28)** - Current
- **Automatic LLM Context Detection** - Self-reporting for optimal thresholds
  - New tool: `detect_llm_capabilities.py` - LLMs self-report context window
  - Auto-detects model-specific thresholds (Claude 200k → 160k, GPT-4 128k → 102k)
  - System automatically adjusts when switching models (Claude ↔ GPT-4)
  - Context flow analysis uses detected thresholds from working_memory.json
  - Safety margins: 80% (200k+), 75% (100k-200k), 70% (<100k)
- Enhanced CLAUDE.md with mandatory LLM self-reporting instructions
- No manual configuration needed when switching between models!

**v3.9.0 (2025-10-28)**
- **Context Flow Analysis** - Predictive context management for LLM agents
  - Extended `system_of_systems_graph_v2.py` with `--context-flow` analysis mode
  - Models LLM context as first-class architectural parameter
  - Predicts cumulative token accumulation through workflow paths
  - Identifies context bottlenecks BEFORE overflow occurs (default threshold: 40k tokens)
  - Generates automatic refresh recommendations
  - Calculates "context efficiency" as architectural quality metric
  - Enables workflow optimization and LLM capability matching
- Enhanced `working_memory_template.json` with context flow fields
- Shift from reactive to predictive context management

**v3.8.0 (2025-10-28)**
- **Human Documentation & Bidirectional Translation**
  - `generate_human_documentation.py` - Convert machine specs to human-readable markdown
  - `parse_human_documentation.py` - Parse human edits back to machine specs with validation
  - `component_swap.py` - Safe component swapping with interface compatibility checking
  - PNG/SVG rendering support for Mermaid diagrams
  - Bidirectional translation: Human ↔ Machine documentation synchronization
  - Non-technical stakeholders can review architecture and propose changes via markdown edits
- Workflow updates: `02-artifacts_visualization.json` now mandatory (removed "conditional" flag)
- Documentation: Added comprehensive analysis (973 lines) and implementation guide (1,257 lines)

**v3.7.0 (2025-10-27)**
- **60-95% LLM context reduction**: Split 4 workflows into 9 modular workflows
  - 00-setup → 00a-basic_setup + 00b-framework_selection (45-55% reduction)
  - 01-systems_engineering → 01a-approach_detection + 01b-bottom_up + 01c-top_down (60-95% reduction)
  - 03-development → 03a-implementation + 03b-validation (43-58% reduction)
  - 04-testing_operations → 04a-testing + 04b-operations (42-55% reduction)
- Load only relevant workflow paths (not both bottom-up AND top-down)
- System cohesion validation: All 15 workflows validated with system_of_systems_graph_v2.py

**v3.6.1 (2025-10-27)**
- **6 missing components** for Early Testing Integration:
  - 3 validation tools: validate_dependencies.py, validate_module_structure.py, validate_configuration_consistency.py
  - 3 testing templates: operational_testing_objectives, service_risk_assessment, system_test_strategy
- Completes D-07 pre-deployment validation workflow

**v3.6.0 (2025-10-26)**
- Early Testing Integration: Define testing strategy during architecture phase (shift-left)
- Prevents 80-90% of deployment blockers through upfront planning

**v3.5.0 (2025-10-26)**
- Architecture lifecycle tracking: designed → as-built → as-fielded
- Delta reports with similarity scores and drift detection

**v3.4.0 (2025-10-26)**
- Bottom-up integration workflow with 9 gap types, exact code-level deltas
- Automatic approach detection (LLM scans directory and routes to bottom-up or top-down)
- Framework selection enhancement with semantic matching, scoring rubric, user confirmation
- Decision Flow Framework for workflows and state machines
- Framework migration tool
- NetworkX analysis guide (400+ lines)

**v3.3.1 (2025-10-25)**
- Tool cleanup: 24 → 16 focused tools
- Comprehensive tool documentation

**v3.3.0 (2025-10-25)**
- Operational environment design (10 IT considerations)
- Real-world condition planning upfront

**v3.2.0 (2025-10-25)**
- IT system requirements (security, deployment, UX)
- Orphaned service detection
- Port management

**v3.1.0 (2025-10-25)**
- Framework-agnostic support (6+ frameworks)
- Comprehensive NetworkX analysis (25+ algorithms)
- Knowledge gap detection

**v3.0.x (2025-10-24)**
- Modular workflow restructure (6 workflows)
- Architecture versioning
- Git automation, development research

## Contributing

Contributions welcome. For major changes, open an issue first to discuss.

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Version 3.7.0** - Framework-agnostic systems engineering with 60-95% context reduction and modular workflows

[Documentation](docs/) • [Validation Report](docs/validation/v3.7.0_systems_cohesion_validation.md) • [Issues](https://github.com/sligara7/reflow/issues)
