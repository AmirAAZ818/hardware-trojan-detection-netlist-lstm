#!/usr/bin/env python3
"""
Config Switcher - Easily switch between test data and real Trust-Hub data

Usage:
    python scripts/switch_config.py test      # Use synthetic test data
    python scripts/switch_config.py trusthub  # Use s15850_T436 data
    python scripts/switch_config.py custom <netlist> <label>  # Use custom files
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def update_config(netlist_filename, label_filename):
    """Update the config file with new default files"""
    config_path = Path(__file__).parent.parent / "src" / "utils" / "config.py"
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace the DEFAULT_NETLIST line
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if 'DEFAULT_NETLIST = NETLIST_DIR' in line and not line.strip().startswith('#'):
            new_lines.append(f'DEFAULT_NETLIST = NETLIST_DIR / "{netlist_filename}"')
        elif 'DEFAULT_LABEL = LABEL_DIR' in line and not line.strip().startswith('#'):
            new_lines.append(f'DEFAULT_LABEL = LABEL_DIR / "{label_filename}"')
        else:
            new_lines.append(line)
    
    # Write back
    with open(config_path, 'w') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✓ Config updated!")
    print(f"  Default Netlist: {netlist_filename}")
    print(f"  Default Label:   {label_filename}")
    print(f"\nYou can now run: python tests/test_step1.py")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "test":
        print("Switching to TEST data (synthetic)...")
        update_config("test_circuit.v", "test_circuit_log.txt")
        
    elif mode == "trusthub":
        print("Switching to TRUST-HUB data (s15850_T436)...")
        update_config("s15850_T436.v", "s15850_T436_log.txt")
        
    elif mode == "custom":
        if len(sys.argv) < 4:
            print("Error: Custom mode requires netlist and label filenames")
            print("Usage: python switch_config.py custom <netlist.v> <label.txt>")
            sys.exit(1)
        
        netlist = sys.argv[2]
        label = sys.argv[3]
        print(f"Switching to CUSTOM data...")
        update_config(netlist, label)
        
    else:
        print(f"Unknown mode: {mode}")
        print("Valid modes: test, trusthub, custom")
        sys.exit(1)


if __name__ == "__main__":
    main()