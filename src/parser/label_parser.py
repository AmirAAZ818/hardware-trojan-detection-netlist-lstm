"""
Label Parser - Extracts Trojan component information from Trust-Hub log files
"""

import re
from typing import Dict, List, Set


class LabelParser:
    """Parser for Trust-Hub Trojan log files"""
    
    def __init__(self):
        # Per-file state (resets each parse)
        self.trojan_components = set()
        self.trojan_type = None
        self.affected_signals = []
        self.trigger_signals = []
        
        # Accumulative statistics (persists across files)
        self.total_files_processed = 0
        self.total_trojan_components = 0
        self.total_affected_signals = 0
        self.total_trigger_signals = 0
    
    def parse(self, log_path: str) -> Dict:
        """
        Parse a Trust-Hub log file to extract Trojan information
        
        Args:
            log_path: Path to the log.txt file
            
        Returns:
            Dictionary containing Trojan information for THIS file only
        """
        # Reset per-file state
        self.trojan_components = set()
        self.trojan_type = None
        self.affected_signals = []
        self.trigger_signals = []
        
        with open(log_path, 'r') as f:
            content = f.read()
        
        # Extract Trojan information
        self._extract_trojan_type(content)
        self._extract_affected_signals(content)
        self._extract_trigger_signals(content)
        self._extract_trojan_components(content)
        
        # Update accumulative statistics
        self.total_files_processed += 1
        self.total_trojan_components += len(self.trojan_components)
        self.total_affected_signals += len(self.affected_signals)
        self.total_trigger_signals += len(self.trigger_signals)
        
        return {
            'trojan_components': list(self.trojan_components),
            'trojan_type': self.trojan_type,
            'affected_signals': self.affected_signals,
            'trigger_signals': self.trigger_signals,
            'num_trojans': len(self.trojan_components)
        }
    
    def _extract_trojan_type(self, content: str):
        """Extract the type of Trojan from log content"""
        type_match = re.search(r'Type:\s*(.+?)(?:\n|Effect:)', content, re.DOTALL)
        if type_match:
            self.trojan_type = type_match.group(1).strip()
    
    def _extract_affected_signals(self, content: str):
        """Extract signals that are affected/modified by the Trojan"""
        effect_match = re.search(r'Effect:.*?following signal\(s\)\.\.\.(.+?)(?:\n|Activation)', 
                                content, re.DOTALL)
        if effect_match:
            signals_text = effect_match.group(1).strip()
            self.affected_signals = [s.strip() for s in signals_text.split() if s.strip()]
    
    def _extract_trigger_signals(self, content: str):
        """Extract signals used in the Trojan trigger condition"""
        trigger_match = re.search(r'Activation Condition:.*?internal signals\.\.\.(.+?)(?:\n\*+|TROJAN BODY)', 
                                 content, re.DOTALL)
        if trigger_match:
            signals_text = trigger_match.group(1).strip()
            self.trigger_signals = [s.strip() for s in signals_text.split() if s.strip()]
    
    def _extract_trojan_components(self, content: str):
        """Extract Trojan component instance names from TROJAN BODY section"""
        trojan_body_match = re.search(r'TROJAN BODY:\s*\n(.+?)(?:\n-{30,}\s*$|\Z)', 
                                     content, re.DOTALL)
        
        if not trojan_body_match:
            return
        
        trojan_body = trojan_body_match.group(1)
        gate_pattern = r'(\w+)\s+(\w+)\s*\('
        
        for match in re.finditer(gate_pattern, trojan_body):
            instance_name = match.group(2)
            
            if instance_name.lower() not in ['input', 'output', 'wire', 'module', 'endmodule']:
                self.trojan_components.add(instance_name)
    
    def is_trojan_component(self, component_name: str) -> bool:
        """Check if a component is part of the Trojan circuit"""
        return component_name in self.trojan_components
    
    def get_statistics(self) -> Dict:
        """Get statistics about the current file"""
        return {
            'num_trojan_components': len(self.trojan_components),
            'num_affected_signals': len(self.affected_signals),
            'num_trigger_signals': len(self.trigger_signals),
            'trojan_type': self.trojan_type
        }
    
    def get_accumulative_statistics(self) -> Dict:
        """Get accumulative statistics across all processed files"""
        return {
            'total_files_processed': self.total_files_processed,
            'total_trojan_components': self.total_trojan_components,
            'total_affected_signals': self.total_affected_signals,
            'total_trigger_signals': self.total_trigger_signals,
            'avg_trojans_per_file': self.total_trojan_components / max(1, self.total_files_processed)
        }


def main():
    """Demo/test function"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python label_parser.py <log_file_path>")
        sys.exit(1)
    
    log_path = sys.argv[1]
    
    parser = LabelParser()
    labels = parser.parse(log_path)
    
    print("\n" + "="*60)
    print("TROJAN LABEL INFORMATION")
    print("="*60)
    print(f"\nTrojan Type: {labels['trojan_type']}")
    print(f"Number of Trojan Components: {labels['num_trojans']}")
    print(f"\nAffected Signals: {', '.join(labels['affected_signals'])}")
    print(f"\nTrigger Signals ({len(labels['trigger_signals'])}): ")
    print(f"  {', '.join(labels['trigger_signals'])}")
    
    print(f"\nTrojan Components ({labels['num_trojans']}):")
    for i, comp in enumerate(sorted(labels['trojan_components']), 1):
        print(f"  {i:2d}. {comp}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()