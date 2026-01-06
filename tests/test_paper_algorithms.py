"""
Test: Paper-Correct Implementation (Algorithm 1 & 2)

This script tests the implementation following the paper's algorithms exactly:
- Algorithm 1: Netlist block extraction (tree-based)
- Algorithm 2: PCP trace generation (pin-level tokens)

Expected results:
- Each trace length = EXACTLY 2*logic_level + 1 (or less at boundaries)
- Token format: {input_pin}_{cell_type}_{output_pin}
- Cross products of input/output paths
"""

import sys
import os
import json
from pathlib import Path

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
from src.extraction.block_tree_extractor import BlockTreeExtractor
from src.extraction.netlist_block_tree import format_block_tree, format_pcp_trace
from src.traces.pcp_trace_generator import PCPTraceGenerator
from src.utils import config


def test_paper_algorithms(netlist_path, label_path=None, logic_level=None):
    """
    Test paper-correct implementation of Algorithms 1 & 2
    
    Args:
        netlist_path: Path to Verilog netlist
        label_path: Path to label file (optional)
        logic_level: BFS depth (default: from config)
    """
    
    if logic_level is None:
        logic_level = config.LOGIC_LEVEL
    
    print("="*80)
    print(" PAPER-CORRECT IMPLEMENTATION TEST (Algorithm 1 & 2)")
    print("="*80)
    
    # ========== Steps 1-2: Parse and Build Graph ==========
    print("\n[1/5] Parsing netlist and building graph...")
    print("-" * 80)
    
    # Parse
    verilog_parser = VerilogParser()
    netlist_data = verilog_parser.parse(netlist_path)
    print(f"✓ Parsed: {len(netlist_data['components'])} components")
    
    # Parse labels
    labels = None
    if label_path and os.path.exists(label_path):
        label_parser = LabelParser()
        labels = label_parser.parse(label_path)
        print(f"✓ Labels: {labels['num_trojans']} Trojan components")
    
    # Build graph
    builder = GraphBuilder()
    graph = builder.build(netlist_data)
    graph_stats = graph.get_statistics()
    print(f"✓ Graph: {graph_stats['num_vertices']} vertices, {graph_stats['num_edges']} edges")
    
    # ========== Step 3: Algorithm 1 - Block Tree Extraction ==========
    print(f"\n[2/5] Algorithm 1: Netlist block tree extraction (logic_level={logic_level})...")
    print("-" * 80)
    
    extractor = BlockTreeExtractor(graph, logic_level=logic_level)
    blocks = extractor.extract_all_blocks(verbose=True)
    
    # Get statistics
    block_stats = extractor.get_statistics()
    
    print(f"\n✓ Block trees extracted!")
    print(f"  Total blocks: {block_stats['num_blocks']}")
    print(f"  Logic level: {block_stats['logic_level']}")
    print(f"  Avg input nodes: {block_stats['avg_input_nodes']:.2f}")
    print(f"  Avg output nodes: {block_stats['avg_output_nodes']:.2f}")
    
    # ========== Step 4: Algorithm 2 - PCP Trace Generation ==========
    print(f"\n[3/5] Algorithm 2: PCP trace generation...")
    print("-" * 80)
    
    generator = PCPTraceGenerator(graph)
    traces_dict = generator.generate_all_traces(blocks, verbose=True)
    
    # Get statistics
    trace_stats = generator.get_statistics()
    
    print(f"\n✓ PCP traces generated!")
    print(f"  Total components: {trace_stats['num_components']}")
    print(f"  Total traces: {trace_stats['num_traces']}")
    print(f"  Avg traces per component: {trace_stats['avg_traces_per_component']:.2f}")
    print(f"  Expected trace length: {trace_stats['expected_trace_length']}")
    print(f"  Actual avg trace length: {trace_stats['avg_trace_length']:.2f}")
    print(f"  Min trace length: {trace_stats['min_trace_length']}")
    print(f"  Max trace length: {trace_stats['max_trace_length']}")
    print(f"  Traces with correct length: {trace_stats['traces_with_correct_length']} ({trace_stats['percentage_correct_length']:.1f}%)")
    
    # ========== Validation ==========
    print("\n[4/5] Validating implementation...")
    print("-" * 80)
    
    # Test 1: All components have traces
    if len(traces_dict) == len(netlist_data['components']):
        print(f"✓ All components have traces: {len(traces_dict)}")
    else:
        print(f"✗ Trace count mismatch: {len(traces_dict)}/{len(netlist_data['components'])}")
    
    # Test 2: Check trace lengths
    expected_length = 2 * logic_level + 1
    correct_lengths = trace_stats['traces_with_correct_length']
    total_traces = trace_stats['num_traces']
    percentage = trace_stats['percentage_correct_length']
    
    if percentage > 80:
        print(f"✓ Most traces have correct length: {correct_lengths}/{total_traces} ({percentage:.1f}%)")
    else:
        print(f"⚠ Some traces have unexpected lengths: {correct_lengths}/{total_traces} ({percentage:.1f}%)")
    
    # Test 3: Check token format
    sample_trace = generator.all_traces[0] if generator.all_traces else None
    if sample_trace and len(sample_trace.tokens) > 0:
        sample_token = sample_trace.tokens[0]
        if '_' in sample_token.to_string():
            print(f"✓ Tokens use pin-level format: {sample_token.to_string()}")
        else:
            print(f"✗ Token format unexpected: {sample_token.to_string()}")
    
    # ========== Show Sample Traces ==========
    print("\n[5/5] Sample traces:")
    print("-" * 80)
    
    # Show 2 normal components
    print("\nSample Normal Components:")
    normal_shown = 0
    for cell_name, trace_list in traces_dict.items():
        if labels and cell_name in labels['trojan_components']:
            continue
        if normal_shown < 2 and trace_list:
            print(format_pcp_trace(trace_list[0]))  # Show first trace for this component
            normal_shown += 1
    
    # Show Trojan components
    if labels:
        print("\nSample Trojan Components:")
        trojan_shown = 0
        for cell_name in labels['trojan_components'][:2]:
            if cell_name in traces_dict and traces_dict[cell_name]:
                print(format_pcp_trace(traces_dict[cell_name][0]))
                trojan_shown += 1
    
    # ========== Summary ==========
    print("\n" + "="*80)
    print(" IMPLEMENTATION TEST COMPLETE")
    print("="*80)
    
    print("\nResults:")
    print(f"  ✓ Algorithm 1 (Block extraction): {block_stats['num_blocks']} blocks")
    print(f"  ✓ Algorithm 2 (Trace generation): {trace_stats['num_traces']} traces")
    print(f"  ✓ Expected trace length: {expected_length} tokens")
    print(f"  ✓ Traces with correct length: {percentage:.1f}%")
    print(f"  ✓ Token format: PIN_CELLTYPE_PIN")
    
    if percentage >= 95:
        print("\n✅ EXCELLENT! Implementation matches paper closely!")
    elif percentage >= 80:
        print("\n✓ GOOD! Most traces correct (some variation at boundaries)")
    else:
        print("\n⚠ NEEDS REVIEW: Many traces have unexpected lengths")
    
    return generator, traces_dict, netlist_data, labels, graph, blocks


def save_results(generator, traces_dict, netlist_data, labels, output_dir):
    """
    Save results to files
    
    Args:
        generator: PCPTraceGenerator instance
        traces_dict: Dictionary of traces
        netlist_data: Parsed netlist data
        labels: Label data
        output_dir: Output directory
    """
    os.makedirs(output_dir, exist_ok=True)
    
    netlist_name = netlist_data['module_name']
    
    # 1. Save traces for training
    traces_path = os.path.join(output_dir, f"{netlist_name}_traces_paper.txt")
    generator.save_traces_for_training(traces_path)
    
    # 2. Save statistics
    stats_path = os.path.join(output_dir, f"{netlist_name}_trace_stats_paper.json")
    
    stats = {
        'module_name': netlist_name,
        'trace_statistics': generator.get_statistics(),
        'implementation': 'paper_algorithms',
        'algorithms_used': ['Algorithm 1', 'Algorithm 2'],
    }
    
    if labels:
        trojan_components = labels['trojan_components']
        trojan_traces = sum(len(traces_dict[c]) for c in trojan_components if c in traces_dict)
        normal_traces = generator.get_statistics()['num_traces'] - trojan_traces
        
        stats['classification'] = {
            'num_trojan_components': len(trojan_components),
            'num_trojan_traces': trojan_traces,
            'num_normal_traces': normal_traces,
        }
    
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"✓ Statistics saved: {stats_path}")


def main():
    """Main function"""
    
    # Parse arguments
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
    
    print()
    
    # Run test
    generator, traces_dict, netlist_data, labels, graph, blocks = test_paper_algorithms(
        netlist_path, label_path, logic_level
    )
    
    # Save results
    output_dir = str(config.PCP_TRACES_DIR)
    save_results(generator, traces_dict, netlist_data, labels, output_dir)


if __name__ == "__main__":
    main()