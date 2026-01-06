"""
PCP Trace Generator - Convert netlist blocks to PCP traces (Algorithm 2)

This module implements Algorithm 2 from the paper: converting hierarchical
netlist blocks into flat sequences of cell types for NLP processing.
"""

from typing import Dict, List, Set, Optional

from src.graph.netlist_graph import PinLevelGraph
from src.extraction.netlist_block import NetlistBlock
from src.traces.pcp_trace import PCPTrace, PCPVocabulary

# Alternatively, you could use relative imports:
# from ..graph.netlist_graph import PinLevelGraph
# from ..extraction.netlist_block import NetlistBlock
# from .pcp_trace import PCPTrace, PCPVocabulary


class TraceGenerator:
    """
    Generate PCP traces from netlist blocks
    
    Converts hierarchical netlist blocks into flat sequences of cell types
    that can be processed by skip-gram and other NLP techniques.
    """
    
    def __init__(self, graph: PinLevelGraph):
        """
        Initialize trace generator
        
        Args:
            graph: Pin-level graph (for looking up cell types from nets)
        """
        self.graph = graph
        self.traces = {}  # {cell_name: PCPTrace}
        self.vocabulary = PCPVocabulary()
    
    def generate_all_traces(self, blocks: Dict[str, NetlistBlock],
                           verbose: bool = False) -> Dict[str, PCPTrace]:
        """
        Generate PCP traces for all netlist blocks
        
        Args:
            blocks: Dictionary of netlist blocks
            verbose: Print progress
            
        Returns:
            Dictionary mapping cell_name to PCPTrace
        """
        if verbose:
            print(f"\nGenerating PCP traces...")
        
        total_blocks = len(blocks)
        
        for i, (cell_name, block) in enumerate(blocks.items()):
            trace = self.generate_trace(block)
            self.traces[cell_name] = trace
            
            if verbose and (i + 1) % 500 == 0:
                print(f"  Processed {i + 1}/{total_blocks} blocks...")
        
        if verbose:
            print(f"✓ Generated {len(self.traces)} PCP traces")
        
        # Build vocabulary
        if verbose:
            print(f"Building vocabulary...")
        
        self.vocabulary.build_from_traces(list(self.traces.values()))
        
        if verbose:
            vocab_stats = self.vocabulary.get_statistics()
            print(f"✓ Vocabulary: {vocab_stats['vocab_size']} unique cell types")
            print(f"  Total tokens: {vocab_stats['total_tokens']}")
        
        return self.traces
    
    def generate_trace(self, block: NetlistBlock) -> PCPTrace:
        """
        Generate PCP trace for a single netlist block
        
        Algorithm:
        1. For each input path, extract cell types along the path
        2. For each output path, extract cell types along the path
        3. Combine into full trace: [input traces] + [center] + [output traces]
        
        Args:
            block: NetlistBlock to convert
            
        Returns:
            PCPTrace object
        """
        trace = PCPTrace(
            center_cell=block.center_cell,
            center_type=block.center_cell_type
        )
        
        # Generate input traces (one per input pin)
        for pin_idx, path in enumerate(block.input_side):
            input_trace = self._generate_path_trace(path)
            trace.input_traces.append(input_trace)
        
        # Generate output traces (one per output pin)
        for pin_idx, path in enumerate(block.output_side):
            output_trace = self._generate_path_trace(path)
            trace.output_traces.append(output_trace)
        
        # Create full trace: flatten all input traces + center + flatten all output traces
        full_trace = []
        
        # Add input traces
        for input_trace in trace.input_traces:
            full_trace.extend(input_trace)
        
        # Add center cell type
        full_trace.append(block.center_cell_type)
        
        # Add output traces
        for output_trace in trace.output_traces:
            full_trace.extend(output_trace)
        
        trace.full_trace = full_trace
        
        return trace
    
    def _generate_path_trace(self, path: List[List[str]]) -> List[str]:
        """
        Generate trace for a single path (input or output)
        
        Converts: [[nets at level 0], [nets at level 1], ...] 
        Into: [cell_type1, cell_type2, ...]
        
        Args:
            path: Hierarchical path (list of nets at each level)
            
        Returns:
            List of cell types
        """
        trace = []
        
        for level_idx, nets in enumerate(path):
            for net in nets:
                # Get cell types connected to this net
                cell_types = self._get_cell_types_from_net(net)
                trace.extend(cell_types)
        
        return trace
    
    def _get_cell_types_from_net(self, net_name: str) -> List[str]:
        """
        Get cell types of components connected to a net
        
        Args:
            net_name: Name of the net
            
        Returns:
            List of cell types
        """
        cell_types = []
        
        # Get pins connected to this net
        pins = self.graph.get_pins_by_net(net_name)
        
        # Get parent cells of these pins
        parent_cells = set()
        for pin in pins:
            if pin.parent_cell:
                parent_cells.add(pin.parent_cell)
        
        # Get cell types
        for cell_name in parent_cells:
            cell_vertex = self.graph.get_vertex(cell_name)
            if cell_vertex and cell_vertex.cell_type:
                cell_types.append(cell_vertex.cell_type)
        
        return cell_types
    
    def get_trace(self, cell_name: str) -> Optional[PCPTrace]:
        """Get trace for a specific cell"""
        return self.traces.get(cell_name)
    
    def get_statistics(self) -> Dict:
        """Get statistics about generated traces"""
        if not self.traces:
            return {}
        
        trace_lengths = [len(trace.full_trace) for trace in self.traces.values()]
        
        return {
            'num_traces': len(self.traces),
            'vocab_size': self.vocabulary.vocab_size,
            'avg_trace_length': sum(trace_lengths) / len(trace_lengths),
            'min_trace_length': min(trace_lengths),
            'max_trace_length': max(trace_lengths),
            'total_tokens': sum(trace_lengths),
        }
    
    def save_traces_for_training(self, output_path: str):
        """
        Save traces in format suitable for skip-gram training
        
        One trace per line, space-separated cell types
        
        Args:
            output_path: Path to output file
        """
        with open(output_path, 'w') as f:
            for trace in self.traces.values():
                f.write(trace.get_trace_string() + '\n')
        
        print(f"✓ Traces saved for training: {output_path}")


def generate_traces_from_blocks(blocks: Dict[str, NetlistBlock],
                                graph: PinLevelGraph,
                                verbose: bool = False) -> Dict[str, PCPTrace]:
    """
    Convenience function to generate PCP traces from blocks
    
    Args:
        blocks: Dictionary of netlist blocks
        graph: Pin-level graph
        verbose: Print progress
        
    Returns:
        Dictionary mapping cell_name to PCPTrace
    """
    generator = TraceGenerator(graph)
    return generator.generate_all_traces(blocks, verbose=verbose)