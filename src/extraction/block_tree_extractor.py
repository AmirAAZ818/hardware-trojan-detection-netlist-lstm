"""
Netlist Block Tree Extractor - Algorithm 1 from Paper

This module implements Algorithm 1 exactly as shown in the paper:
"Netlist block extraction for components in netlist"

Key features:
- Recursive BFS with depth limit (logic_level)
- Creates tree structure of paths
- Stores pin-to-pin connections
"""

from typing import Dict, List, Set, Optional
from collections import deque

from src.graph.netlist_graph import PinLevelGraph, Vertex, VertexType
# Assuming netlist_block_tree.py is in src/extraction/
from src.extraction.netlist_block_tree import NetlistBlockTree, PathNode


class BlockTreeExtractor:
    """
    Extract netlist block trees using Algorithm 1 from paper
    
    Creates tree-based representation of local neighborhoods
    around each component using recursive BFS.
    """
    
    def __init__(self, graph: PinLevelGraph, logic_level: int = 4):
        """
        Initialize block tree extractor
        
        Args:
            graph: Pin-level graph to extract blocks from
            logic_level: Depth of recursive BFS (default: 4)
        """
        self.graph = graph
        self.logic_level = logic_level
        self.blocks = {}  # {cell_name: NetlistBlockTree}
    
    def extract_all_blocks(self, verbose: bool = False) -> Dict[str, NetlistBlockTree]:
        """
        Extract netlist block trees for all components
        
        Args:
            verbose: Print progress
            
        Returns:
            Dictionary mapping cell_name to NetlistBlockTree
        """
        if verbose:
            print(f"\nExtracting netlist block trees (logic_level={self.logic_level})...")
        
        total_cells = len(self.graph.cells)
        
        for i, (cell_name, cell_vertex) in enumerate(self.graph.cells.items()):
            block = self.extract_block(cell_name)
            self.blocks[cell_name] = block
            
            if verbose and (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{total_cells} components...")
        
        if verbose:
            print(f"✓ Extracted {len(self.blocks)} netlist block trees")
        
        return self.blocks
    
    def extract_block(self, cell_name: str) -> NetlistBlockTree:
        """
        Extract netlist block tree for a single component
        
        Implements Algorithm 1, lines 1-14
        
        Args:
            cell_name: Name of the center cell
            
        Returns:
            NetlistBlockTree object
        """
        cell_vertex = self.graph.get_vertex(cell_name)
        if not cell_vertex:
            raise ValueError(f"Cell not found: {cell_name}")
        
        # Initialize Dict D_t to store v_c's netlist block tree (line 3)
        block = NetlistBlockTree(
            center_cell=cell_name,
            center_cell_type=cell_vertex.cell_type,
            logic_level=self.logic_level
        )
        
        # cnt ← logic_level (line 4)
        cnt = self.logic_level
        
        # if indegree(v_c) > 0 then (line 5)
        input_pins = self.graph.get_cell_input_pins(cell_name)
        if len(input_pins) > 0:
            # D_t['I'] ← RECURSION(v_c, cnt, 'I') (line 6)
            block.input_tree = self.recursion(cell_name, cnt, 'I')
        
        # if outdegree(v_c) > 0 then (line 8)
        output_pins = self.graph.get_cell_output_pins(cell_name)
        if len(output_pins) > 0:
            # D_t['O'] ← RECURSION(v_c, cnt, 'O') (line 9)
            block.output_tree = self.recursion(cell_name, cnt, 'O')
        
        # key ← Instance Name of v_c (line 11)
        # D_nb[key] ← D_t (line 12)
        # (We return the block instead of storing in dict here)
        
        return block
    
    def recursion(self, v_c: str, cnt: int, direction: str) -> List:
        """
        Recursive BFS procedure from Algorithm 1 (lines 15-38)
        
        Args:
            v_c: Current cell name
            cnt: Remaining depth (starts at logic_level, decrements)
            direction: 'I' for input (backward) or 'O' for output (forward)
            
        Returns:
            List L_p of PathNodes (tree structure)
        """
        # Initialize List L_p to store the accessed nets (line 16)
        L_p = []
        
        # if cnt > 0 then (line 17)
        if cnt > 0:
            # ll ← (logic_level − cnt) + 1 (line 18)
            ll = (self.logic_level - cnt) + 1
            
            # if Direction = 'I' then (line 19)
            if direction == 'I':
                # Get input pins of current cell
                input_pins = self.graph.get_cell_input_pins(v_c)
                
                # for each v_p in {v | (v, v_c) ∈ E} do (line 20)
                for v_p in input_pins:
                    # for each v'_p in {v | (v, v_p) ∈ E} do (line 21)
                    # Get pins that connect TO this input pin (backward)
                    backward_neighbors = self.graph.get_neighbors(v_p.name, direction="backward")
                    
                    for neighbor_name in backward_neighbors:
                        neighbor = self.graph.get_vertex(neighbor_name)
                        
                        # Skip if not a pin
                        if not neighbor or neighbor.type != VertexType.PIN:
                            continue
                        
                        # v'_c ← parent(v'_p) (line 22)
                        v_c_prime = neighbor.parent_cell
                        
                        # Skip if no parent cell
                        if not v_c_prime:
                            continue
                        
                        # Get cell vertex
                        v_c_prime_vertex = self.graph.get_vertex(v_c_prime)
                        if not v_c_prime_vertex or v_c_prime_vertex.type != VertexType.CELL:
                            continue
                        
                        # L_p.push([v'_c, v_p, v'_p, v_c, ll]) (line 23)
                        node = PathNode(
                            next_cell=v_c_prime,
                            current_pin=v_p.name,
                            next_pin=neighbor.name,
                            current_cell=v_c,
                            level=ll
                        )
                        L_p.append(node)
                        
                        # L_p.push(RECURSION(v'_c, cnt − 1, 'I')) (line 24)
                        recursive_result = self.recursion(v_c_prime, cnt - 1, 'I')
                        L_p.extend(recursive_result)
            
            # else if Direction = 'O' then (line 27)
            elif direction == 'O':
                # Get output pins of current cell
                output_pins = self.graph.get_cell_output_pins(v_c)
                
                # for each v_p in {v | (v_c, v) ∈ E} do (line 28)
                for v_p in output_pins:
                    # for each v'_p in {v | (v_p, v) ∈ E} do (line 29)
                    # Get pins that this output pin connects TO (forward)
                    forward_neighbors = self.graph.get_neighbors(v_p.name, direction="forward")
                    
                    for neighbor_name in forward_neighbors:
                        neighbor = self.graph.get_vertex(neighbor_name)
                        
                        # Skip if not a pin
                        if not neighbor or neighbor.type != VertexType.PIN:
                            continue
                        
                        # v'_c ← child(v'_p) (line 30)
                        v_c_prime = neighbor.parent_cell
                        
                        # Skip if no parent cell
                        if not v_c_prime:
                            continue
                        
                        # Get cell vertex
                        v_c_prime_vertex = self.graph.get_vertex(v_c_prime)
                        if not v_c_prime_vertex or v_c_prime_vertex.type != VertexType.CELL:
                            continue
                        
                        # L_p.push([v'_c, v_p, v'_p, v_c, ll]) (line 31)
                        node = PathNode(
                            next_cell=v_c_prime,
                            current_pin=v_p.name,
                            next_pin=neighbor.name,
                            current_cell=v_c,
                            level=ll
                        )
                        L_p.append(node)
                        
                        # L_p.push(RECURSION(v'_c, cnt − 1, 'O')) (line 32)
                        recursive_result = self.recursion(v_c_prime, cnt - 1, 'O')
                        L_p.extend(recursive_result)
        
        # return L_p (line 37)
        return L_p
    
    def get_block(self, cell_name: str) -> Optional[NetlistBlockTree]:
        """Get extracted block tree for a specific cell"""
        return self.blocks.get(cell_name)
    
    def get_statistics(self) -> Dict:
        """Get statistics about extracted block trees"""
        if not self.blocks:
            return {}
        
        total_blocks = len(self.blocks)
        total_input_nodes = sum(len(b.input_tree) for b in self.blocks.values())
        total_output_nodes = sum(len(b.output_tree) for b in self.blocks.values())
        
        return {
            'num_blocks': total_blocks,
            'logic_level': self.logic_level,
            'total_input_nodes': total_input_nodes,
            'total_output_nodes': total_output_nodes,
            'avg_input_nodes': total_input_nodes / total_blocks if total_blocks > 0 else 0,
            'avg_output_nodes': total_output_nodes / total_blocks if total_blocks > 0 else 0,
        }


def extract_block_trees_from_graph(graph: PinLevelGraph, logic_level: int = 4, 
                                   verbose: bool = False) -> Dict[str, NetlistBlockTree]:
    """
    Convenience function to extract all netlist block trees from a graph
    
    Args:
        graph: Pin-level graph
        logic_level: BFS depth (default: 4)
        verbose: Print progress
        
    Returns:
        Dictionary mapping cell_name to NetlistBlockTree
    """
    extractor = BlockTreeExtractor(graph, logic_level)
    return extractor.extract_all_blocks(verbose=verbose)