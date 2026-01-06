"""
Step 3 Test: Netlist Block Extraction (BFS-based)

This script tests the netlist block extraction by:
1. Building graph from parsed netlist (Step 1-2)
2. Extracting netlist blocks using BFS (Step 3)
3. Validating block structure
4. Showing sample blocks
5. Preparing data for Step 4 (PCP trace generation)
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
from src.extraction.block_extractor import BlockExtractor
from src.extraction.netlist_block import format_netlist_block
from src.utils import config


def test_step3(netlist_path, label_path=None, logic_level=None):
    """
    Test Step 3: Extract netlist blocks from graph
    
    Args:
        netlist_path: Path to Verilog netlist
        label_path: Path to label file (optional)
        logic_level: BFS depth (default: from config)
    """
    
    if logic_level is None:
        logic_level = config.LOGIC_LEVEL
    
    print("="*80)
    print(" STEP 3: NETLIST BLOCK EXTRACTION TEST")
    print("="*80)
    
    # ========== Step 1-2: Parse and Build Graph ==========
    print("\n[1/4] Parsing netlist and building graph...")
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
    
    # ========== Step 3: Extract Netlist Blocks ==========
    print(f"\n[2/4] Extracting netlist blocks (logic_level={logic_level})...")
    print("-" * 80)
    
    extractor = BlockExtractor(graph, logic_level=logic_level)
    blocks = extractor.extract_all_blocks(verbose=True)
    
    # Get statistics
    block_stats = extractor.get_statistics()
    
    print(f"\n✓ Netlist blocks extracted!")
    print(f"  Total blocks: {block_stats['num_blocks']}")
    print(f"  Logic level: {block_stats['logic_level']}")
    print(f"  Avg nets per block: {block_stats['avg_nets_per_block']:.2f}")
    print(f"  Avg input paths: {block_stats['avg_input_paths']:.2f}")
    print(f"  Avg output paths: {block_stats['avg_output_paths']:.2f}")
    
    # ========== Step 4: Validate Blocks ==========
    print("\n[3/4] Validating block structure...")
    print("-" * 80)
    
    # Test 1: Check all components have blocks
    components_with_blocks = len(blocks)
    total_components = len(netlist_data['components'])
    
    if components_with_blocks == total_components:
        print(f"✓ All components have blocks: {components_with_blocks}")
    else:
        print(f"✗ Block count mismatch: {components_with_blocks}/{total_components}")
    
    # Test 2: Check block structure
    sample_block = list(blocks.values())[0]
    if len(sample_block.input_side) > 0 and len(sample_block.output_side) > 0:
        print(f"✓ Blocks have input and output sides")
    
    # Test 3: Check hierarchical structure
    has_hierarchy = False
    for block in list(blocks.values())[:10]:
        if block.input_side:
            if len(block.input_side[0]) > 1:  # More than 1 level
                has_hierarchy = True
                break
    
    if has_hierarchy:
        print(f"✓ Blocks have hierarchical structure (multiple levels)")
    
    # ========== Step 5: Show Sample Blocks ==========
    print("\n[4/4] Sample netlist blocks:")
    print("-" * 80)
    
    # Show 3 normal components
    print("\nSample Normal Components:")
    normal_shown = 0
    for cell_name, block in blocks.items():
        if labels and cell_name in labels['trojan_components']:
            continue
        if normal_shown < 2:
            print(format_netlist_block(block, max_nets_per_level=3))
            normal_shown += 1
    
    # Show Trojan components if available
    if labels:
        print("\nSample Trojan Components:")
        trojan_shown = 0
        for cell_name in labels['trojan_components'][:2]:
            if cell_name in blocks:
                print(format_netlist_block(blocks[cell_name], max_nets_per_level=3))
                trojan_shown += 1
                if trojan_shown >= 2:
                    break
    
    # ========== Summary ==========
    print("\n" + "="*80)
    print(" STEP 3 COMPLETE - NETLIST BLOCKS EXTRACTED")
    print("="*80)
    
    print("\nBlocks ready for Step 4 (PCP Trace Generation)!")
    print(f"  ✓ {block_stats['num_blocks']} blocks extracted")
    print(f"  ✓ Hierarchical structure (logic_level={logic_level})")
    print(f"  ✓ Input and output paths")
    print(f"  ✓ Ready for flattening to PCP traces")
    
    return blocks, netlist_data, labels, graph


def save_blocks_summary(blocks, netlist_data, labels, output_path):
    """
    Save blocks summary to JSON
    
    Note: We only save statistics, not all block data (too large)
    For actual PCP traces, use Step 4
    """
    
    # Get overall statistics
    extractor = BlockExtractor(None)  # Dummy
    extractor.blocks = blocks
    stats = extractor.get_statistics()
    
    # Sample a few blocks
    sample_blocks = {}
    for cell_name in list(blocks.keys())[:5]:
        block = blocks[cell_name]
        sample_blocks[cell_name] = block.to_dict()
    
    # Classification
    if labels:
        trojan_blocks = [name for name in blocks.keys() 
                        if name in labels['trojan_components']]
        normal_blocks = [name for name in blocks.keys() 
                        if name not in labels['trojan_components']]
        
        classification = {
            'num_trojan_blocks': len(trojan_blocks),
            'num_normal_blocks': len(normal_blocks),
            'trojan_block_names': trojan_blocks[:10],  # First 10
        }
    else:
        classification = {
            'num_trojan_blocks': 0,
            'num_normal_blocks': len(blocks),
        }
    
    summary = {
        'module_name': netlist_data['module_name'],
        'statistics': stats,
        'classification': classification,
        'sample_blocks': sample_blocks,
    }
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Blocks summary saved to: {output_path}")


def main():
    """Main function"""
    
    # Parse command-line arguments
    if len(sys.argv) >= 2:
        netlist_path = sys.argv[1]
        label_path = sys.argv[2] if len(sys.argv) > 2 else None
        logic_level = int(sys.argv[3]) if len(sys.argv) > 3 else None
        print(f"Using provided files:")
        print(f"  Netlist: {netlist_path}")
        if label_path:
            print(f"  Labels:  {label_path}")
        if logic_level:
            print(f"  Logic Level: {logic_level}")
    else:
        print("No arguments provided, using config defaults...")
        config.print_config()
        
        netlist_path = str(config.DEFAULT_NETLIST)
        label_path = str(config.DEFAULT_LABEL) if config.DEFAULT_LABEL.exists() else None
        logic_level = config.LOGIC_LEVEL
        
        if not os.path.exists(netlist_path):
            print("\n❌ Error: Default netlist file not found!")
            print(f"   Expected: {netlist_path}")
            sys.exit(1)
    
    print()  # Blank line
    
    # Run test
    blocks, netlist_data, labels, graph = test_step3(netlist_path, label_path, logic_level)
    
    # Save summary
    output_path = config.get_output_path(netlist_path, suffix="_blocks_summary")
    save_blocks_summary(blocks, netlist_data, labels, str(output_path))


if __name__ == "__main__":
    main()