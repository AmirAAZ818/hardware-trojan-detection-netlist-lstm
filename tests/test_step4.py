"""
Step 4 Test: PCP Trace Generation

This script tests PCP trace generation by:
1. Building graph and extracting blocks (Steps 1-3)
2. Generating PCP traces from blocks (Step 4)
3. Building vocabulary
4. Saving traces for skip-gram training (Step 5)
5. Optional: Visualizing sample blocks
"""

import sys
import os
import json
from pathlib import Path

# ==========================================
# FIX: Add project root to Python path
# ==========================================
# Get the directory where this script is located
current_dir = Path(__file__).resolve().parent
# Get the parent directory (project root)
project_root = current_dir.parent
# Add to sys.path if not already there
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
# ==========================================

from src.parser.verilog_parser import VerilogParser
from src.parser.label_parser import LabelParser
from src.graph.graph_builder import GraphBuilder
from src.extraction.block_extractor import BlockExtractor
from src.traces.trace_generator import TraceGenerator
from src.traces.pcp_trace import format_pcp_trace
from src.utils import config

# Optional visualization
try:
    from src.visualization.block_visualizer import visualize_sample_blocks
    HAS_VISUALIZATION = True
except ImportError:
    HAS_VISUALIZATION = False


def test_step4(netlist_path, label_path=None, logic_level=None, visualize=False):
    """
    Test Step 4: Generate PCP traces
    
    Args:
        netlist_path: Path to Verilog netlist
        label_path: Path to label file (optional)
        logic_level: BFS depth (default: from config)
        visualize: Whether to generate visualizations
    """
    
    if logic_level is None:
        logic_level = config.LOGIC_LEVEL
    
    print("="*80)
    print(" STEP 4: PCP TRACE GENERATION TEST")
    print("="*80)
    
    # ========== Steps 1-3: Parse, Build Graph, Extract Blocks ==========
    print("\n[1/5] Parsing netlist, building graph, extracting blocks...")
    print("-" * 80)
    
    # Parse
    verilog_parser = VerilogParser()
    netlist_data = verilog_parser.parse(netlist_path)
    print(f"✓ Parsed: {len(netlist_data['components'])} components")
    
    # Labels
    labels = None
    if label_path and os.path.exists(label_path):
        label_parser = LabelParser()
        labels = label_parser.parse(label_path)
        print(f"✓ Labels: {labels['num_trojans']} Trojan components")
    
    # Build graph
    builder = GraphBuilder()
    graph = builder.build(netlist_data)
    print(f"✓ Graph: {graph.get_statistics()['num_vertices']} vertices")
    
    # Extract blocks
    extractor = BlockExtractor(graph, logic_level=logic_level)
    blocks = extractor.extract_all_blocks(verbose=False)
    print(f"✓ Blocks: {len(blocks)} extracted (logic_level={logic_level})")
    
    # ========== Step 4: Generate PCP Traces ==========
    print(f"\n[2/5] Generating PCP traces...")
    print("-" * 80)
    
    generator = TraceGenerator(graph)
    traces = generator.generate_all_traces(blocks, verbose=True)
    
    # Get statistics
    trace_stats = generator.get_statistics()
    vocab_stats = generator.vocabulary.get_statistics()
    
    print(f"\n✓ PCP traces generated!")
    print(f"  Total traces: {trace_stats['num_traces']}")
    print(f"  Vocabulary size: {trace_stats['vocab_size']}")
    print(f"  Avg trace length: {trace_stats['avg_trace_length']:.2f}")
    print(f"  Total tokens: {trace_stats['total_tokens']}")
    print(f"\nMost common cell types:")
    for cell_type, count in vocab_stats['most_common'][:5]:
        print(f"  - {cell_type}: {count}")
    
    # ========== Validation ==========
    print("\n[3/5] Validating traces...")
    print("-" * 80)
    
    # Test 1: All blocks have traces
    if len(traces) == len(blocks):
        print(f"✓ All blocks have traces: {len(traces)}")
    else:
        print(f"✗ Trace count mismatch: {len(traces)}/{len(blocks)}")
    
    # Test 2: Traces contain cell types
    has_content = all(len(trace.full_trace) > 0 for trace in traces.values())
    if has_content:
        print(f"✓ All traces have content")
    
    # Test 3: Center type is in trace
    center_in_trace = all(trace.center_type in trace.full_trace 
                         for trace in traces.values())
    if center_in_trace:
        print(f"✓ Center cell type present in all traces")
    
    # ========== Show Sample Traces ==========
    print("\n[4/5] Sample PCP traces:")
    print("-" * 80)
    
    # Normal components
    print("\nSample Normal Components:")
    normal_shown = 0
    for cell_name, trace in traces.items():
        if labels and cell_name in labels['trojan_components']:
            continue
        if normal_shown < 2:
            print(format_pcp_trace(trace, max_length=10))
            normal_shown += 1
    
    # Trojan components
    if labels:
        print("\nSample Trojan Components:")
        trojan_shown = 0
        for cell_name in labels['trojan_components'][:2]:
            if cell_name in traces:
                print(format_pcp_trace(traces[cell_name], max_length=10))
                trojan_shown += 1
    
    # ========== Optional Visualization ==========
    if visualize and HAS_VISUALIZATION:
        print("\n[5/5] Generating visualizations...")
        print("-" * 80)
        
        viz_dir = os.path.join(config.VISUALIZATIONS_DIR, 
                              Path(netlist_path).stem)
        
        try:
            visualize_sample_blocks(blocks, labels, graph, viz_dir, num_samples=3)
        except Exception as e:
            print(f"Warning: Visualization failed: {e}")
    elif visualize and not HAS_VISUALIZATION:
        print("\n[5/5] Skipping visualization (networkx not installed)")
        print("-" * 80)
        print("Install with: pip install networkx matplotlib")
    else:
        print("\n[5/5] Skipping visualization (use --visualize flag to enable)")
        print("-" * 80)
    
    # ========== Summary ==========
    print("\n" + "="*80)
    print(" STEP 4 COMPLETE - PCP TRACES GENERATED")
    print("="*80)
    
    print("\nTraces ready for Step 5 (Skip-gram Training)!")
    print(f"  ✓ {trace_stats['num_traces']} traces")
    print(f"  ✓ {trace_stats['vocab_size']} unique cell types")
    print(f"  ✓ {trace_stats['total_tokens']} total tokens")
    print(f"  ✓ Ready for Word2Vec / Skip-gram")
    
    return traces, generator, netlist_data, labels, graph, blocks


def save_traces_and_vocab(traces, generator, netlist_data, labels, output_dir):
    """
    Save traces and vocabulary for Step 5
    
    Args:
        traces: Dictionary of PCPTrace objects
        generator: TraceGenerator instance
        netlist_data: Parsed netlist data
        labels: Label data
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    
    netlist_name = netlist_data['module_name']
    
    # 1. Save traces for training (one per line, space-separated)
    traces_path = os.path.join(output_dir, f"{netlist_name}_traces.txt")
    generator.save_traces_for_training(traces_path)
    
    # 2. Save vocabulary
    vocab_path = os.path.join(output_dir, f"{netlist_name}_vocabulary.json")
    with open(vocab_path, 'w') as f:
        json.dump(generator.vocabulary.to_dict(), f, indent=2)
    print(f"✓ Vocabulary saved: {vocab_path}")
    
    # 3. Save trace statistics
    stats_path = os.path.join(output_dir, f"{netlist_name}_trace_stats.json")
    
    # Classify traces
    if labels:
        trojan_traces = [name for name in traces.keys() 
                        if name in labels['trojan_components']]
        normal_traces = [name for name in traces.keys() 
                        if name not in labels['trojan_components']]
        classification = {
            'num_trojan_traces': len(trojan_traces),
            'num_normal_traces': len(normal_traces),
        }
    else:
        classification = {
            'num_trojan_traces': 0,
            'num_normal_traces': len(traces),
        }
    
    stats = {
        'module_name': netlist_name,
        'trace_statistics': generator.get_statistics(),
        'vocabulary_statistics': generator.vocabulary.get_statistics(),
        'classification': classification,
    }
    
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Statistics saved: {stats_path}")


def main():
    """Main function"""
    
    # Parse arguments
    visualize = '--visualize' in sys.argv or '-v' in sys.argv
    
    if len(sys.argv) >= 2 and not sys.argv[1].startswith('-'):
        netlist_path = sys.argv[1]
        label_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else None
        logic_level = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('-') else None
        print(f"Using provided files:")
        print(f"  Netlist: {netlist_path}")
        if label_path:
            print(f"  Labels:  {label_path}")
    else:
        print("No arguments provided, using config defaults...")
        config.print_config()
        
        netlist_path = str(config.DEFAULT_NETLIST)
        label_path = str(config.DEFAULT_LABEL) if config.DEFAULT_LABEL.exists() else None
        logic_level = config.LOGIC_LEVEL
        
        if not os.path.exists(netlist_path):
            print("\n❌ Error: Default netlist file not found!")
            sys.exit(1)
    
    if visualize:
        print(f"  Visualization: ENABLED")
    print()
    
    # Run test
    traces, generator, netlist_data, labels, graph, blocks = test_step4(
        netlist_path, label_path, logic_level, visualize=visualize
    )
    
    # Save outputs
    output_dir = str(config.PCP_TRACES_DIR)
    save_traces_and_vocab(traces, generator, netlist_data, labels, output_dir)


if __name__ == "__main__":
    main()