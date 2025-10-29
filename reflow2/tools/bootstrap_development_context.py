#!/usr/bin/env python3
"""
Development Workflow Bootstrap Tool
Creates and initializes development tracking files for service development workflow.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

# Adjust paths for reflow directory structure
REFLOW_ROOT = Path(__file__).parent.parent
TEMPLATES_PATH = REFLOW_ROOT / "templates"

def load_template(template_name):
    """Load a template file from the templates directory."""
    # Security: Sanitize template path (v3.4.0 fix - SV-01)
    try:
        reflow_root = validate_system_root(REFLOW_ROOT)
        template_path = sanitize_path(
            f"templates/{template_name}",
            reflow_root,
            must_exist=True
        )
    except (PathSecurityError, FileNotFoundError) as e:
        raise FileNotFoundError(f"Template not found or path security violation: {template_name} - {e}")

    if template_path.suffix == '.json':
        try:
            return safe_load_json(template_path, file_type_description=f"template file '{template_name}'")
        except JSONValidationError as e:
            raise ValueError(f"Invalid JSON in template {template_name}: {e}")
    else:
        with open(template_path) as f:
            return f.read()

def bootstrap_development_context(system_name, system_path):
    """
    Bootstrap development context for a system.

    Args:
        system_name: Name of the system
        system_path: Pre-validated Path object to system directory
    """
    system_dir = system_path
    system_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    created_files = []

    print(f"🔧 Bootstrapping development context for system: {system_name}")
    print(f"📁 System directory: {system_dir}")

    # Check for build_ready_index.json
    # Security: Sanitize build_ready_index path (v3.4.0 fix - SV-01)
    try:
        build_ready_path = sanitize_path(
            "build_ready_index.json",
            system_dir,
            must_exist=False
        )
        if not build_ready_path.exists():
            print(f"⚠️  Warning: build_ready_index.json not found at {build_ready_path}")
            print("   This file is required for development workflow entry")
    except PathSecurityError as e:
        print(f"⚠️  Warning: Could not check for build_ready_index.json: {e}")
    
    # Create dev_progress_tracker.json
    try:
        dev_tracker_template = load_template("dev_progress_tracker_template.json")
        dev_tracker_template["system_name"] = system_name
        dev_tracker_template["started_timestamp"] = timestamp
        dev_tracker_template["last_updated"] = timestamp

        # Security: Sanitize dev_progress_tracker path (v3.4.0 fix - SV-01)
        dev_tracker_path = sanitize_path(
            "dev_progress_tracker.json",
            system_dir,
            must_exist=False
        )
        with open(dev_tracker_path, 'w') as f:
            json.dump(dev_tracker_template, f, indent=2)
        created_files.append(dev_tracker_path)
        print(f"✅ Created: {dev_tracker_path}")
    except PathSecurityError as e:
        print(f"❌ Failed to create dev_progress_tracker.json: Path security violation: {e}")
    except Exception as e:
        print(f"❌ Failed to create dev_progress_tracker.json: {e}")
    
    # Create dev_current_focus.md
    try:
        dev_focus_template = load_template("dev_current_focus_template.md")
        dev_focus_content = dev_focus_template.replace("REPLACE_WITH_SYSTEM_NAME", system_name)
        dev_focus_content = dev_focus_content.replace("YYYY-MM-DD HH:MM:SS",
                                                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        dev_focus_content = dev_focus_content.replace("CURRENT_STAGE_ID", "D1")
        dev_focus_content = dev_focus_content.replace("STAGE_NAME", "Initialization & Environment Bootstrap")
        dev_focus_content = dev_focus_content.replace("CURRENT_SERVICE_ID", "TBD")
        dev_focus_content = dev_focus_content.replace("DESCRIPTION_OF_NEXT_ACTION",
                                                     "Parse build_ready_index.json and enumerate dependency layers")
        dev_focus_content = dev_focus_content.replace("DETAILED_DESCRIPTION_OF_CURRENT_TASK",
                                                     "Establish reproducible development environment per service dependency groups")

        # Security: Sanitize dev_current_focus path (v3.4.0 fix - SV-01)
        dev_focus_path = sanitize_path(
            "dev_current_focus.md",
            system_dir,
            must_exist=False
        )
        with open(dev_focus_path, 'w') as f:
            f.write(dev_focus_content)
        created_files.append(dev_focus_path)
        print(f"✅ Created: {dev_focus_path}")
    except PathSecurityError as e:
        print(f"❌ Failed to create dev_current_focus.md: Path security violation: {e}")
    except Exception as e:
        print(f"❌ Failed to create dev_current_focus.md: {e}")
    
    # Create dev_working_memory.json
    try:
        dev_memory_template = load_template("dev_working_memory_template.json")
        dev_memory_template["system_name"] = system_name
        dev_memory_template["last_refresh_timestamp"] = timestamp
        dev_memory_template["next_action"] = "Parse build_ready_index.json to enumerate dependency layers"
        dev_memory_template["snapshot_management"]["last_snapshot_timestamp"] = timestamp
        dev_memory_template["development_metrics"]["stage_start_time"] = timestamp

        # Security: Sanitize dev_working_memory path (v3.4.0 fix - SV-01)
        dev_memory_path = sanitize_path(
            "dev_working_memory.json",
            system_dir,
            must_exist=False
        )
        with open(dev_memory_path, 'w') as f:
            json.dump(dev_memory_template, f, indent=2)
        created_files.append(dev_memory_path)
        print(f"✅ Created: {dev_memory_path}")
    except PathSecurityError as e:
        print(f"❌ Failed to create dev_working_memory.json: Path security violation: {e}")
    except Exception as e:
        print(f"❌ Failed to create dev_working_memory.json: {e}")
    
    # Create dev_process_log.md
    try:
        log_content = f"""# Development Process Log

**System:** {system_name}
**Started:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Bootstrap Entry
- Development context initialized
- Tracking files created
- Ready for Stage D1: Initialization & Environment Bootstrap

## Process Log
<!-- Log entries will be added here as development progresses -->

---
*This log tracks the development process for {system_name}. Each stage transition, quality gate, and significant decision should be recorded here.*
"""

        # Security: Sanitize dev_process_log path (v3.4.0 fix - SV-01)
        dev_log_path = sanitize_path(
            "dev_process_log.md",
            system_dir,
            must_exist=False
        )
        with open(dev_log_path, 'w') as f:
            f.write(log_content)
        created_files.append(dev_log_path)
        print(f"✅ Created: {dev_log_path}")
    except PathSecurityError as e:
        print(f"❌ Failed to create dev_process_log.md: Path security violation: {e}")
    except Exception as e:
        print(f"❌ Failed to create dev_process_log.md: {e}")
    
    # Create dev_context_checkpoint.md
    try:
        checkpoint_content = f"""# Context Checkpoint

**System:** {system_name}
**Timestamp:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Stage:** D1 - Initialization & Environment Bootstrap

## Active Service
TBD (will be determined from build_ready_index.json)

## Stage & Subtasks Remaining
- [ ] D1.1: Parse build_ready_index.json to enumerate dependency layers
- [ ] D1.2: Create dev_progress_tracker.json with all services initial status=not_started
- [ ] D1.3: Initialize per-service dev_current_focus.md with first implementation target
- [ ] D1.4: Validate required runtimes, toolchains, and lint/test frameworks
- [ ] D1.5: Record environment baseline hashes/versions to dev_process_log.md
- [ ] D1.6: Create SYSTEM_MISSION_STATEMENT.md capturing the fundamental 'why' of the system
- [ ] D1.7: Create USER_SCENARIOS.md with realistic user stories and expected outcomes
- [ ] D1.8: Create SUCCESS_CRITERIA.md defining measurable mission success indicators

## Recently Completed Actions
- Bootstrap development context initialized
- Development tracking files created

## Blocking Issues / Risks
None identified at bootstrap

## Evidence Artifacts Added
- dev_progress_tracker.json
- dev_current_focus.md
- dev_working_memory.json
- dev_process_log.md
- dev_context_checkpoint.md (this file)
"""

        # Security: Sanitize dev_context_checkpoint path (v3.4.0 fix - SV-01)
        checkpoint_path = sanitize_path(
            "dev_context_checkpoint.md",
            system_dir,
            must_exist=False
        )
        with open(checkpoint_path, 'w') as f:
            f.write(checkpoint_content)
        created_files.append(checkpoint_path)
        print(f"✅ Created: {checkpoint_path}")
    except PathSecurityError as e:
        print(f"❌ Failed to create dev_context_checkpoint.md: Path security violation: {e}")
    except Exception as e:
        print(f"❌ Failed to create dev_context_checkpoint.md: {e}")
    
    # Summary
    print(f"\n🎉 Bootstrap complete!")
    print(f"Created {len(created_files)} development tracking files:")
    for file_path in created_files:
        print(f"  - {file_path.name}")
    
    print(f"\n📋 Next steps:")
    print(f"1. Ensure build_ready_index.json exists in {system_dir}")
    print(f"2. Review and update dev_current_focus.md")
    print(f"3. Begin Stage D1: Initialization & Environment Bootstrap")
    print(f"4. Use development workflow for guided implementation")
    
    return created_files

def main():
    parser = argparse.ArgumentParser(description="Bootstrap development context for service development workflow")
    parser.add_argument("system_name", help="Name of the system being developed")
    parser.add_argument("--system-path", default=None, 
                       help="Path to system directory (default: systems/<system_name>)")
    parser.add_argument("--force", action="store_true",
                       help="Overwrite existing files if they exist")
    
    args = parser.parse_args()
    
    if args.system_path is None:
        # Default to systems/<system_name> relative to current directory
        args.system_path = f"systems/{args.system_name}"

    # Security: Validate system path (v3.4.0 fix - SV-01)
    # Allow creating new directory, but validate it's not a traversal path
    try:
        system_path = Path(args.system_path).resolve()

        # Check for path traversal attempts
        if ".." in args.system_path.split("/"):
            raise PathSecurityError("Path traversal detected in system path")

        # Create directory if it doesn't exist (mkdir will be called in bootstrap function)
        # But validate parent exists
        if system_path.parent.exists():
            system_path = validate_system_root(system_path) if system_path.exists() else system_path
        else:
            print(f"❌ Error: Parent directory {system_path.parent} does not exist")
            sys.exit(1)

    except PathSecurityError as e:
        print(f"❌ Path security violation: {e}")
        sys.exit(1)

    # Check if files already exist
    existing_files = []
    tracking_files = [
        "dev_progress_tracker.json",
        "dev_current_focus.md",
        "dev_working_memory.json",
        "dev_process_log.md",
        "dev_context_checkpoint.md"
    ]

    for file_name in tracking_files:
        # Security: Sanitize file path (v3.4.0 fix - SV-01)
        try:
            if system_path.exists():
                file_path = sanitize_path(file_name, system_path, must_exist=False)
                if file_path.exists():
                    existing_files.append(file_name)
        except PathSecurityError:
            # Ignore security errors during existence check - will be caught during creation
            pass

    if existing_files and not args.force:
        print(f"❌ Error: The following files already exist in {system_path}:")
        for file_name in existing_files:
            print(f"  - {file_name}")
        print(f"\nUse --force to overwrite existing files")
        sys.exit(1)
    
    try:
        created_files = bootstrap_development_context(args.system_name, system_path)
        print(f"\n✅ Development context bootstrap successful!")
    except Exception as e:
        print(f"❌ Bootstrap failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()