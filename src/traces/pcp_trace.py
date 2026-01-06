"""
PCP Trace Generation (Step 4, Algorithm 2)

PCP = Primary Cell and Primary Cell's Primary Inputs

This module flattens netlist blocks into sequences of cell types that can
be processed by NLP techniques (skip-gram in Step 5).

Key Concept:
- Netlist Block (hierarchical) → PCP Trace (flat sequence)
- Sequence contains cell types along paths
- Used as "sentences" for skip-gram training
"""

from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class PCPTrace:
    """
    PCP Trace for a component
    
    A PCP trace is a flat sequence of cell types extracted from the
    netlist block. This serves as a "sentence" for skip-gram training.
    
    Structure:
    - center_cell: The component name
    - center_type: The cell type of the center component
    - input_traces: List of traces from input side
    - output_traces: List of traces from output side
    - full_trace: Flattened sequence of all cell types
    """
    
    center_cell: str
    center_type: str
    input_traces: List[List[str]] = field(default_factory=list)
    output_traces: List[List[str]] = field(default_factory=list)
    full_trace: List[str] = field(default_factory=list)
    
    def __repr__(self):
        return (f"PCPTrace({self.center_cell} ({self.center_type}), "
                f"len={len(self.full_trace)})")
    
    def get_trace_string(self) -> str:
        """Get the full trace as a space-separated string"""
        return " ".join(self.full_trace)
    
    def get_statistics(self) -> Dict:
        """Get statistics about the trace"""
        return {
            'center_cell': self.center_cell,
            'center_type': self.center_type,
            'trace_length': len(self.full_trace),
            'num_input_traces': len(self.input_traces),
            'num_output_traces': len(self.output_traces),
            'unique_cell_types': len(set(self.full_trace)),
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'center_cell': self.center_cell,
            'center_type': self.center_type,
            'input_traces': self.input_traces,
            'output_traces': self.output_traces,
            'full_trace': self.full_trace,
            'statistics': self.get_statistics(),
        }


class PCPVocabulary:
    """
    Vocabulary of cell types for PCP traces
    
    Maps cell types to integer indices for neural network processing
    """
    
    def __init__(self):
        self.word2idx = {}  # {cell_type: index}
        self.idx2word = {}  # {index: cell_type}
        self.word_counts = Counter()  # {cell_type: count}
        self.vocab_size = 0
    
    def build_from_traces(self, traces: List[PCPTrace]):
        """
        Build vocabulary from PCP traces
        
        Args:
            traces: List of PCP traces
        """
        # Count cell types
        for trace in traces:
            self.word_counts.update(trace.full_trace)
        
        # Create mappings (sorted by frequency for consistency)
        sorted_words = sorted(self.word_counts.items(), 
                            key=lambda x: (-x[1], x[0]))  # By count desc, then alphabetically
        
        for idx, (word, count) in enumerate(sorted_words):
            self.word2idx[word] = idx
            self.idx2word[idx] = word
        
        self.vocab_size = len(self.word2idx)
    
    def encode_trace(self, trace: PCPTrace) -> List[int]:
        """
        Encode a trace to integer indices
        
        Args:
            trace: PCPTrace to encode
            
        Returns:
            List of integer indices
        """
        return [self.word2idx.get(cell_type, -1) for cell_type in trace.full_trace]
    
    def decode_trace(self, indices: List[int]) -> List[str]:
        """
        Decode integer indices back to cell types
        
        Args:
            indices: List of integer indices
            
        Returns:
            List of cell type strings
        """
        return [self.idx2word.get(idx, '<UNK>') for idx in indices]
    
    def get_statistics(self) -> Dict:
        """Get vocabulary statistics"""
        return {
            'vocab_size': self.vocab_size,
            'total_tokens': sum(self.word_counts.values()),
            'most_common': self.word_counts.most_common(10),
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'word2idx': self.word2idx,
            'idx2word': {str(k): v for k, v in self.idx2word.items()},
            'word_counts': dict(self.word_counts),
            'vocab_size': self.vocab_size,
            'statistics': self.get_statistics(),
        }


def format_pcp_trace(trace: PCPTrace, max_length: int = 50) -> str:
    """
    Format a PCP trace for display
    
    Args:
        trace: PCPTrace to format
        max_length: Maximum tokens to show
        
    Returns:
        Formatted string
    """
    lines = []
    lines.append(f"\nPCP Trace: {trace.center_cell} ({trace.center_type})")
    lines.append("=" * 60)
    
    # Input traces
    lines.append("INPUT TRACES:")
    for i, input_trace in enumerate(trace.input_traces):
        trace_str = " → ".join(input_trace[:max_length])
        if len(input_trace) > max_length:
            trace_str += f" ... (+{len(input_trace) - max_length} more)"
        lines.append(f"  Input {i}: {trace_str}")
    
    # Output traces
    lines.append("\nOUTPUT TRACES:")
    for i, output_trace in enumerate(trace.output_traces):
        trace_str = " → ".join(output_trace[:max_length])
        if len(output_trace) > max_length:
            trace_str += f" ... (+{len(output_trace) - max_length} more)"
        lines.append(f"  Output {i}: {trace_str}")
    
    # Full trace
    lines.append(f"\nFULL TRACE ({len(trace.full_trace)} tokens):")
    full_str = " ".join(trace.full_trace[:max_length])
    if len(trace.full_trace) > max_length:
        full_str += f" ... (+{len(trace.full_trace) - max_length} more)"
    lines.append(f"  {full_str}")
    
    lines.append("=" * 60)
    return "\n".join(lines)