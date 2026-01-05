# Hardware Trojan Detection - Deep Learning Implementation

Implementation of "Deep Learning-based Hardware Trojan Detection with Block-based Netlist Information Extraction" (IEEE 2021)

## Project Status

### ✅ Completed: Step 1 - Netlist and Label Parsing

**Date:** January 5, 2026

**Implementation:**
- ✅ Verilog Parser (`src/parser/verilog_parser.py`)
- ✅ Label Parser (`src/parser/label_parser.py`)
- ✅ Cell library inference (no .lib file required!)
- ✅ Comprehensive test suite
- ✅ Sample data and test cases

**Key Features:**
1. **Verilog Parser**
   - Parses gate-level Verilog netlists
   - Extracts module, ports, components, and connections
   - Infers cell library from netlist (handles missing .lib files)
   - Supports various gate types and pin naming conventions

2. **Label Parser**
   - Extracts Trojan component names from Trust-Hub log files
   - Identifies trigger signals and affected signals
   - Classifies components as Normal vs. Trojan

## Project Structure

```
hardware_trojan_detection/
├── data/
│   ├── raw/
│   │   ├── netlists/           # Verilog netlist files
│   │   └── labels/             # Trust-Hub log files
│   └── processed/              # Parsed data (JSON)
├── src/
│   └── parser/
│       ├── verilog_parser.py   # ✅ Step 1A: Verilog parsing
│       └── label_parser.py     # ✅ Step 1B: Label parsing
├── tests/
│   └── test_step1.py           # ✅ Combined test script
└── requirements.txt            # Dependencies
```

## Quick Start

### 1. Test with Synthetic Data

```bash
# Test Verilog parser only
python src/parser/verilog_parser.py data/raw/netlists/test_circuit.v

# Test label parser only
python src/parser/label_parser.py data/raw/labels/test_circuit_log.txt

# Test both parsers together
python tests/test_step1.py data/raw/netlists/test_circuit.v data/raw/labels/test_circuit_log.txt
```

### 2. Use with Real Trust-Hub Data

```bash
# Place your Trust-Hub files:
# - data/raw/netlists/s15850_T436.v
# - data/raw/labels/s15850_T436_log.txt

# Run combined test
python tests/test_step1.py data/raw/netlists/s15850_T436.v data/raw/labels/s15850_T436_log.txt
```

## Usage Examples

### Parse Verilog Netlist

```python
from src.parser.verilog_parser import VerilogParser

parser = VerilogParser()
netlist_data = parser.parse('data/raw/netlists/s15850_T436.v')

print(f"Module: {netlist_data['module_name']}")
print(f"Components: {len(netlist_data['components'])}")
print(f"Cell Types: {len(netlist_data['cell_library'])}")
```

### Parse Trojan Labels

```python
from src.parser.label_parser import LabelParser

parser = LabelParser()
labels = parser.parse('data/raw/labels/s15850_T436_log.txt')

print(f"Trojan Type: {labels['trojan_type']}")
print(f"Trojan Components: {labels['num_trojans']}")
print(f"Trojan names: {labels['trojan_components']}")
```

### Classify Components

```python
# Check if a component is a Trojan
label_parser = LabelParser()
labels = label_parser.parse('labels.txt')

component_name = "trig122_0U1"
is_trojan = component_name in labels['trojan_components']
print(f"{component_name} is {'Trojan' if is_trojan else 'Normal'}")
```

## Test Results

### Synthetic Test Circuit

**Netlist:** `test_circuit.v`
- Module: test_circuit
- Components: 9 (5 normal + 4 Trojan)
- Ports: 5 (CK, rst, a, b, out)
- Wires: 11
- Cell Types: 6 (and2s1, or2s1, nor2s1, xor2s1, dffs2, hi1s1)

**Label Classification:**
- Normal: U1, U2, U3, reg0, U_out
- Trojan: trig_counter_reg_0, trig_counter_reg_1, trig_U1, trojan_payload

### Trust-Hub s15850_T436

**Expected Results:**
- Module: s15850
- Components: ~10,000+ (typical for ISCAS benchmark)
- Trojan Components: 24
  - 7 trigger circuit components (trig122_0U1-U7)
  - 4 counter registers (troj36_0counter_reg_*)
  - 12 payload logic gates (troj36_0U3-U13)
  - 1 final XOR payload (trojan36_0)

## Important Notes

### Handling Missing .lib Files

The Verilog parser **automatically infers the cell library** from the netlist itself:

1. Extracts all pin names from component instantiations
2. Uses heuristics to determine pin directions:
   - Output pins: Q, QN, Z, Y, OUT, O, S, CO, SUM
   - Input pins: A, B, C, D, DIN, CLK, EN, RST, SET

**Result:** No separate `.lib` file needed!

### Supported Verilog Format

- Gate-level netlists only (not behavioral)
- Named port connections: `.PIN(signal)`
- Standard Verilog comments: `//` and `/* */`
- Multiple components per module

## Next Steps

### Step 2: Pin-Level Graph Construction
- [ ] Implement graph data structures
- [ ] Build pin-level graph from parsed netlist
- [ ] Connect pins through nets

### Step 3: Netlist Block Extraction
- [ ] Implement BFS-based block extraction
- [ ] Support configurable logic levels
- [ ] Extract hierarchical block structure

### Step 4: PCP Trace Generation
- [ ] Convert blocks to PCP sequences
- [ ] Generate multiple traces per component
- [ ] Output in format ready for Skip-gram training

## Data Requirements

### Trust-Hub Benchmarks

**Website:** https://trust-hub.org/

**Required Files:**
1. Gate-level Verilog netlists (`.v` files)
2. Log files with Trojan labels (`log.txt`)

**Recommended Benchmark:**
- **LEDA library** - 914 samples (580 combinational + 334 sequential)
- Examples: s15850, s35932, c2670, c3540, etc.

## Testing

```bash
# Run Step 1 test suite
python tests/test_step1.py data/raw/netlists/test_circuit.v data/raw/labels/test_circuit_log.txt

# Expected output:
# ✓ Netlist parsed successfully
# ✓ Labels parsed successfully
# ✓ Component classification complete
# ✓ Parsed data saved to data/processed/
```

## Troubleshooting

**Issue:** Parser fails on complex Verilog syntax
- **Solution:** Ensure netlist is gate-level (not behavioral RTL)
- Verify port connections use named format: `.PIN(signal)`

**Issue:** No Trojan components found
- **Solution:** Check log file has "TROJAN BODY:" section
- Verify component names match exactly

**Issue:** Cell library inference incorrect
- **Solution:** Pin direction heuristics can be adjusted in `_infer_cell_library()`
- For specific libraries, you can manually override

## References

**Paper:** J. Cruz et al., "Deep Learning-based Hardware Trojan Detection with Block-based Netlist Information Extraction," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 2021

**Trust-Hub:** https://trust-hub.org/

## Author

Amirhossein  
Shahid Bahonar University of Kerman  
January 2026