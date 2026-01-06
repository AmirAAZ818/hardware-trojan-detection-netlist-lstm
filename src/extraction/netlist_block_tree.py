"""
Netlist Block Tree Data Structures (Paper Algorithm 1)

This module provides tree-based data structures for netlist blocks
following Algorithm 1 from the paper exactly.

Key differences from previous implementation:
- Tree structure (not hierarchical levels)
- Stores pin-to-pin connections
- Recursive path building
"""

from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class PathNode:
    """
    Node in a netlist block path tree
    
    Corresponds to line 23 in Algorithm 1:
    L_p.push([v_c', v_p, v_p', v_c, ll])
    
    Attributes:
        next_cell: v_c' - The next cell in the path
        current_pin: v_p - Current pin we're at
        next_pin: v_p' - Pin we're going to
        current_cell: v_c - Current cell
        level: ll - Level in the tree (logic_level - cnt + 1)
    """
    next_cell: str
    current_pin: str
    next_pin: str
    current_cell: str
    level: int
    
    def __repr__(self):
        return f"PathNode({self.current_pin} -> {self.next_cell} -> {self.next_pin}, level={self.level})"


@dataclass
class NetlistBlockTree:
    """
    Tree-based netlist block (Algorithm 1 output)
    
    Structure:
    - center_cell: The component at the center
    - input_tree: List of PathNodes for input direction (recursive)
    - output_tree: List of PathNodes for output direction (recursive)
    
    This is the D_t structure from Algorithm 1
    """
    center_cell: str
    center_cell_type: str
    logic_level: int
    input_tree: List = field(default_factory=list)  # L_p for 'I' direction
    output_tree: List = field(default_factory=list)  # L_p for 'O' direction
    
    def __repr__(self):
        return (f"NetlistBlockTree({self.center_cell} ({self.center_cell_type}), "
                f"logic_level={self.logic_level}, "
                f"input_nodes={len(self.input_tree)}, "
                f"output_nodes={len(self.output_tree)})")


@dataclass
class FlattenedPath:
    """
    A flattened path from the tree structure (Algorithm 2, FLATTEN output)
    
    This is one complete path from input/output direction
    Length should be <= logic_level
    """
    nodes: List[PathNode] = field(default_factory=list)
    
    def __len__(self):
        return len(self.nodes)
    
    def __getitem__(self, idx):
        return self.nodes[idx]
    
    def __repr__(self):
        return f"FlattenedPath(length={len(self.nodes)})"


@dataclass
class PCPToken:
    """
    A single PCP token (one hop in the path)
    
    Format: [input_pin, cell_type, output_pin]
    Example: ['DIN', 'i1s3', 'Q']
    
    Corresponds to line 12 in Algorithm 2:
    PCP ← [net_a.v_p, net_a.v_c, net_b.v_p]
    """
    input_pin: str
    cell_type: str
    output_pin: str
    
    def to_string(self) -> str:
        """Convert to paper format: DIN_i1s3_Q"""
        return f"{self.input_pin}_{self.cell_type}_{self.output_pin}"
    
    def __repr__(self):
        return self.to_string()


@dataclass
class PCPTrace:
    """
    Complete PCP trace for one input-output path pair
    
    Structure: [input_path_tokens] + [center_token] + [output_path_tokens]
    Length: Should be exactly 2*logic_level + 1
    
    This is one L_pcps from Algorithm 2
    """
    center_cell: str
    center_cell_type: str
    tokens: List[PCPToken] = field(default_factory=list)
    logic_level: int = 4
    
    def __len__(self):
        return len(self.tokens)
    
    def to_string(self) -> str:
        """Convert trace to space-separated string"""
        return " ".join([token.to_string() for token in self.tokens])
    
    def get_statistics(self) -> Dict:
        """Get statistics about the trace"""
        return {
            'center_cell': self.center_cell,
            'center_cell_type': self.center_cell_type,
            'trace_length': len(self.tokens),
            'expected_length': 2 * self.logic_level + 1,
            'length_matches': len(self.tokens) == 2 * self.logic_level + 1,
        }
    
    def __repr__(self):
        return (f"PCPTrace({self.center_cell}, "
                f"length={len(self.tokens)}, "
                f"expected={2*self.logic_level + 1})")


def format_block_tree(tree: NetlistBlockTree, max_nodes: int = 10) -> str:
    """
    Format a netlist block tree for display
    
    Args:
        tree: NetlistBlockTree to format
        max_nodes: Maximum nodes to show per direction
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append(f"\nNetlist Block Tree: {tree.center_cell} ({tree.center_cell_type})")
    lines.append("=" * 70)
    lines.append(f"Logic Level: {tree.logic_level}")
    lines.append("")
    
    # Input tree
    lines.append("INPUT TREE (Backward Direction):")
    lines.append("-" * 70)
    if tree.input_tree:
        for i, node in enumerate(tree.input_tree[:max_nodes]):
            if isinstance(node, PathNode):
                lines.append(f"  [{i}] {node}")
        if len(tree.input_tree) > max_nodes:
            lines.append(f"  ... (+{len(tree.input_tree) - max_nodes} more nodes)")
    else:
        lines.append("  (empty)")
    
    lines.append("")
    
    # Output tree
    lines.append("OUTPUT TREE (Forward Direction):")
    lines.append("-" * 70)
    if tree.output_tree:
        for i, node in enumerate(tree.output_tree[:max_nodes]):
            if isinstance(node, PathNode):
                lines.append(f"  [{i}] {node}")
        if len(tree.output_tree) > max_nodes:
            lines.append(f"  ... (+{len(tree.output_tree) - max_nodes} more nodes)")
    else:
        lines.append("  (empty)")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)


def format_pcp_trace(trace: PCPTrace) -> str:
    """
    Format a PCP trace for display
    
    Args:
        trace: PCPTrace to format
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append(f"\nPCP Trace: {trace.center_cell} ({trace.center_cell_type})")
    lines.append("=" * 70)
    lines.append(f"Trace Length: {len(trace.tokens)} (expected: {2*trace.logic_level + 1})")
    
    if len(trace.tokens) == 2 * trace.logic_level + 1:
        lines.append("✓ Length is CORRECT")
    else:
        lines.append(f"✗ Length mismatch!")
    
    lines.append("")
    lines.append("Tokens:")
    lines.append("-" * 70)
    
    for i, token in enumerate(trace.tokens):
        marker = ""
        if i < trace.logic_level:
            marker = "[INPUT]"
        elif i == trace.logic_level:
            marker = "[CENTER]"
        else:
            marker = "[OUTPUT]"
        
        lines.append(f"  [{i:2d}] {marker:10s} {token.to_string()}")
    
    lines.append("")
    lines.append("Full trace string:")
    lines.append(trace.to_string())
    lines.append("=" * 70)
    
    return "\n".join(lines)