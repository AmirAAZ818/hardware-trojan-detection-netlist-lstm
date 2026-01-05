"""
Step 1 Test: Combined Netlist and Label Parsing

This script demonstrates both parsers working together and provides
a foundation for Step 2 (graph building).
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


def test_step1(netlist_path, label_path=None):
    """
    Test Step 1: Parse netlist and labels
    
    Args:
        netlist_path: Path to Verilog netlist file
        label_path: Path to log.txt file (optional)
    """
    
    print("="*80)
    print(" STEP 1: NETLIST AND LABEL PARSING TEST")
    print("="*80)
    
    # ========== Parse Verilog Netlist ==========
    print("\n[1/2] Parsing Verilog netlist...")
    print("-" * 80)
    
    verilog_parser = VerilogParser()
    netlist_data = verilog_parser.parse(netlist_path)
    
    # Print netlist statistics
    stats = verilog_parser.get_statistics()
    print(f"\n✓ Netlist parsed successfully!")
    print(f"  Module: {stats['module_name']}")
    print(f"  Components: {stats['num_components']}")
    print(f"  Ports: {stats['num_ports']}")
    print(f"  Internal Wires: {stats['num_wires']}")
    print(f"  Cell Types: {stats['num_cell_types']}")
    
    # Show cell library
    print(f"\nInferred Cell Library:")
    for i, (cell_type, pins) in enumerate(sorted(netlist_data['cell_library'].items())[:5], 1):
        pin_strs = [f"{name}({dir[0]})" for name, dir in pins.items()]
        print(f"  {i}. {cell_type:15s}: {', '.join(pin_strs)}")
    if len(netlist_data['cell_library']) > 5:
        print(f"  ... and {len(netlist_data['cell_library']) - 5} more cell types")
    
    # ========== Parse Labels (if provided) ==========
    if label_path and os.path.exists(label_path):
        print("\n[2/2] Parsing Trojan labels...")
        print("-" * 80)
        
        label_parser = LabelParser()
        label_data = label_parser.parse(label_path)
        
        print(f"\n✓ Labels parsed successfully!")
        print(f"  Trojan Type: {label_data['trojan_type']}")
        print(f"  Trojan Components: {label_data['num_trojans']}")
        print(f"  Affected Signals: {', '.join(label_data['affected_signals'])}")
        print(f"  Trigger Signals: {len(label_data['trigger_signals'])}")
        
        # Cross-reference: Check which parsed components are Trojans
        trojan_set = set(label_data['trojan_components'])
        normal_count = 0
        trojan_count = 0
        
        for component in netlist_data['components']:
            if component['instance'] in trojan_set:
                trojan_count += 1
            else:
                normal_count += 1
        
        print(f"\nComponent Classification:")
        print(f"  Normal components: {normal_count}")
        print(f"  Trojan components: {trojan_count}")
        print(f"  Total: {normal_count + trojan_count}")
        
        # Show examples of each
        print(f"\nSample Trojan Components (first 5):")
        shown = 0
        for component in netlist_data['components']:
            if component['instance'] in trojan_set and shown < 5:
                print(f"  {shown + 1}. {component['instance']} ({component['cell_type']})")
                shown += 1
        
        print(f"\nSample Normal Components (first 5):")
        shown = 0
        for component in netlist_data['components']:
            if component['instance'] not in trojan_set and shown < 5:
                print(f"  {shown + 1}. {component['instance']} ({component['cell_type']})")
                shown += 1
        
        # Prepare combined output
        output_data = {
            'netlist': netlist_data,
            'labels': label_data,
            'statistics': {
                'total_components': len(netlist_data['components']),
                'normal_components': normal_count,
                'trojan_components': trojan_count
            }
        }
    else:
        print("\n[2/2] No label file provided, skipping...")
        output_data = {
            'netlist': netlist_data,
            'labels': None,
            'statistics': {
                'total_components': len(netlist_data['components']),
                'normal_components': len(netlist_data['components']),
                'trojan_components': 0
            }
        }
    
    # ========== Summary ==========
    print("\n" + "="*80)
    print(" STEP 1 COMPLETE - READY FOR STEP 2 (GRAPH BUILDING)")
    print("="*80)
    print("\nNext Steps:")
    print("  1. Build pin-level graph from parsed netlist")
    print("  2. Extract netlist blocks using BFS")
    print("  3. Generate PCP traces")
    
    return output_data


def save_parsed_data(data, output_path):
    """Save parsed data to JSON file"""
    # Convert sets to lists for JSON serialization
    if 'netlist' in data and 'wires' in data['netlist']:
        if isinstance(data['netlist']['wires'], set):
            data['netlist']['wires'] = list(data['netlist']['wires'])
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✓ Parsed data saved to: {output_path}")


def main():
    """Main function"""
    # Import config
    from src.utils import config
    
    # Parse command-line arguments (optional now!)
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
            print("  3. Run with arguments: python test_step1.py <netlist> [label]")
            sys.exit(1)
    
    print()  # Blank line for readability
    
    # Run test
    parsed_data = test_step1(netlist_path, label_path)
    
    # Save output using config
    output_path = config.get_output_path(netlist_path, suffix="_parsed")
    save_parsed_data(parsed_data, str(output_path))


if __name__ == "__main__":
    main()