"""
Netlist Block Data Structures (Step 3)

This module provides the data structure for representing netlist blocks -
local neighborhoods around components extracted via BFS.

Key Concepts:
- Netlist Block: Local topology around a center component
- Hierarchical structure: Organized by logic level (depth)
- Input side: Backward BFS from input pins
- Output side: Forward BFS from output pins
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field


@dataclass
class NetlistBlock:
    """
    Represents a netlist block - local neighborhood around a component
    
    Structure:
    - center_cell: The component at the center
    - input_side: List of hierarchical paths from input pins (backward BFS)
    - output_side: List of hierarchical paths from output pins (forward BFS)
    
    Each path is organized by logic level (depth in BFS):
    - Level 0: Nets directly connected to center cell pins
    - Level 1: Nets one hop away
    - Level 2: Nets two hops away
    - ...
    - Level N: Nets N hops away (N = logic_level)
    
    Example for logic_level=2:
    
    Input side (backward from input pin DIN1):
      Level 0: [net1]
      Level 1: [net2, net3]
      Level 2: [net4]
    
    Output side (forward from output pin Q):
      Level 0: [net5]
      Level 1: [net6, net7]
      Level 2: [net8, net9]
    """
    
    center_cell: str
    center_cell_type: str
    input_side: List[List[List[str]]] = field(default_factory=list)
    output_side: List[List[List[str]]] = field(default_factory=list)
    logic_level: int = 4
    
    def __repr__(self):
        num_input_paths = len(self.input_side)
        num_output_paths = len(self.output_side)
        return (f"NetlistBlock({self.center_cell} ({self.center_cell_type}), "
                f"logic_level={self.logic_level}, "
                f"input_paths={num_input_paths}, "
                f"output_paths={num_output_paths})")
    
    def get_input_path(self, pin_index: int) -> List[List[str]]:
        """
        Get the hierarchical path for a specific input pin
        
        Args:
            pin_index: Index of the input pin (0, 1, 2, ...)
            
        Returns:
            Hierarchical path: [[nets at level 0], [nets at level 1], ...]
        """
        if pin_index < len(self.input_side):
            return self.input_side[pin_index]
        return []
    
    def get_output_path(self, pin_index: int) -> List[List[str]]:
        """
        Get the hierarchical path for a specific output pin
        
        Args:
            pin_index: Index of the output pin (0, 1, 2, ...)
            
        Returns:
            Hierarchical path: [[nets at level 0], [nets at level 1], ...]
        """
        if pin_index < len(self.output_side):
            return self.output_side[pin_index]
        return []
    
    def get_all_nets(self) -> Set[str]:
        """
        Get all unique nets in the block
        
        Returns:
            Set of net names
        """
        all_nets = set()
        
        # Collect from input side
        for path in self.input_side:
            for level_nets in path:
                all_nets.update(level_nets)
        
        # Collect from output side
        for path in self.output_side:
            for level_nets in path:
                all_nets.update(level_nets)
        
        return all_nets
    
    def get_statistics(self) -> Dict:
        """Get statistics about the netlist block"""
        return {
            'center_cell': self.center_cell,
            'center_cell_type': self.center_cell_type,
            'logic_level': self.logic_level,
            'num_input_pins': len(self.input_side),
            'num_output_pins': len(self.output_side),
            'total_nets': len(self.get_all_nets()),
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'center_cell': self.center_cell,
            'center_cell_type': self.center_cell_type,
            'logic_level': self.logic_level,
            'input_side': self.input_side,
            'output_side': self.output_side,
            'statistics': self.get_statistics(),
        }


def format_netlist_block(block: NetlistBlock, max_nets_per_level: int = 5) -> str:
    """
    Format a netlist block for display
    
    Args:
        block: NetlistBlock to format
        max_nets_per_level: Maximum nets to show per level
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append(f"\nNetlist Block: {block.center_cell} ({block.center_cell_type})")
    lines.append("=" * 60)
    lines.append(f"Logic Level: {block.logic_level}")
    lines.append(f"Input Pins: {len(block.input_side)}, Output Pins: {len(block.output_side)}")
    lines.append("")
    
    # Input side
    lines.append("INPUT SIDE (Backward BFS):")
    lines.append("-" * 60)
    for i, path in enumerate(block.input_side):
        lines.append(f"  Input Pin {i}:")
        for level, nets in enumerate(path):
            nets_to_show = nets[:max_nets_per_level]
            more = len(nets) - max_nets_per_level
            nets_str = ", ".join(nets_to_show)
            if more > 0:
                nets_str += f" ... (+{more} more)"
            lines.append(f"    Level {level}: [{nets_str}]")
    
    lines.append("")
    
    # Output side
    lines.append("OUTPUT SIDE (Forward BFS):")
    lines.append("-" * 60)
    for i, path in enumerate(block.output_side):
        lines.append(f"  Output Pin {i}:")
        for level, nets in enumerate(path):
            nets_to_show = nets[:max_nets_per_level]
            more = len(nets) - max_nets_per_level
            nets_str = ", ".join(nets_to_show)
            if more > 0:
                nets_str += f" ... (+{more} more)"
            lines.append(f"    Level {level}: [{nets_str}]")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)