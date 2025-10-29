#!/usr/bin/env python3
"""
Detect LLM capabilities by prompting for self-reporting (v3.9.1).

This tool helps LLMs self-report their context window capabilities,
enabling automatic threshold adjustment for different models.

Usage:
    # Interactive mode (for LLM to call)
    python3 detect_llm_capabilities.py --interactive

    # Manual mode (user specifies)
    python3 detect_llm_capabilities.py --model "Claude Sonnet 4.5" --context-window 200000

    # Update working memory
    python3 detect_llm_capabilities.py --interactive --update-working-memory /path/to/system
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys


def calculate_recommended_threshold(context_window: int) -> dict:
    """
    Calculate recommended threshold based on context window size.

    Uses safety margins:
    - 200k+: 80% (conservative, plenty of room)
    - 100k-200k: 75% (moderate)
    - <100k: 70% (aggressive, frequent refreshes)
    """
    if context_window >= 200000:
        safety_margin = 0.80
        refresh_strategy = "conservative"
    elif context_window >= 100000:
        safety_margin = 0.75
        refresh_strategy = "moderate"
    else:
        safety_margin = 0.70
        refresh_strategy = "aggressive"

    threshold = int(context_window * safety_margin)

    return {
        'threshold': threshold,
        'safety_margin_percent': int(safety_margin * 100),
        'refresh_strategy': refresh_strategy
    }


def detect_llm_capabilities_interactive() -> dict:
    """
    Interactive mode: Prompts for LLM to self-report capabilities.

    LLMs should respond to prompts about their context window.
    """
    print("=" * 60)
    print("LLM Capability Detection (v3.9.1)")
    print("=" * 60)
    print("\nThis tool helps detect your context window for optimal")
    print("threshold configuration in Reflow workflows.\n")

    # Prompt for model name
    print("What LLM model are you?")
    print("Examples: 'Claude Sonnet 4.5', 'GPT-4 Turbo', 'GPT-3.5'")
    model_name = input("Model name: ").strip()

    if not model_name:
        model_name = "Unknown LLM"

    # Prompt for context window
    print("\nWhat is your context window in tokens?")
    print("Examples: 200000 (Claude), 128000 (GPT-4), 16000 (GPT-3.5)")

    while True:
        try:
            context_window_str = input("Context window (tokens): ").strip()
            context_window = int(context_window_str)

            if context_window < 1000:
                print(f"⚠️  Warning: {context_window} tokens seems very low. Are you sure?")
                confirm = input("Continue? (yes/no): ").strip().lower()
                if confirm != 'yes':
                    continue

            break
        except ValueError:
            print("❌ Invalid input. Please enter an integer (e.g., 200000)")

    # Calculate recommended threshold
    threshold_info = calculate_recommended_threshold(context_window)

    capabilities = {
        'model_name': model_name,
        'context_window_tokens': context_window,
        'recommended_threshold': threshold_info['threshold'],
        'safety_margin_percent': threshold_info['safety_margin_percent'],
        'refresh_strategy': threshold_info['refresh_strategy'],
        'auto_detected': True,
        'detection_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'detection_method': 'interactive'
    }

    # Display results
    print("\n" + "=" * 60)
    print("✅ LLM Capabilities Detected")
    print("=" * 60)
    print(f"Model: {model_name}")
    print(f"Context Window: {context_window:,} tokens")
    print(f"Recommended Threshold: {threshold_info['threshold']:,} tokens")
    print(f"Safety Margin: {threshold_info['safety_margin_percent']}%")
    print(f"Refresh Strategy: {threshold_info['refresh_strategy']}")
    print("=" * 60)

    return capabilities


def update_working_memory(system_root: Path, capabilities: dict) -> bool:
    """Update working_memory.json with detected LLM capabilities."""
    working_memory_path = system_root / 'context' / 'working_memory.json'

    if not working_memory_path.exists():
        print(f"❌ Error: working_memory.json not found at {working_memory_path}")
        return False

    try:
        with open(working_memory_path, 'r') as f:
            working_memory = json.load(f)

        # Update llm_capabilities section
        if 'context_management' not in working_memory:
            working_memory['context_management'] = {}

        working_memory['context_management']['llm_capabilities'] = capabilities

        # Update context_flow_analysis threshold if enabled
        if 'context_flow_analysis' in working_memory['context_management']:
            working_memory['context_management']['context_flow_analysis']['threshold'] = capabilities['recommended_threshold']
            print(f"✅ Updated context flow threshold to {capabilities['recommended_threshold']:,} tokens")

        # Write back
        with open(working_memory_path, 'w') as f:
            json.dump(working_memory, f, indent=2)

        print(f"✅ Updated working_memory.json at {working_memory_path}")
        return True

    except Exception as e:
        print(f"❌ Error updating working_memory.json: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Detect LLM capabilities for automatic threshold configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive detection (LLM self-reports)
  python3 detect_llm_capabilities.py --interactive

  # Interactive with working memory update
  python3 detect_llm_capabilities.py --interactive --update-working-memory /path/to/system

  # Manual specification
  python3 detect_llm_capabilities.py --model "GPT-4 Turbo" --context-window 128000

  # Manual with working memory update
  python3 detect_llm_capabilities.py --model "Claude Sonnet 4.5" --context-window 200000 \\
      --update-working-memory /path/to/system
        """
    )

    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode (LLM self-reports)')
    parser.add_argument('--model', type=str,
                       help='Model name (e.g., "Claude Sonnet 4.5")')
    parser.add_argument('--context-window', type=int,
                       help='Context window in tokens (e.g., 200000)')
    parser.add_argument('--update-working-memory', type=str,
                       help='System root path to update working_memory.json')

    args = parser.parse_args()

    # Detect capabilities
    if args.interactive:
        capabilities = detect_llm_capabilities_interactive()
    elif args.model and args.context_window:
        threshold_info = calculate_recommended_threshold(args.context_window)
        capabilities = {
            'model_name': args.model,
            'context_window_tokens': args.context_window,
            'recommended_threshold': threshold_info['threshold'],
            'safety_margin_percent': threshold_info['safety_margin_percent'],
            'refresh_strategy': threshold_info['refresh_strategy'],
            'auto_detected': False,
            'detection_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'detection_method': 'manual'
        }

        print(f"\n✅ LLM Capabilities: {args.model}")
        print(f"   Context Window: {args.context_window:,} tokens")
        print(f"   Recommended Threshold: {threshold_info['threshold']:,} tokens")
    else:
        print("❌ Error: Must use --interactive OR provide --model and --context-window")
        parser.print_help()
        return 1

    # Output JSON
    print("\n" + "=" * 60)
    print("JSON Output:")
    print(json.dumps(capabilities, indent=2))
    print("=" * 60)

    # Update working memory if requested
    if args.update_working_memory:
        system_root = Path(args.update_working_memory)
        if not system_root.exists():
            print(f"❌ Error: System root not found: {system_root}")
            return 1

        if update_working_memory(system_root, capabilities):
            print("\n✅ All done! LLM capabilities configured.")
        else:
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
