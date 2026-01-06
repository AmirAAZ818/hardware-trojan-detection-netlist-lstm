"""
Netlist Block Extractor - BFS-based block extraction (Step 3, Algorithm 1)

This module implements the BFS-based algorithm to extract netlist blocks
around each component. This is Algorithm 1 from the paper.

Key Algorithm:
1. For each component, extract a netlist block
2. Backward BFS from input pins (logic_level hops)
3. Forward BFS from output pins (logic_level hops)
4. Store nets accessed at each level hierarchically
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import deque

# ==========================================
# FIX: Use full path starting with src
# ==========================================
from src.graph.netlist_graph import PinLevelGraph, Vertex, VertexType
from src.extraction.netlist_block import NetlistBlock

# Alternatively, you could use a relative import for the sibling file:
# from .netlist_block import NetlistBlock


class BlockExtractor:
    """
    Extracts netlist blocks using BFS traversal 
    
    Implements Algorithm 1 from the paper:
    - Backward BFS from input pins
    - Forward BFS from output pins
    - Hierarchical storage by logic level
    """
    
    def __init__(self, graph: PinLevelGraph, logic_level: int = 4):
        """
        Initialize block extractor
        
        Args:
            graph: Pin-level graph to extract blocks from
            logic_level: Depth of BFS traversal (default: 4)
        """
        self.graph = graph
        self.logic_level = logic_level
        self.blocks = {}  # {cell_name: NetlistBlock}
    
    def extract_all_blocks(self, verbose: bool = False) -> Dict[str, NetlistBlock]:
        """
        Extract netlist blocks for all components
        
        Args:
            verbose: Print progress
            
        Returns:
            Dictionary mapping cell_name to NetlistBlock
        """
        if verbose:
            print(f"\nExtracting netlist blocks (logic_level={self.logic_level})...")
        
        total_cells = len(self.graph.cells)
        
        for i, (cell_name, cell_vertex) in enumerate(self.graph.cells.items()):
            block = self.extract_block(cell_name)
            self.blocks[cell_name] = block
            
            if verbose and (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{total_cells} components...")
        
        if verbose:
            print(f"✓ Extracted {len(self.blocks)} netlist blocks")
        
        return self.blocks
    
    def extract_block(self, cell_name: str) -> NetlistBlock:
        """
        Extract netlist block for a single component
        
        Args:
            cell_name: Name of the center cell
            
        Returns:
            NetlistBlock object
        """
        cell_vertex = self.graph.get_vertex(cell_name)
        if not cell_vertex:
            raise ValueError(f"Cell not found: {cell_name}")
        
        # Create netlist block
        block = NetlistBlock(
            center_cell=cell_name,
            center_cell_type=cell_vertex.cell_type,
            logic_level=self.logic_level
        )
        
        # Extract input side (backward BFS from each input pin)
        input_pins = self.graph.get_cell_input_pins(cell_name)
        for input_pin in input_pins:
            path = self._bfs_backward(input_pin.name, self.logic_level)
            block.input_side.append(path)
        
        # Extract output side (forward BFS from each output pin)
        output_pins = self.graph.get_cell_output_pins(cell_name)
        for output_pin in output_pins:
            path = self._bfs_forward(output_pin.name, self.logic_level)
            block.output_side.append(path)
        
        return block
    
    def _bfs_backward(self, start_pin: str, max_depth: int) -> List[List[str]]:
        """
        Perform backward BFS from a pin (traverse input side)
        
        Algorithm:
        1. Start from the pin
        2. Follow edges backward (reverse direction)
        3. Collect nets at each level
        4. Stop at max_depth
        
        Args:
            start_pin: Starting pin name
            max_depth: Maximum depth (logic_level)
            
        Returns:
            Hierarchical list: [[nets at level 0], [nets at level 1], ...]
        """
        # Initialize result structure
        nets_by_level = [[] for _ in range(max_depth + 1)]
        
        # BFS queue: (current_vertex, current_depth)
        queue = deque([(start_pin, 0)])
        visited = {start_pin}
        
        while queue:
            current, depth = queue.popleft()
            
            # Stop if we've reached max depth
            if depth > max_depth:
                continue
            
            current_vertex = self.graph.get_vertex(current)
            if not current_vertex:
                continue
            
            # If current vertex is a pin, record its net
            if current_vertex.type == VertexType.PIN and current_vertex.net:
                if depth <= max_depth:
                    nets_by_level[depth].append(current_vertex.net)
            
            # Get neighbors in backward direction
            neighbors = self.graph.get_neighbors(current, direction="backward")
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor_vertex = self.graph.get_vertex(neighbor)
                    
                    # Skip if neighbor is the parent cell (don't go back to center)
                    if neighbor_vertex and neighbor_vertex.type == VertexType.CELL:
                        if neighbor == current_vertex.parent_cell:
                            continue
                    
                    # Determine next depth
                    # Only increment depth when crossing to a different cell's pin
                    next_depth = depth
                    if neighbor_vertex and neighbor_vertex.type == VertexType.PIN:
                        # Check if this pin belongs to a different cell
                        if (current_vertex.type == VertexType.PIN and 
                            neighbor_vertex.parent_cell != current_vertex.parent_cell):
                            next_depth = depth + 1
                    
                    if next_depth <= max_depth:
                        queue.append((neighbor, next_depth))
        
        return nets_by_level
    
    def _bfs_forward(self, start_pin: str, max_depth: int) -> List[List[str]]:
        """
        Perform forward BFS from a pin (traverse output side)
        
        Algorithm:
        1. Start from the pin
        2. Follow edges forward
        3. Collect nets at each level
        4. Stop at max_depth
        
        Args:
            start_pin: Starting pin name
            max_depth: Maximum depth (logic_level)
            
        Returns:
            Hierarchical list: [[nets at level 0], [nets at level 1], ...]
        """
        # Initialize result structure
        nets_by_level = [[] for _ in range(max_depth + 1)]
        
        # BFS queue: (current_vertex, current_depth)
        queue = deque([(start_pin, 0)])
        visited = {start_pin}
        
        while queue:
            current, depth = queue.popleft()
            
            # Stop if we've reached max depth
            if depth > max_depth:
                continue
            
            current_vertex = self.graph.get_vertex(current)
            if not current_vertex:
                continue
            
            # If current vertex is a pin, record its net
            if current_vertex.type == VertexType.PIN and current_vertex.net:
                if depth <= max_depth:
                    nets_by_level[depth].append(current_vertex.net)
            
            # Get neighbors in forward direction
            neighbors = self.graph.get_neighbors(current, direction="forward")
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor_vertex = self.graph.get_vertex(neighbor)
                    
                    # Skip if neighbor is the parent cell (don't go back to center)
                    if neighbor_vertex and neighbor_vertex.type == VertexType.CELL:
                        if neighbor == current_vertex.parent_cell:
                            continue
                    
                    # Determine next depth
                    # Only increment depth when crossing to a different cell's pin
                    next_depth = depth
                    if neighbor_vertex and neighbor_vertex.type == VertexType.PIN:
                        # Check if this pin belongs to a different cell
                        if (current_vertex.type == VertexType.PIN and 
                            neighbor_vertex.parent_cell != current_vertex.parent_cell):
                            next_depth = depth + 1
                    
                    if next_depth <= max_depth:
                        queue.append((neighbor, next_depth))
        
        return nets_by_level
    
    def get_block(self, cell_name: str) -> Optional[NetlistBlock]:
        """Get extracted block for a specific cell"""
        return self.blocks.get(cell_name)
    
    def get_statistics(self) -> Dict:
        """Get statistics about extracted blocks"""
        if not self.blocks:
            return {}
        
        total_blocks = len(self.blocks)
        total_nets = sum(len(block.get_all_nets()) for block in self.blocks.values())
        avg_nets_per_block = total_nets / total_blocks if total_blocks > 0 else 0
        
        # Analyze input/output paths
        total_input_paths = sum(len(block.input_side) for block in self.blocks.values())
        total_output_paths = sum(len(block.output_side) for block in self.blocks.values())
        
        return {
            'num_blocks': total_blocks,
            'logic_level': self.logic_level,
            'total_nets_in_blocks': total_nets,
            'avg_nets_per_block': avg_nets_per_block,
            'total_input_paths': total_input_paths,
            'total_output_paths': total_output_paths,
            'avg_input_paths': total_input_paths / total_blocks if total_blocks > 0 else 0,
            'avg_output_paths': total_output_paths / total_blocks if total_blocks > 0 else 0,
        }


def extract_blocks_from_graph(graph: PinLevelGraph, logic_level: int = 4, 
                              verbose: bool = False) -> Dict[str, NetlistBlock]:
    """
    Convenience function to extract all netlist blocks from a graph
    
    Args:
        graph: Pin-level graph
        logic_level: BFS depth (default: 4)
        verbose: Print progress
        
    Returns:
        Dictionary mapping cell_name to NetlistBlock
    """
    extractor = BlockExtractor(graph, logic_level)
    return extractor.extract_all_blocks(verbose=verbose)