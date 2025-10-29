#!/usr/bin/env python3
"""
RAG-enhanced LLM agent wrapper for reflow workflows.

This integration layer automatically retrieves and injects relevant context
into LLM agent prompts at appropriate trigger points.

Usage:
    # As a library
    from rag_agent_wrapper import RAGAgentWrapper

    wrapper = RAGAgentWrapper(system_path="systems/my_system")
    enhanced_prompt = wrapper.wrap_user_query("How do I validate the architecture?")

    # As a command-line tool
    python3 rag_agent_wrapper.py <system_path> --query "your query" --output prompt.txt
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError

# Import RAG retrieval tool
try:
    from retrieve_rag_context import RAGContextRetriever
except ImportError:
    print("ERROR: retrieve_rag_context.py must be in the same directory")
    sys.exit(1)


class RAGAgentWrapper:
    """Wrapper that integrates RAG context retrieval with LLM agent prompts."""
    
    def __init__(self, system_path: str, config_path: str = None):
        self.system_path = Path(system_path).resolve()
        self.retriever = RAGContextRetriever(str(system_path), config_path)
        
        # Load context state
        self.context_state = self._load_context_state()
        
        # Operation counter for periodic refresh
        self.operations_since_refresh = 0
        self.last_refresh_time = datetime.now()
    
    def _load_context_state(self) -> Dict[str, Any]:
        """Load current workflow context state."""
        return self.retriever._load_current_context()
    
    def _should_trigger_refresh(self) -> bool:
        """Check if periodic refresh should be triggered."""
        config = self.retriever.config
        refresh_triggers = config['context_management']['refresh_triggers']
        
        # Check operation count
        if self.operations_since_refresh >= refresh_triggers['operation_count']:
            return True
        
        # Check time elapsed
        time_elapsed = (datetime.now() - self.last_refresh_time).total_seconds() / 60
        if time_elapsed >= refresh_triggers['time_minutes']:
            return True
        
        return False
    
    def _detect_trigger_type(self, user_input: str) -> str:
        """Detect which retrieval strategy should be triggered."""
        # Step transition keywords
        if any(keyword in user_input.lower() for keyword in ['next step', 'proceed', 'continue workflow', 'start step']):
            return 'on_step_start'
        
        # Tool execution keywords
        if any(keyword in user_input.lower() for keyword in ['run tool', 'execute', 'validate', 'generate', 'analyze']):
            return 'on_tool_execution'
        
        # Periodic refresh check
        if self._should_trigger_refresh():
            return 'periodic_refresh'
        
        # Default to user query
        return 'on_user_query'
    
    def wrap_user_query(self, user_query: str, explicit_strategy: str = None) -> str:
        """
        Wrap a user query with retrieved RAG context.
        
        Args:
            user_query: The user's question or command
            explicit_strategy: Optional explicit strategy name to use
            
        Returns:
            Enhanced prompt with injected context
        """
        # Detect degradation in user query (e.g., confusion signals)
        degradation_signals = self.retriever.detect_degradation(user_query)
        
        if degradation_signals:
            # Retrieve corrective context
            results = self.retriever.retrieve_for_degradation(degradation_signals)
            context_block = self.retriever.format_context_for_injection(results)
            
            enhanced_prompt = f"""
**CRITICAL CONTEXT REFRESH REQUIRED**

Degradation signals detected: {', '.join(degradation_signals)}

{context_block}

---

USER QUERY: {user_query}

**IMPORTANT**: Before responding, review the CRITICAL CONTEXT above and ensure your actions align with the mandatory requirements.
"""
            return enhanced_prompt
        
        # Normal retrieval flow
        strategy = explicit_strategy or self._detect_trigger_type(user_query)
        
        # Update context vars with user query
        context_vars = self.context_state.copy()
        context_vars['user_query_text'] = user_query
        
        # Retrieve context
        results = self.retriever.retrieve_by_strategy(strategy, context_vars)
        context_block = self.retriever.format_context_for_injection(results)
        
        # Increment operation counter
        self.operations_since_refresh += 1
        
        # Format enhanced prompt
        enhanced_prompt = f"""
{context_block}

---

USER QUERY: {user_query}

**REMINDER**: Follow the workflow instructions and behavioral rules specified in the MANDATORY CONTEXT above.
"""
        return enhanced_prompt
    
    def wrap_agent_response(self, agent_response: str) -> Dict[str, Any]:
        """
        Analyze agent response for degradation and provide feedback.
        
        Args:
            agent_response: The LLM agent's response
            
        Returns:
            Analysis results with degradation detection and recommended actions
        """
        # Detect degradation
        degradation_signals = self.retriever.detect_degradation(agent_response)
        
        analysis = {
            'response_valid': len(degradation_signals) == 0,
            'degradation_signals': degradation_signals,
            'timestamp': datetime.now().isoformat(),
            'operations_since_refresh': self.operations_since_refresh
        }
        
        if degradation_signals:
            # Get corrective context
            corrective_results = self.retriever.retrieve_for_degradation(degradation_signals)
            analysis['corrective_context'] = corrective_results
            analysis['recommendation'] = 'INJECT_CORRECTIVE_CONTEXT'
            analysis['severity'] = self._assess_severity(degradation_signals)
        else:
            analysis['recommendation'] = 'PROCEED'
            analysis['severity'] = 'NONE'
        
        # Check if refresh needed
        if self._should_trigger_refresh():
            analysis['refresh_required'] = True
            self.operations_since_refresh = 0
            self.last_refresh_time = datetime.now()
        
        return analysis
    
    def _assess_severity(self, signals: List[str]) -> str:
        """Assess severity of degradation signals."""
        degradation_config = self.retriever.config.get('degradation_detection', {})
        
        critical_count = 0
        for signal_config in degradation_config.get('signal_patterns', []):
            if signal_config['signal'] in signals:
                if signal_config.get('alert_level') == 'CRITICAL':
                    critical_count += 1
        
        if critical_count > 0:
            return 'CRITICAL'
        elif len(signals) > 2:
            return 'HIGH'
        elif len(signals) > 0:
            return 'MEDIUM'
        return 'LOW'
    
    def execute_validation_before_operation(self) -> Dict[str, Any]:
        """
        Execute validation checks before any operation.
        
        Returns validation checklist results.
        """
        context_state = self._load_context_state()
        
        validation_checks = self.retriever.config['context_management']['validation_before_every_operation']
        
        results = {
            'validation_time': datetime.now().isoformat(),
            'system_name': context_state['system_name'],
            'working_directory': context_state['working_directory'],
            'current_step': context_state['current_step'],
            'current_substep': context_state['current_substep'],
            'operations_since_refresh': self.operations_since_refresh,
            'checks_passed': [],
            'checks_failed': [],
            'overall_status': 'PASS'
        }
        
        # Check working directory
        expected_wd = str(self.system_path)
        if context_state['working_directory'] != expected_wd:
            results['checks_failed'].append({
                'check': 'working_directory_verification',
                'expected': expected_wd,
                'actual': context_state['working_directory'],
                'message': 'Working directory mismatch - system isolation breach'
            })
        else:
            results['checks_passed'].append('working_directory_verification')
        
        # Check operation count
        if self.operations_since_refresh > 4:
            results['checks_failed'].append({
                'check': 'operation_count',
                'value': self.operations_since_refresh,
                'message': 'Operations count exceeds limit - context refresh required'
            })
        else:
            results['checks_passed'].append('operation_count')
        
        # Check if context files exist
        required_files = ['working_memory.json', 'step_progress_tracker.json', 'current_focus.md']
        for filename in required_files:
            filepath = self.system_path / "context" / filename
            if not filepath.exists():
                results['checks_failed'].append({
                    'check': f'context_file_{filename}',
                    'message': f'Required context file missing: {filename}'
                })
            else:
                results['checks_passed'].append(f'context_file_{filename}')
        
        if results['checks_failed']:
            results['overall_status'] = 'FAIL'
        
        return results
    
    def force_context_refresh(self) -> Dict[str, Any]:
        """Force a full context refresh."""
        print("Forcing context refresh...")
        
        # Reload context state
        self.context_state = self._load_context_state()
        
        # Execute periodic refresh strategy
        results = self.retriever.retrieve_by_strategy('periodic_refresh', self.context_state)
        
        # Reset counters
        self.operations_since_refresh = 0
        self.last_refresh_time = datetime.now()
        
        refresh_summary = {
            'refresh_time': datetime.now().isoformat(),
            'context_state': self.context_state,
            'retrieved_context': results,
            'status': 'COMPLETE'
        }
        
        return refresh_summary
    
    def get_current_focus_context(self) -> str:
        """Get formatted current focus for LLM injection."""
        focus_file = self.system_path / "context" / "current_focus.md"
        if focus_file.exists():
            with open(focus_file, 'r') as f:
                return f.read()
        return "No current focus defined"


def main():
    parser = argparse.ArgumentParser(
        description="RAG-enhanced LLM agent wrapper"
    )
    parser.add_argument(
        'system_path',
        help="Path to system directory"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Wrap query command
    wrap_parser = subparsers.add_parser('wrap', help='Wrap a user query with RAG context')
    wrap_parser.add_argument('--query', required=True, help='User query to wrap')
    wrap_parser.add_argument('--strategy', help='Explicit retrieval strategy')
    wrap_parser.add_argument('--output', help='Output file for enhanced prompt')
    
    # Analyze response command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze agent response for degradation')
    analyze_parser.add_argument('--response', required=True, help='Agent response text or file')
    analyze_parser.add_argument('--output', help='Output file for analysis results')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Execute pre-operation validation')
    validate_parser.add_argument('--output', help='Output file for validation results')
    
    # Refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Force context refresh')
    refresh_parser.add_argument('--output', help='Output file for refresh summary')
    
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(args.system_path)
    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: System path does not exist: {args.system_path}")
        sys.exit(1)

    wrapper = RAGAgentWrapper(str(system_path))
    
    if args.command == 'wrap':
        enhanced_prompt = wrapper.wrap_user_query(args.query, args.strategy)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(enhanced_prompt)
            print(f"✓ Enhanced prompt saved to {args.output}")
        else:
            print(enhanced_prompt)
    
    elif args.command == 'analyze':
        # Load response from file if it's a path
        response_text = args.response
        if Path(args.response).exists():
            with open(args.response, 'r') as f:
                response_text = f.read()
        
        analysis = wrapper.wrap_agent_response(response_text)
        output = json.dumps(analysis, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✓ Analysis saved to {args.output}")
        else:
            print(output)
    
    elif args.command == 'validate':
        validation = wrapper.execute_validation_before_operation()
        output = json.dumps(validation, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✓ Validation results saved to {args.output}")
        else:
            print(output)
        
        if validation['overall_status'] == 'FAIL':
            print("\n⚠️  Validation FAILED - review checks_failed")
            sys.exit(1)
    
    elif args.command == 'refresh':
        refresh_summary = wrapper.force_context_refresh()
        output = json.dumps(refresh_summary, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✓ Refresh summary saved to {args.output}")
        else:
            print(output)


if __name__ == '__main__':
    main()
