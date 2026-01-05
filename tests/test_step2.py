"""
Step 2 Test: Pin-Level Graph Construction

This script tests the graph building functionality by:
1. Loading parsed netlist from Step 1
2. Building pin-level graph
3. Validating graph structure
4. Testing graph operations
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
from src.graph.netlist_graph import VertexType
from src.utils import config


def test_step2(netlist_path, label_path=None):
    """
    Test Step 2: Build pin-level graph from netlist
    
    Args:
        netlist_path: Path to Verilog netlist
        label_path: Path to label file (optional)
    """
    
    print("="*80)
    print(" STEP 2: PIN-LEVEL GRAPH CONSTRUCTION TEST")
    print("="*80)
    
    # ========== Step 1: Parse Netlist ==========
    print("\n[1/3] Parsing netlist...")
    print("-" * 80)
    
    verilog_parser = VerilogParser()
    netlist_data = verilog_parser.parse(netlist_path)
    
    stats = verilog_parser.get_statistics()
    print(f"✓ Parsed: {stats['num_components']} components, {stats['num_cell_types']} cell types")
    
    # Parse labels if provided
    labels = None
    if label_path and os.path.exists(label_path):
        label_parser = LabelParser()
        labels = label_parser.parse(label_path)
        print(f"✓ Labels: {labels['num_trojans']} Trojan components")
    
    # ========== Step 2: Build Graph ==========
    print("\n[2/3] Building pin-level graph...")
    print("-" * 80)
    
    builder = GraphBuilder()
    graph = builder.build(netlist_data)
    
    # Print summary
    print(builder.get_graph_summary())
    
    # ========== Step 3: Validate Graph ==========
    print("[3/3] Validating graph structure...")
    print("-" * 80)
    
    # Test 1: Check vertex counts
    graph_stats = graph.get_statistics()
    expected_cells = len(netlist_data['components'])
    
    if graph_stats['num_cells'] == expected_cells:
        print(f"✓ Cell count matches: {graph_stats['num_cells']}")
    else:
        print(f"✗ Cell count mismatch: expected {expected_cells}, got {graph_stats['num_cells']}")
    
    # Test 2: Check all cells have pins
    cells_without_pins = []
    for cell_name in graph.cells:
        pins = graph.get_cell_pins(cell_name)
        if len(pins) == 0:
            cells_without_pins.append(cell_name)
    
    if len(cells_without_pins) == 0:
        print(f"✓ All cells have pins")
    else:
        print(f"✗ {len(cells_without_pins)} cells have no pins")
    
    # Test 3: Sample some components
    print(f"\nSample Components (showing graph structure):")
    sample_components = list(netlist_data['components'])[:3]
    
    for i, comp in enumerate(sample_components, 1):
        instance = comp['instance']
        cell_type = comp['cell_type']
        
        # Get pins
        input_pins = graph.get_cell_input_pins(instance)
        output_pins = graph.get_cell_output_pins(instance)
        
        print(f"\n{i}. {instance} ({cell_type})")
        print(f"   Input pins:  {len(input_pins)}")
        for pin in input_pins[:3]:  # Show first 3
            neighbors = graph.get_neighbors(pin.name, "forward")
            print(f"     - {pin.name} → {len(neighbors)} connections")
        
        print(f"   Output pins: {len(output_pins)}")
        for pin in output_pins[:3]:  # Show first 3
            neighbors = graph.get_neighbors(pin.name, "forward")
            print(f"     - {pin.name} → {len(neighbors)} connections")
    
    # Test 4: Check connectivity
    total_connections = 0
    for vertex_name in graph.vertices:
        neighbors = graph.get_neighbors(vertex_name, "forward")
        total_connections += len(neighbors)
    
    print(f"\n✓ Total forward connections: {total_connections}")
    if len(graph.vertices) > 0:
        print(f"✓ Average connections per vertex: {total_connections / len(graph.vertices):.2f}")
    
    # Test 5: If labels provided, check Trojan components
    if labels:
        print(f"\nTrojan Component Graph Structure:")
        trojan_comps = labels['trojan_components'][:3]  # First 3
        
        for comp_name in trojan_comps:
            if comp_name in graph.cells:
                input_pins = graph.get_cell_input_pins(comp_name)
                output_pins = graph.get_cell_output_pins(comp_name)
                print(f"  {comp_name}: {len(input_pins)} inputs, {len(output_pins)} outputs")
    
    # ========== Summary ==========
    print("\n" + "="*80)
    print(" STEP 2 COMPLETE - GRAPH BUILT SUCCESSFULLY")
    print("="*80)
    
    print("\nGraph ready for Step 3 (Netlist Block Extraction)!")
    print("  ✓ Pin-level representation")
    print("  ✓ Cell-pin connections")
    print("  ✓ Net-based connectivity")
    print("  ✓ Ready for BFS traversal")
    
    return graph, netlist_data, labels


def save_graph_info(graph, netlist_data, output_path):
    """Save graph information to JSON file"""
    
    # Get graph statistics
    stats = graph.get_statistics()
    
    # Sample some vertices
    sample_cells = list(graph.cells.keys())[:10]
    sample_pins = list(graph.pins.keys())[:20]
    
    graph_info = {
        'module_name': netlist_data['module_name'],
        'statistics': stats,
        'sample_cells': sample_cells,
        'sample_pins': sample_pins,
        'num_components': len(netlist_data['components']),
    }
    
    with open(output_path, 'w') as f:
        json.dump(graph_info, f, indent=2)
    
    print(f"\n✓ Graph info saved to: {output_path}")


def main():
    """Main function"""
    
    # Parse command-line arguments
    if len(sys.argv) >= 2:
        # Use provided arguments
        netlist_path = sys.argv[1]
        label_path = sys.argv[2] if len(sys.argv) > 2 else None
        print(f"Using provided files:")
        print(f"  Netlist: {netlist_path}")
        if label_path:
            print(f"  Labels:  {label_path}")
    else:
        # Use config defaults
        print("No arguments provided, using config defaults...")
        config.print_config()
        
        netlist_path = str(config.DEFAULT_NETLIST)
        label_path = str(config.DEFAULT_LABEL) if config.DEFAULT_LABEL.exists() else None
        
        if not os.path.exists(netlist_path):
            print("\n❌ Error: Default netlist file not found!")
            print(f"   Expected: {netlist_path}")
            print("\nOptions:")
            print("  1. Place your netlist file at the default location")
            print("  2. Update DEFAULT_NETLIST in src/utils/config.py")
            print("  3. Run with arguments: python test_step2.py <netlist> [label]")
            sys.exit(1)
    
    print()  # Blank line
    
    # Run test
    graph, netlist_data, labels = test_step2(netlist_path, label_path)
    
    # Save graph info using config
    output_path = config.get_output_path(netlist_path, suffix="_graph_info")
    save_graph_info(graph, netlist_data, str(output_path))


if __name__ == "__main__":
    main()