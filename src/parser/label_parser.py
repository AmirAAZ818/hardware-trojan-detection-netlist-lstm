"""
Label Parser - Extracts Trojan component information from Trust-Hub log files

This module parses the log.txt files that accompany Trojan-infected netlists
to identify which components are part of the Trojan circuit.
"""

import re
from typing import Dict, List, Set


class LabelParser:
    """Parser for Trust-Hub Trojan log files"""
    
    def __init__(self):
        self.trojan_components = set()
        self.trojan_type = None
        self.affected_signals = []
        self.trigger_signals = []
    
    def parse(self, log_path: str) -> Dict:
        """
        Parse a Trust-Hub log file to extract Trojan information
        
        Args:
            log_path: Path to the log.txt file
            
        Returns:
            Dictionary containing:
                - trojan_components: Set of component instance names
                - trojan_type: Type of Trojan (e.g., "counter with 9 states")
                - affected_signals: List of signals modified by Trojan
                - trigger_signals: List of signals used in trigger condition
        """
        with open(log_path, 'r') as f:
            content = f.read()
        
        # Extract Trojan type
        self._extract_trojan_type(content)
        
        # Extract affected signals
        self._extract_affected_signals(content)
        
        # Extract trigger signals
        self._extract_trigger_signals(content)
        
        # Extract Trojan components from TROJAN BODY section
        self._extract_trojan_components(content)
        
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
            # Split by whitespace to get individual signal names
            self.affected_signals = [s.strip() for s in signals_text.split() if s.strip()]
    
    def _extract_trigger_signals(self, content: str):
        """Extract signals used in the Trojan trigger condition"""
        trigger_match = re.search(r'Activation Condition:.*?internal signals\.\.\.(.+?)(?:\n\*+|TROJAN BODY)', 
                                 content, re.DOTALL)
        if trigger_match:
            signals_text = trigger_match.group(1).strip()
            # Split by whitespace to get individual signal names
            self.trigger_signals = [s.strip() for s in signals_text.split() if s.strip()]
    
    def _extract_trojan_components(self, content: str):
        """
        Extract Trojan component instance names from TROJAN BODY section
        
        Parses gate instantiations like:
            nor2s1 trig122_0U1 ( .DIN1(trig122_0n1), ... );
            dffs2 troj36_0counter_reg_0_ ( .DIN(troj36_0n10), ... );
        """
        # Find the TROJAN BODY section - capture everything until the end or next major section
        # The TROJAN BODY section ends with a line of dashes followed by empty line or EOF
        trojan_body_match = re.search(r'TROJAN BODY:\s*\n(.+?)(?:\n-{30,}\s*$|\Z)', 
                                     content, re.DOTALL)
        
        if not trojan_body_match:
            print("Warning: Could not find TROJAN BODY section in log file")
            return
        
        trojan_body = trojan_body_match.group(1)
        
        # Parse gate instantiations
        # Pattern matches: <cell_type> <instance_name> ( ... );
        # Examples:
        #   nor2s1 trig122_0U1 ( .DIN1(n1), .Q(out) );
        #   dffs2 troj36_0counter_reg_0_ ( .DIN(n2), .CLK(CK), .Q(q) );
        
        gate_pattern = r'(\w+)\s+(\w+)\s*\('
        
        for match in re.finditer(gate_pattern, trojan_body):
            cell_type = match.group(1)
            instance_name = match.group(2)
            
            # Filter out common keywords that might be captured
            if instance_name.lower() not in ['input', 'output', 'wire', 'module', 'endmodule']:
                self.trojan_components.add(instance_name)
        
        print(f"Extracted {len(self.trojan_components)} Trojan components from log file")
    
    def is_trojan_component(self, component_name: str) -> bool:
        """
        Check if a component is part of the Trojan circuit
        
        Args:
            component_name: Instance name of the component
            
        Returns:
            True if component is a Trojan component, False otherwise
        """
        return component_name in self.trojan_components
    
    def get_statistics(self) -> Dict:
        """Get statistics about the parsed Trojan information"""
        return {
            'num_trojan_components': len(self.trojan_components),
            'num_affected_signals': len(self.affected_signals),
            'num_trigger_signals': len(self.trigger_signals),
            'trojan_type': self.trojan_type
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