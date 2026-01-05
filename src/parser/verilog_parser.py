"""
Verilog Parser - Parse gate-level Verilog netlists

This module parses gate-level Verilog netlists and extracts:
- Module definition and ports
- Component instances (gates)
- Net connections
- Inferred cell library (pin definitions)
"""

import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class VerilogParser:
    """Parser for gate-level Verilog netlists"""
    
    def __init__(self):
        self.module_name = None
        self.ports = []  # List of {name, direction}
        self.components = []  # List of {instance, cell_type, connections}
        self.wires = set()  # Set of wire names
        self.cell_library = {}  # {cell_type: {pin_name: direction}}
    
    def parse(self, netlist_path: str) -> Dict:
        """
        Parse a gate-level Verilog netlist
        
        Args:
            netlist_path: Path to the Verilog (.v) file
            
        Returns:
            Dictionary containing:
                - module_name: Name of the module
                - ports: List of port definitions
                - components: List of component instances
                - wires: Set of internal wire names
                - cell_library: Inferred cell library with pin definitions
        """
        print(f"Parsing netlist: {netlist_path}")
        
        with open(netlist_path, 'r') as f:
            content = f.read()
        
        # Remove comments
        content = self._remove_comments(content)
        
        # Parse module declaration
        self._parse_module_declaration(content)
        
        # Parse port declarations
        self._parse_port_declarations(content)
        
        # Parse wire declarations
        self._parse_wire_declarations(content)
        
        # Parse component instances (gates)
        self._parse_components(content)
        
        # Infer cell library from parsed components
        self._infer_cell_library()
        
        print(f"Parsed {len(self.components)} components, {len(self.cell_library)} cell types")
        
        return {
            'module_name': self.module_name,
            'ports': self.ports,
            'components': self.components,
            'wires': list(self.wires),
            'cell_library': self.cell_library
        }
    
    def _remove_comments(self, content: str) -> str:
        """Remove single-line (//) and multi-line (/* */) comments"""
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove single-line comments
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
        return content
    
    def _parse_module_declaration(self, content: str):
        """
        Parse module declaration
        Example: module test_circuit ( input1, input2, output1 );
        """
        module_match = re.search(r'module\s+(\w+)\s*\((.*?)\)\s*;', content, re.DOTALL)
        
        if not module_match:
            raise ValueError("Could not find module declaration")
        
        self.module_name = module_match.group(1)
        print(f"Module name: {self.module_name}")
    
    def _parse_port_declarations(self, content: str):
        """
        Parse input/output/inout port declarations
        Examples:
            input a, b, c;
            output [3:0] out;
            input wire clk;
        """
        # Pattern for input/output/inout declarations
        port_patterns = [
            r'(input|output|inout)\s+(?:wire\s+)?(?:\[\d+:\d+\]\s+)?(\w+(?:\s*,\s*\w+)*)\s*;',
        ]
        
        for pattern in port_patterns:
            for match in re.finditer(pattern, content):
                direction = match.group(1)
                port_list = match.group(2)
                
                # Split by comma to handle multiple ports in one declaration
                for port_name in port_list.split(','):
                    port_name = port_name.strip()
                    if port_name:
                        self.ports.append({
                            'name': port_name,
                            'direction': direction
                        })
        
        print(f"Found {len(self.ports)} ports")
    
    def _parse_wire_declarations(self, content: str):
        """
        Parse wire declarations
        Examples:
            wire n1, n2, n3;
            wire [7:0] bus;
        """
        wire_pattern = r'wire\s+(?:\[\d+:\d+\]\s+)?(\w+(?:\s*,\s*\w+)*)\s*;'
        
        for match in re.finditer(wire_pattern, content):
            wire_list = match.group(1)
            
            # Split by comma
            for wire_name in wire_list.split(','):
                wire_name = wire_name.strip()
                if wire_name:
                    self.wires.add(wire_name)
        
        print(f"Found {len(self.wires)} wire declarations")
    
    def _parse_components(self, content: str):
        """
        Parse component (gate) instantiations
        
        Examples:
            and2 U1 ( .A(a), .B(b), .Z(out) );
            nor2s1 trig_U1 ( .DIN1(n1), .DIN2(n2), .Q(n3) );
            dffs2 reg0 ( .DIN(d), .CLK(clk), .Q(q) );
        
        Pattern: <cell_type> <instance_name> ( <pin_connections> );
        """
        # Pattern to match gate instantiations with named port connections
        # Handles multi-line instantiations
        component_pattern = r'(\w+)\s+(\w+)\s*\((.*?)\)\s*;'
        
        for match in re.finditer(component_pattern, content, re.DOTALL):
            cell_type = match.group(1)
            instance_name = match.group(2)
            connections_str = match.group(3)
            
            # Skip module declaration and port declarations
            if cell_type.lower() in ['module', 'input', 'output', 'inout', 'wire', 'reg', 'endmodule']:
                continue
            
            # Parse pin connections
            connections = self._parse_pin_connections(connections_str)
            
            if connections:  # Only add if we found valid connections
                component = {
                    'instance': instance_name,
                    'cell_type': cell_type,
                    'connections': connections
                }
                self.components.append(component)
    
    def _parse_pin_connections(self, connections_str: str) -> Dict[str, str]:
        """
        Parse pin connections from the component instantiation
        
        Input: ".DIN1(n1), .DIN2(n2), .Q(out)"
        Output: {'DIN1': 'n1', 'DIN2': 'n2', 'Q': 'out'}
        """
        connections = {}
        
        # Pattern: .PIN_NAME(signal_name)
        pin_pattern = r'\.(\w+)\s*\(\s*(\w+)\s*\)'
        
        for match in re.finditer(pin_pattern, connections_str):
            pin_name = match.group(1)
            signal_name = match.group(2)
            connections[pin_name] = signal_name
        
        return connections
    
    def _infer_cell_library(self):
        """
        Infer cell library (pin definitions) from the parsed components
        
        For each cell type, determine which pins are inputs and which are outputs
        based on signal flow analysis
        """
        # Collect all pin names for each cell type
        cell_pins = defaultdict(set)
        
        for component in self.components:
            cell_type = component['cell_type']
            for pin_name in component['connections'].keys():
                cell_pins[cell_type].add(pin_name)
        
        # Build signal usage tracking
        signal_drivers = {}  # {signal: [(cell_instance, pin)]}
        signal_loads = defaultdict(list)  # {signal: [(cell_instance, pin)]}
        
        for component in self.components:
            instance = component['instance']
            for pin_name, signal in component['connections'].items():
                # We'll determine direction in next step
                if signal not in signal_drivers:
                    signal_drivers[signal] = []
                signal_drivers[signal].append((instance, pin_name))
                signal_loads[signal].append((instance, pin_name))
        
        # Infer pin directions for each cell type
        for cell_type in cell_pins:
            self.cell_library[cell_type] = {}
            
            # Collect evidence for each pin's direction
            pin_directions = defaultdict(lambda: {'input': 0, 'output': 0})
            
            for component in self.components:
                if component['cell_type'] != cell_type:
                    continue
                
                for pin_name, signal in component['connections'].items():
                    # Count how many times this signal is driven vs loaded
                    drivers = [p for i, p in signal_drivers.get(signal, []) if i == component['instance']]
                    loads = [p for i, p in signal_loads.get(signal, []) if i == component['instance']]
                    
                    # Heuristics for direction inference
                    # Common output pin names
                    if pin_name in ['Q', 'QN', 'Z', 'Y', 'OUT', 'O', 'S', 'CO', 'SUM']:
                        pin_directions[pin_name]['output'] += 10
                    
                    # Common input pin names
                    if pin_name in ['A', 'B', 'C', 'D', 'DIN', 'DIN1', 'DIN2', 'DIN3', 'DIN4', 
                                   'DIN5', 'CLK', 'CK', 'EN', 'EB', 'RST', 'SET', 'CI', 'S0', 'S1']:
                        pin_directions[pin_name]['input'] += 10
            
            # Assign directions based on accumulated evidence
            for pin_name in cell_pins[cell_type]:
                if pin_directions[pin_name]['output'] > pin_directions[pin_name]['input']:
                    self.cell_library[cell_type][pin_name] = 'output'
                else:
                    self.cell_library[cell_type][pin_name] = 'input'
    
    def get_component(self, instance_name: str) -> Dict:
        """Get a specific component by instance name"""
        for comp in self.components:
            if comp['instance'] == instance_name:
                return comp
        return None
    
    def get_cell_pins(self, cell_type: str) -> Dict[str, str]:
        """Get pin definitions for a cell type"""
        return self.cell_library.get(cell_type, {})
    
    def get_statistics(self) -> Dict:
        """Get statistics about the parsed netlist"""
        cell_type_counts = defaultdict(int)
        for comp in self.components:
            cell_type_counts[comp['cell_type']] += 1
        
        return {
            'module_name': self.module_name,
            'num_components': len(self.components),
            'num_ports': len(self.ports),
            'num_wires': len(self.wires),
            'num_cell_types': len(self.cell_library),
            'cell_type_distribution': dict(cell_type_counts)
        }


def main():
    """Demo/test function"""
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python verilog_parser.py <netlist_file>")
        sys.exit(1)
    
    netlist_path = sys.argv[1]
    
    parser = VerilogParser()
    netlist_data = parser.parse(netlist_path)
    
    stats = parser.get_statistics()
    
    print("\n" + "="*60)
    print("VERILOG NETLIST PARSING RESULTS")
    print("="*60)
    print(f"\nModule Name: {stats['module_name']}")
    print(f"Components: {stats['num_components']}")
    print(f"Ports: {stats['num_ports']}")
    print(f"Wires: {stats['num_wires']}")
    print(f"Cell Types: {stats['num_cell_types']}")
    
    print(f"\nCell Type Distribution (top 10):")
    sorted_cells = sorted(stats['cell_type_distribution'].items(), 
                         key=lambda x: x[1], reverse=True)
    for cell_type, count in sorted_cells[:10]:
        print(f"  {cell_type:20s}: {count:4d}")
    
    print(f"\nInferred Cell Library ({len(netlist_data['cell_library'])} cell types):")
    for cell_type in sorted(list(netlist_data['cell_library'].keys()))[:10]:
        pins = netlist_data['cell_library'][cell_type]
        pin_strs = [f"{name}({dir[0]})" for name, dir in pins.items()]
        print(f"  {cell_type:20s}: {', '.join(pin_strs)}")
    
    if len(netlist_data['cell_library']) > 10:
        print(f"  ... and {len(netlist_data['cell_library']) - 10} more")
    
    print(f"\nSample Components (first 5):")
    for i, comp in enumerate(netlist_data['components'][:5], 1):
        conn_str = ', '.join([f"{p}={s}" for p, s in comp['connections'].items()])
        print(f"  {i}. {comp['instance']} ({comp['cell_type']}): {conn_str}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()