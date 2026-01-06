"""
PCP Trace Generator - Algorithm 2 from Paper

This module implements Algorithm 2 exactly as shown in the paper:
"PCP feature trace extraction from netlist block"

Key features:
- FLATTEN procedure to convert tree to paths
- Cross product of input and output paths
- Generate pin-level tokens: [input_pin, cell_type, output_pin]
- Guarantee trace length = 2*logic_level + 1
"""

from typing import Dict, List, Optional
from src.graph.netlist_graph import PinLevelGraph
from src.extraction.netlist_block_tree import (
    NetlistBlockTree, PathNode, FlattenedPath, 
    PCPToken, PCPTrace
)


class PCPTraceGenerator:
    """
    Generate PCP traces from netlist block trees
    
    Implements Algorithm 2 from the paper
    """
    
    def __init__(self, graph: PinLevelGraph):
        """
        Initialize PCP trace generator
        
        Args:
            graph: Pin-level graph (for looking up cell types and pin info)
        """
        self.graph = graph
        self.traces = {}  # {component_name: List[PCPTrace]}
        self.all_traces = []  # Flat list of all traces
    
    def generate_all_traces(self, blocks: Dict[str, NetlistBlockTree],
                           verbose: bool = False) -> Dict[str, List[PCPTrace]]:
        """
        Generate PCP traces for all netlist block trees
        
        Implements Algorithm 2, lines 1-28
        
        Args:
            blocks: Dictionary of netlist block trees (D_nb)
            verbose: Print progress
            
        Returns:
            Dictionary mapping cell_name to List[PCPTrace]
        """
        if verbose:
            print(f"\nGenerating PCP traces from block trees...")
        
        total_blocks = len(blocks)
        
        # for each key, D_t pair in D_nb do (line 1)
        for i, (key, D_t) in enumerate(blocks.items()):
            traces = self.generate_traces_for_block(key, D_t)
            self.traces[key] = traces
            self.all_traces.extend(traces)
            
            if verbose and (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{total_blocks} blocks...")
        
        if verbose:
            print(f"✓ Generated {len(self.all_traces)} PCP traces from {total_blocks} blocks")
            avg_traces = len(self.all_traces) / total_blocks if total_blocks > 0 else 0
            print(f"  Average traces per component: {avg_traces:.2f}")
        
        return self.traces
    
    def generate_traces_for_block(self, key: str, D_t: NetlistBlockTree) -> List[PCPTrace]:
        """
        Generate PCP traces for a single block
        
        Implements Algorithm 2, lines 2-27
        
        Args:
            key: Component name
            D_t: Netlist block tree
            
        Returns:
            List of PCPTrace objects
        """
        # Init. List L_PI, L_PO for storing netlist paths on 2 sides (line 2)
        L_PI = []
        L_PO = []
        
        # Initialize List L_ft to store PCP feature traces (line 3)
        L_ft = []
        
        # L_PI ← FLATTEN(D_t['I']) (line 4)
        L_PI = self.flatten(D_t.input_tree, D_t.logic_level)
        
        # L_PO ← FLATTEN(D_t['O']) (line 5)
        L_PO = self.flatten(D_t.output_tree, D_t.logic_level)
        
        # If no paths, create a single trace with just the center
        if len(L_PI) == 0 and len(L_PO) == 0:
            # Just the center component (isolated node)
            trace = PCPTrace(
                center_cell=D_t.center_cell,
                center_cell_type=D_t.center_cell_type,
                logic_level=D_t.logic_level
            )
            # Single token for center
            center_token = self._create_center_token(D_t)
            trace.tokens.append(center_token)
            L_ft.append(trace)
            return L_ft
        
        # If no input paths, use empty path
        if len(L_PI) == 0:
            L_PI = [FlattenedPath(nodes=[])]
        
        # If no output paths, use empty path
        if len(L_PO) == 0:
            L_PO = [FlattenedPath(nodes=[])]
        
        # for each path_I in L_PI do (line 6)
        for path_I in L_PI:
            # for each path_O in L_PO do (line 7)
            for path_O in L_PO:
                # Initialize List L_pcps to store PCP feature trace (line 8)
                L_pcps = []
                
                # Generate input path tokens (lines 9-14)
                # CRITICAL: Limit to logic_level tokens maximum
                # for i = length of path_I − 1; i > 1; i − − do (line 9)
                tokens_added = 0
                for i in range(len(path_I) - 1, 0, -1):
                    # Stop if we've already added logic_level tokens
                    if tokens_added >= D_t.logic_level:
                        break
                    
                    # net_a ← path_I[i − 1] (line 10)
                    net_a = path_I[i - 1]
                    # net_b ← path_I[i] (line 11)
                    net_b = path_I[i]
                    
                    # PCP ← [net_a.v_p, net_a.v_c, net_b.v_p] (line 12)
                    PCP = self._create_pcp_token(net_a, net_b)
                    
                    # L_pcps.push(PCP) (line 13)
                    L_pcps.append(PCP)
                    tokens_added += 1
                
                # Generate center token (lines 15-18)
                if len(path_I) > 0 and len(path_O) > 0:
                    # net_a ← path_I[0] (line 15)
                    net_a = path_I[0]
                    # net_b ← path_O[0] (line 16)
                    net_b = path_O[0]
                    
                    # PCP_0 ← [net_a.v_p, net_a.v_c, net_b.v_p] (line 17)
                    PCP_0 = self._create_pcp_token(net_a, net_b)
                elif len(path_I) > 0:
                    # Only input path
                    net_a = path_I[0]
                    PCP_0 = self._create_token_from_node(net_a, is_center=True)
                elif len(path_O) > 0:
                    # Only output path
                    net_b = path_O[0]
                    PCP_0 = self._create_token_from_node(net_b, is_center=True)
                else:
                    # Just center
                    PCP_0 = self._create_center_token(D_t)
                
                # L_pcps.push(PCP_0) (line 18)
                L_pcps.append(PCP_0)
                
                # Generate output path tokens (lines 19-24)
                # CRITICAL: Limit to logic_level tokens maximum
                # for i = 1; i < length of path_O − 1; i + + do (line 19)
                tokens_added = 0
                for i in range(1, len(path_O)):
                    # Stop if we've already added logic_level tokens
                    if tokens_added >= D_t.logic_level:
                        break
                    
                    # net_a ← path_O[i − 1] (line 20)
                    net_a = path_O[i - 1]
                    # net_b ← path_O[i] (line 21)
                    net_b = path_O[i]
                    
                    # PCP ← [net_a.v_p, net_a.v_c, net_b.v_p] (line 22)
                    PCP = self._create_pcp_token(net_a, net_b)
                    
                    # L_pcps.push(PCP) (line 23)
                    L_pcps.append(PCP)
                    tokens_added += 1
                
                # Create PCPTrace object
                trace = PCPTrace(
                    center_cell=D_t.center_cell,
                    center_cell_type=D_t.center_cell_type,
                    tokens=L_pcps,
                    logic_level=D_t.logic_level
                )
                
                # D_ft[key] ← L_pcps (line 27)
                L_ft.append(trace)
        
        return L_ft
    
    def flatten(self, L: List, logic_level: int) -> List[FlattenedPath]:
        """
        FLATTEN procedure from Algorithm 2 (lines 30-46)
        
        Converts tree structure to list of paths
        
        Args:
            L: List of PathNodes (tree structure)
            logic_level: Maximum path length (depth limit)
            
        Returns:
            List of FlattenedPath objects
        """
        # Initialize List L_S as stack for unfolding tree (line 31)
        L_S = []  # Stack
        
        # Initialize List L_P to store lists of nets (netlist paths) (line 32)
        L_P = []  # Paths
        
        # for each net in L do (line 33)
        for net in L:
            # Skip if not a PathNode (might be nested list from recursion)
            if not isinstance(net, PathNode):
                continue
            
            # if L_S is not empty ∧ L_S.top.ll > net.ll then (line 34)
            if len(L_S) > 0 and L_S[-1].level > net.level:
                # L_P.push(L_S) (line 35)
                # CRITICAL FIX: Trim path to logic_level before adding
                path_nodes = list(L_S)
                if len(path_nodes) > logic_level:
                    path_nodes = path_nodes[:logic_level]
                L_P.append(FlattenedPath(nodes=path_nodes))
                
                # repeat (line 36-38)
                while True:
                    # L_S.pop (line 37)
                    if len(L_S) > 0:
                        L_S.pop()
                    
                    # until L_S is empty ∨ L_S.top.ll < net.ll (line 38)
                    if len(L_S) == 0 or L_S[-1].level < net.level:
                        break
            # else (line 39)
            else:
                # L_S.push(net) (line 40)
                L_S.append(net)
        
        # if L_S is not empty then (line 43)
        if len(L_S) > 0:
            # L_P.push(L_S) (line 44)
            # CRITICAL FIX: Trim path to logic_level before adding
            path_nodes = list(L_S)
            if len(path_nodes) > logic_level:
                path_nodes = path_nodes[:logic_level]
            L_P.append(FlattenedPath(nodes=path_nodes))
        
        # return L_P (line 46)
        return L_P
    
    def _create_pcp_token(self, net_a: PathNode, net_b: PathNode) -> PCPToken:
        """
        Create a PCP token from two connected path nodes
        
        Format: [net_a.v_p, net_a.v_c, net_b.v_p]
        
        Args:
            net_a: First path node
            net_b: Second path node
            
        Returns:
            PCPToken object
        """
        # Extract pin names (remove cell prefix)
        input_pin = self._extract_pin_name(net_a.current_pin)
        output_pin = self._extract_pin_name(net_b.current_pin)
        
        # Get cell type from next_cell
        cell_vertex = self.graph.get_vertex(net_a.next_cell)
        cell_type = cell_vertex.cell_type if cell_vertex else net_a.next_cell
        
        return PCPToken(
            input_pin=input_pin,
            cell_type=cell_type,
            output_pin=output_pin
        )
    
    def _create_token_from_node(self, node: PathNode, is_center: bool = False) -> PCPToken:
        """Create a PCP token from a single node"""
        input_pin = self._extract_pin_name(node.current_pin)
        output_pin = self._extract_pin_name(node.next_pin)
        
        cell_vertex = self.graph.get_vertex(node.current_cell if is_center else node.next_cell)
        cell_type = cell_vertex.cell_type if cell_vertex else node.current_cell
        
        return PCPToken(
            input_pin=input_pin,
            cell_type=cell_type,
            output_pin=output_pin
        )
    
    def _create_center_token(self, block: NetlistBlockTree) -> PCPToken:
        """Create a PCP token for just the center component"""
        cell_vertex = self.graph.get_vertex(block.center_cell)
        
        # Get first input and output pins if available
        input_pins = self.graph.get_cell_input_pins(block.center_cell)
        output_pins = self.graph.get_cell_output_pins(block.center_cell)
        
        input_pin = self._extract_pin_name(input_pins[0].name) if input_pins else "IN"
        output_pin = self._extract_pin_name(output_pins[0].name) if output_pins else "OUT"
        
        return PCPToken(
            input_pin=input_pin,
            cell_type=block.center_cell_type,
            output_pin=output_pin
        )
    
    def _extract_pin_name(self, full_pin_name: str) -> str:
        """
        Extract pin name from full pin identifier
        
        Example: "U2.DIN1" -> "DIN1"
        """
        if '.' in full_pin_name:
            return full_pin_name.split('.')[-1]
        return full_pin_name
    
    def get_statistics(self) -> Dict:
        """Get statistics about generated traces"""
        if not self.all_traces:
            return {}
        
        trace_lengths = [len(trace) for trace in self.all_traces]
        expected_lengths = [2 * trace.logic_level + 1 for trace in self.all_traces]
        correct_lengths = sum(1 for trace in self.all_traces 
                             if len(trace) == 2 * trace.logic_level + 1)
        
        return {
            'num_components': len(self.traces),
            'num_traces': len(self.all_traces),
            'avg_traces_per_component': len(self.all_traces) / len(self.traces) if self.traces else 0,
            'avg_trace_length': sum(trace_lengths) / len(trace_lengths),
            'expected_trace_length': 2 * self.all_traces[0].logic_level + 1 if self.all_traces else 0,
            'min_trace_length': min(trace_lengths) if trace_lengths else 0,
            'max_trace_length': max(trace_lengths) if trace_lengths else 0,
            'traces_with_correct_length': correct_lengths,
            'percentage_correct_length': (correct_lengths / len(self.all_traces) * 100) if self.all_traces else 0,
        }
    
    def save_traces_for_training(self, output_path: str):
        """
        Save traces in format for skip-gram training
        
        One trace per line, space-separated tokens
        
        Args:
            output_path: Path to output file
        """
        with open(output_path, 'w') as f:
            for trace in self.all_traces:
                f.write(trace.to_string() + '\n')
        
        print(f"✓ Traces saved for training: {output_path}")


def generate_pcp_traces_from_blocks(blocks: Dict[str, NetlistBlockTree],
                                    graph: PinLevelGraph,
                                    verbose: bool = False) -> Dict[str, List[PCPTrace]]:
    """
    Convenience function to generate PCP traces from block trees
    
    Args:
        blocks: Dictionary of netlist block trees
        graph: Pin-level graph
        verbose: Print progress
        
    Returns:
        Dictionary mapping cell_name to List[PCPTrace]
    """
    generator = PCPTraceGenerator(graph)
    return generator.generate_all_traces(blocks, verbose=verbose)