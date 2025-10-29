#!/usr/bin/env python3
"""
Validate and enforce clean 4-folder directory structure for reflow systems.

This tool enforces the mandatory 4-folder structure (context, specs, services, docs)
and prevents clutter from prohibited files at system root level.

Usage:
    python3 validate_directory_structure.py <system_path>
    python3 validate_directory_structure.py <system_path> --auto-clean
    python3 validate_directory_structure.py <system_path> --report-only

Example:
    python3 validate_directory_structure.py /home/user/my_system
"""

import os
import sys
import json
import shutil
from pathlib import Path
import argparse
from datetime import datetime
import fnmatch

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

# Embedded mode detection (auto-added during injection)
def _detect_embedded_mode():
    """Detect if running in embedded mode and return appropriate paths."""
    script_path = Path(__file__).resolve()
    
    # Check if we're in context/tools/ (embedded mode)
    if script_path.parent.name == 'tools' and script_path.parent.parent.name == 'context':
        # We're embedded: context/tools/script.py
        system_root = script_path.parent.parent.parent  # Go up to system root
        context_root = script_path.parent.parent  # context/
        
        return {
            'embedded': True,
            'system_root': system_root,
            'context_root': context_root,
            'tools_path': context_root / 'tools',
            'templates_path': context_root / 'templates',
            'workflows_path': context_root / 'workflows',
            'definitions_path': context_root / 'definitions',
            'tracking_path': context_root / 'tracking'
        }
    else:
        # Standard reflow mode
        reflow_root = script_path.parent.parent  # Assume tools/ is in reflow root
        return {
            'embedded': False,
            'reflow_root': reflow_root,
            'tools_path': reflow_root / 'tools',
            'templates_path': reflow_root / 'templates',
            'workflows_path': reflow_root / 'workflows',
            'definitions_path': reflow_root / 'definitions'
        }

# Get mode configuration
_MODE_CONFIG = _detect_embedded_mode()

def _get_system_path(provided_path=None):
    """Get system path, handling both embedded and standard modes."""
    if provided_path:
        return Path(provided_path).resolve()
    
    if _MODE_CONFIG['embedded']:
        # In embedded mode, system is parent of context/
        return _MODE_CONFIG['system_root']
    else:
        # In standard mode, assume current directory or provided path
        return Path.cwd()

# Directory structure rules
ALLOWED_ROOT_FOLDERS = ['context', 'specs', 'services', 'docs']

PROHIBITED_PATTERNS = [
    '*.md',  # Except README.md in some cases
    '*_summary*',
    '*_report*', 
    '*_status*',
    '*_update*',
    '*_overview*',
    '*.backup',
    '*.tmp',
    '*.temp',
    '*.bak',
    '.DS_Store',
    'Thumbs.db'
]

ALLOWED_ROOT_FILES = [
    'README.md',  # System readme is sometimes acceptable
    '.gitignore', # Git configuration
    '.gitattributes',
    'LICENSE',
    'requirements.txt',  # If system has Python deps
    'package.json',  # If system has Node deps
    'Makefile',  # Build system
    'docker-compose.yml',  # Container orchestration
    'Dockerfile'  # Container definition
]

def load_behavioral_rules():
    """Load behavioral rules for directory structure enforcement."""
    if _MODE_CONFIG['embedded']:
        rules_path = _MODE_CONFIG['context_root'] / 'workflows' / 'instructions' / '1-behavioral-rules.json'
    else:
        rules_path = _MODE_CONFIG['reflow_root'] / 'instructions' / '1-behavioral-rules.json'
    
    if rules_path.exists():
        try:
            rules = safe_load_json(rules_path, file_type_description="behavioral rules file")
            return rules.get('DIRECTORY_STRUCTURE_ENFORCEMENT', {})
        except (JSONValidationError, FileNotFoundError) as e:
            # Fallback to default rules if file can't be loaded
            print(f"Warning: Could not load behavioral rules from {rules_path}: {e}")
            pass
    
    # Fallback rules if file not found
    return {
        "allowed_root_folders": ALLOWED_ROOT_FOLDERS,
        "prohibited_at_root": [
            "*.md files (except system README.md if explicitly needed)",
            "*.json files (except build_ready_index.json in services/)",
            "*.txt files", 
            "*_summary* files",
            "*_report* files",
            "*_status* files",
            "*.backup files",
            "*.tmp files"
        ]
    }

def scan_system_directory(system_path):
    """Scan system directory and categorize all items."""
    system_path = Path(system_path)
    
    if not system_path.exists():
        return None, f"System path does not exist: {system_path}"
    
    scan_results = {
        'allowed_folders': [],
        'prohibited_folders': [],
        'allowed_files': [],
        'prohibited_files': [],
        'missing_folders': [],
        'total_items': 0
    }
    
    # Check for required folders
    for folder_name in ALLOWED_ROOT_FOLDERS:
        folder_path = system_path / folder_name
        if folder_path.exists() and folder_path.is_dir():
            scan_results['allowed_folders'].append(folder_name)
        else:
            scan_results['missing_folders'].append(folder_name)
    
    # Scan all items in system root
    try:
        for item in system_path.iterdir():
            scan_results['total_items'] += 1
            
            if item.is_dir():
                if item.name in ALLOWED_ROOT_FOLDERS:
                    continue  # Already counted above
                else:
                    scan_results['prohibited_folders'].append(item.name)
            
            elif item.is_file():
                # Check if file is allowed
                if item.name in ALLOWED_ROOT_FILES:
                    scan_results['allowed_files'].append(item.name)
                else:
                    # Check against prohibited patterns
                    is_prohibited = False
                    for pattern in PROHIBITED_PATTERNS:
                        if fnmatch.fnmatch(item.name, pattern):
                            is_prohibited = True
                            break
                    
                    if is_prohibited:
                        scan_results['prohibited_files'].append(item.name)
                    else:
                        # File doesn't match prohibited patterns, but check if it should be elsewhere
                        if item.suffix.lower() in ['.json', '.md', '.txt', '.log']:
                            scan_results['prohibited_files'].append(item.name + " (should be in appropriate folder)")
                        else:
                            scan_results['allowed_files'].append(item.name)
    
    except PermissionError as e:
        return None, f"Permission denied scanning directory: {e}"
    
    return scan_results, None

def generate_cleanup_plan(system_path, scan_results):
    """Generate a plan for cleaning up prohibited items."""
    system_path = Path(system_path)
    cleanup_plan = {
        'actions': [],
        'safe_removals': [],
        'suggested_moves': [],
        'manual_review': []
    }
    
    # Plan for prohibited files
    for file_name in scan_results['prohibited_files']:
        file_path = system_path / file_name.split(' (')[0]  # Remove annotation
        
        if not file_path.exists():
            continue
        
        # Categorize cleanup action
        if any(fnmatch.fnmatch(file_name, pattern) for pattern in ['*.backup', '*.tmp', '*.temp', '*.bak']):
            cleanup_plan['safe_removals'].append({
                'path': str(file_path),
                'reason': 'Temporary/backup file',
                'action': 'delete'
            })
        elif file_name.endswith('.md'):
            if 'summary' in file_name.lower() or 'report' in file_name.lower() or 'status' in file_name.lower():
                cleanup_plan['safe_removals'].append({
                    'path': str(file_path),
                    'reason': 'Prohibited report/summary file',
                    'action': 'delete'
                })
            else:
                cleanup_plan['suggested_moves'].append({
                    'path': str(file_path),
                    'destination': str(system_path / 'docs' / file_name),
                    'reason': 'Markdown file should be in docs/',
                    'action': 'move'
                })
        elif file_name.endswith('.json'):
            # JSON files usually belong in specs or context
            if 'config' in file_name.lower() or 'settings' in file_name.lower():
                cleanup_plan['suggested_moves'].append({
                    'path': str(file_path),
                    'destination': str(system_path / 'context' / file_name),
                    'reason': 'Configuration JSON should be in context/',
                    'action': 'move'
                })
            else:
                cleanup_plan['suggested_moves'].append({
                    'path': str(file_path),
                    'destination': str(system_path / 'specs' / 'machine' / file_name),
                    'reason': 'JSON spec should be in specs/machine/',
                    'action': 'move'
                })
        else:
            cleanup_plan['manual_review'].append({
                'path': str(file_path),
                'reason': 'File type/purpose unclear',
                'action': 'review'
            })
    
    # Plan for prohibited folders
    for folder_name in scan_results['prohibited_folders']:
        folder_path = system_path / folder_name
        cleanup_plan['manual_review'].append({
            'path': str(folder_path),
            'reason': 'Additional folder not in 4-folder structure',
            'action': 'review'
        })
    
    return cleanup_plan

def execute_cleanup(system_path, cleanup_plan, auto_confirm=False):
    """Execute the cleanup plan."""
    system_path = Path(system_path)
    executed_actions = []
    failed_actions = []
    
    # Create missing directories for moves
    for action in cleanup_plan['suggested_moves']:
        dest_path = Path(action['destination'])
        dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Execute safe removals
    for action in cleanup_plan['safe_removals']:
        if not auto_confirm:
            response = input(f"Delete {action['path']} ({action['reason']})? [y/N]: ")
            if response.lower() != 'y':
                continue
        
        try:
            os.remove(action['path'])
            executed_actions.append(f"Deleted: {action['path']}")
        except Exception as e:
            failed_actions.append(f"Failed to delete {action['path']}: {e}")
    
    # Execute suggested moves
    for action in cleanup_plan['suggested_moves']:
        if not auto_confirm:
            response = input(f"Move {action['path']} to {action['destination']} ({action['reason']})? [y/N]: ")
            if response.lower() != 'y':
                continue
        
        try:
            shutil.move(action['path'], action['destination'])
            executed_actions.append(f"Moved: {action['path']} -> {action['destination']}")
        except Exception as e:
            failed_actions.append(f"Failed to move {action['path']}: {e}")
    
    return executed_actions, failed_actions

def log_cleanup_action(system_path, executed_actions, failed_actions):
    """Log cleanup actions to process log."""
    system_path = Path(system_path)
    process_log = system_path / 'context' / 'process_log.md'
    
    if not process_log.exists():
        # Create basic process log if it doesn't exist
        process_log.parent.mkdir(exist_ok=True)
        with open(process_log, 'w') as f:
            f.write("# Process Log\n\n")
    
    # Append cleanup log entry
    try:
        with open(process_log, 'a') as f:
            f.write(f"\n## Directory Structure Cleanup - {datetime.now().isoformat()}\n\n")
            
            if executed_actions:
                f.write("### Actions Executed:\n")
                for action in executed_actions:
                    f.write(f"- ✅ {action}\n")
                f.write("\n")
            
            if failed_actions:
                f.write("### Actions Failed:\n")
                for action in failed_actions:
                    f.write(f"- ❌ {action}\n")
                f.write("\n")
            
            f.write("### Tool: validate_directory_structure.py\n")
            f.write("### Purpose: Maintain clean 4-folder structure (context, specs, services, docs)\n\n")
    except:
        pass  # Don't fail if logging doesn't work

def generate_validation_report(system_path, scan_results, cleanup_plan):
    """Generate comprehensive validation report."""
    print(f"\n📋 DIRECTORY STRUCTURE VALIDATION REPORT")
    print(f"🎯 System: {system_path}")
    print(f"📅 Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall status
    has_issues = (len(scan_results['prohibited_files']) > 0 or 
                 len(scan_results['prohibited_folders']) > 0 or
                 len(scan_results['missing_folders']) > 0)
    
    if has_issues:
        print("❌ VALIDATION FAILED - Issues found")
    else:
        print("✅ VALIDATION PASSED - Clean 4-folder structure")
    
    print(f"\n📊 Summary:")
    print(f"  Total items scanned: {scan_results['total_items']}")
    print(f"  Required folders found: {len(scan_results['allowed_folders'])}/{len(ALLOWED_ROOT_FOLDERS)}")
    print(f"  Prohibited files: {len(scan_results['prohibited_files'])}")
    print(f"  Prohibited folders: {len(scan_results['prohibited_folders'])}")
    
    # Required folders status
    print(f"\n📁 Required Folders:")
    for folder in ALLOWED_ROOT_FOLDERS:
        if folder in scan_results['allowed_folders']:
            print(f"  ✅ {folder}/")
        else:
            print(f"  ❌ {folder}/ (missing)")
    
    # Allowed files
    if scan_results['allowed_files']:
        print(f"\n📄 Allowed Files:")
        for file_name in sorted(scan_results['allowed_files']):
            print(f"  ✅ {file_name}")
    
    # Issues found
    if scan_results['prohibited_files']:
        print(f"\n⚠️  Prohibited Files ({len(scan_results['prohibited_files'])}):")
        for file_name in sorted(scan_results['prohibited_files']):
            print(f"  ❌ {file_name}")
    
    if scan_results['prohibited_folders']:
        print(f"\n⚠️  Prohibited Folders ({len(scan_results['prohibited_folders'])}):")
        for folder_name in sorted(scan_results['prohibited_folders']):
            print(f"  ❌ {folder_name}/")
    
    # Cleanup plan
    if cleanup_plan['safe_removals'] or cleanup_plan['suggested_moves']:
        print(f"\n🔧 Cleanup Plan:")
        
        if cleanup_plan['safe_removals']:
            print(f"  Safe to remove ({len(cleanup_plan['safe_removals'])}):")
            for action in cleanup_plan['safe_removals']:
                print(f"    🗑️  {Path(action['path']).name} - {action['reason']}")
        
        if cleanup_plan['suggested_moves']:
            print(f"  Suggested moves ({len(cleanup_plan['suggested_moves'])}):")
            for action in cleanup_plan['suggested_moves']:
                src_name = Path(action['path']).name
                dest_folder = Path(action['destination']).parent.name
                print(f"    📦 {src_name} → {dest_folder}/ - {action['reason']}")
        
        if cleanup_plan['manual_review']:
            print(f"  Requires manual review ({len(cleanup_plan['manual_review'])}):")
            for action in cleanup_plan['manual_review']:
                print(f"    🤔 {Path(action['path']).name} - {action['reason']}")
    
    return not has_issues

def main():
    parser = argparse.ArgumentParser(description='Validate and enforce 4-folder directory structure')
    parser.add_argument('system_path', help='Path to system directory to validate')
    parser.add_argument('--auto-clean', action='store_true', help='Automatically execute safe cleanup actions')
    parser.add_argument('--report-only', action='store_true', help='Generate report without cleanup options')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(args.system_path)
    except PathSecurityError as e:
        print(f"❌ Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ System path does not exist: {args.system_path}")
        sys.exit(1)
    
    # Scan directory
    scan_results, error = scan_system_directory(system_path)
    if error:
        print(f"❌ Scan failed: {error}")
        sys.exit(1)
    
    # Generate cleanup plan
    cleanup_plan = generate_cleanup_plan(system_path, scan_results)
    
    if args.json:
        # JSON output mode
        output = {
            "system_path": str(system_path),
            "timestamp": datetime.now().isoformat(),
            "scan_results": scan_results,
            "cleanup_plan": cleanup_plan,
            "validation_passed": len(scan_results['prohibited_files']) == 0 and len(scan_results['prohibited_folders']) == 0
        }
        print(json.dumps(output, indent=2))
        return
    
    # Generate report
    validation_passed = generate_validation_report(system_path, scan_results, cleanup_plan)
    
    # Handle cleanup if requested and needed
    if not args.report_only and (cleanup_plan['safe_removals'] or cleanup_plan['suggested_moves']):
        print(f"\n🔧 Cleanup Options:")
        print("  1. Run with --auto-clean for automatic cleanup")
        print("  2. Execute cleanup interactively now")
        print("  3. Skip cleanup")
        
        if args.auto_clean:
            print("\n🔄 Executing automatic cleanup...")
            executed_actions, failed_actions = execute_cleanup(system_path, cleanup_plan, auto_confirm=True)
        else:
            response = input("\nExecute cleanup interactively? [y/N]: ")
            if response.lower() == 'y':
                executed_actions, failed_actions = execute_cleanup(system_path, cleanup_plan, auto_confirm=False)
            else:
                executed_actions, failed_actions = [], []
        
        if executed_actions or failed_actions:
            print(f"\n📋 Cleanup Results:")
            if executed_actions:
                print(f"  ✅ Completed ({len(executed_actions)}):")
                for action in executed_actions:
                    print(f"    {action}")
            if failed_actions:
                print(f"  ❌ Failed ({len(failed_actions)}):")
                for action in failed_actions:
                    print(f"    {action}")
            
            # Log cleanup actions
            log_cleanup_action(system_path, executed_actions, failed_actions)
    
    # Final recommendations
    if not validation_passed:
        print(f"\n🎯 Recommendations:")
        print("  • Keep only 4 folders at system root: context/, specs/, services/, docs/")
        print("  • Move documentation files to docs/")
        print("  • Move configuration files to context/")  
        print("  • Move specification files to specs/machine/")
        print("  • Remove temporary and backup files")
        print("  • Run this tool regularly to maintain clean structure")
    
    sys.exit(0 if validation_passed else 1)

if __name__ == "__main__":
    main()