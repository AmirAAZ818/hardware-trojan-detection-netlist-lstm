"""
Graph Builder - Constructs pin-level graphs from parsed netlists (Step 2)

This module takes the parsed netlist data from Step 1 and builds
a pin-level graph representation suitable for BFS-based block extraction.

Algorithm:
1. Create cell vertices for each component
2. Create pin vertices for each pin of each component
3. Create port vertices for module I/O
4. Connect cells ↔ their pins (bidirectional)
5. Connect pins through nets (directional: output → input)
"""

from typing import Dict, List, Set
from .netlist_graph import PinLevelGraph, Vertex, VertexType, create_pin_name


class GraphBuilder:
    """
    Builds a pin-level graph from parsed netlist data
    
    Input: Parsed netlist from VerilogParser (Step 1)
    Output: PinLevelGraph ready for block extraction (Step 3)
    """
    
    def __init__(self):
        self.graph = None
        self.netlist_data = None
    
    def build(self, netlist_data: Dict) -> PinLevelGraph:
        """
        Build a pin-level graph from parsed netlist data
        
        Args:
            netlist_data: Dictionary from VerilogParser containing:
                - module_name
                - ports
                - components
                - wires
                - cell_library
                
        Returns:
            PinLevelGraph object
        """
        self.netlist_data = netlist_data
        self.graph = PinLevelGraph()
        
        print(f"\nBuilding pin-level graph for module '{netlist_data['module_name']}'...")
        
        # Step 1: Create vertices for ports
        self._create_port_vertices()
        
        # Step 2: Create vertices for cells (components)
        self._create_cell_vertices()
        
        # Step 3: Create vertices for pins
        self._create_pin_vertices()
        
        # Step 4: Connect cells to their pins (bidirectional)
        self._connect_cells_to_pins()
        
        # Step 5: Connect pins through nets (directional)
        self._connect_pins_through_nets()
        
        stats = self.graph.get_statistics()
        print(f"✓ Graph built: {stats['num_vertices']} vertices, {stats['num_edges']} edges")
        
        return self.graph
    
    def _create_port_vertices(self):
        """Create vertex for each module port"""
        for port in self.netlist_data['ports']:
            port_name = port['name']
            
            vertex = Vertex(
                name=port_name,
                vertex_type=VertexType.PORT
            )
            vertex.pin_direction = port['direction']  # input or output
            
            self.graph.add_vertex(vertex)
        
        print(f"  Created {len(self.netlist_data['ports'])} port vertices")
    
    def _create_cell_vertices(self):
        """Create vertex for each component (cell)"""
        for component in self.netlist_data['components']:
            instance_name = component['instance']
            cell_type = component['cell_type']
            
            vertex = Vertex(
                name=instance_name,
                vertex_type=VertexType.CELL
            )
            vertex.cell_type = cell_type
            
            self.graph.add_vertex(vertex)
        
        print(f"  Created {len(self.netlist_data['components'])} cell vertices")
    
    def _create_pin_vertices(self):
        """
        Create vertex for each pin of each component
        
        For each component, creates pin vertices based on the cell library.
        Pin full name: <cell_name>.<pin_name> (e.g., "U1.DIN1")
        """
        cell_library = self.netlist_data['cell_library']
        pin_count = 0
        
        for component in self.netlist_data['components']:
            instance_name = component['instance']
            cell_type = component['cell_type']
            connections = component['connections']
            
            # Get pin definitions from cell library
            if cell_type not in cell_library:
                print(f"  Warning: Cell type '{cell_type}' not in library, skipping pins")
                continue
            
            pin_defs = cell_library[cell_type]
            
            # Create a vertex for each pin
            for pin_name, pin_direction in pin_defs.items():
                # Full pin name: instance.pin
                full_pin_name = create_pin_name(instance_name, pin_name)
                
                vertex = Vertex(
                    name=full_pin_name,
                    vertex_type=VertexType.PIN,
                    parent_cell=instance_name
                )
                vertex.pin_direction = pin_direction
                vertex.pin_name = pin_name
                
                # Get the net this pin is connected to
                if pin_name in connections:
                    vertex.net = connections[pin_name]
                
                self.graph.add_vertex(vertex)
                pin_count += 1
        
        print(f"  Created {pin_count} pin vertices")
    
    def _connect_cells_to_pins(self):
        """
        Connect each cell to its pins with bidirectional edges
        
        Creates edges: cell ↔ pin
        This allows traversal from cell to its pins and vice versa.
        """
        edge_count = 0
        
        for cell_name, pin_vertices in self.graph.cell_pins.items():
            for pin_vertex in pin_vertices:
                # Bidirectional edge: cell ↔ pin
                self.graph.add_bidirectional_edge(cell_name, pin_vertex.name)
                edge_count += 2  # Two edges (forward and backward)
        
        print(f"  Created {edge_count} cell-pin edges")
    
    def _connect_pins_through_nets(self):
        """
        Connect pins through nets (signal wires)
        
        For each net:
        - Find all pins connected to it
        - Connect: output pins → input pins
        - Also connect: ports → pins and pins → ports
        
        This creates the actual circuit connectivity.
        """
        edge_count = 0
        
        for net_name, pin_vertices in self.graph.nets.items():
            # Separate input and output pins on this net
            output_pins = []
            input_pins = []
            
            # Also check if this net is a port
            port_vertex = self.graph.get_vertex(net_name)
            
            for pin in pin_vertices:
                if pin.pin_direction == "output":
                    output_pins.append(pin)
                elif pin.pin_direction == "input":
                    input_pins.append(pin)
            
            # Connect outputs to inputs
            # Rule: Each output pin drives all input pins on the same net
            for output_pin in output_pins:
                for input_pin in input_pins:
                    self.graph.add_edge(output_pin.name, input_pin.name)
                    edge_count += 1
            
            # Handle port connections
            if port_vertex:
                if port_vertex.pin_direction == "input":
                    # Input port → all input pins on this net
                    for input_pin in input_pins:
                        self.graph.add_edge(port_vertex.name, input_pin.name)
                        edge_count += 1
                elif port_vertex.pin_direction == "output":
                    # Output pins → output port
                    for output_pin in output_pins:
                        self.graph.add_edge(output_pin.name, port_vertex.name)
                        edge_count += 1
        
        print(f"  Created {edge_count} pin-pin edges (through nets)")
    
    def get_graph_summary(self) -> str:
        """Get a summary string of the graph structure"""
        if not self.graph:
            return "No graph built yet"
        
        stats = self.graph.get_statistics()
        
        summary = f"""
Pin-Level Graph Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Module: {self.netlist_data['module_name']}

Vertices:
  Total:  {stats['num_vertices']}
  Cells:  {stats['num_cells']}
  Pins:   {stats['num_pins']}
  Ports:  {stats['num_ports']}

Edges:    {stats['num_edges']}
Nets:     {stats['num_nets']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary


def build_graph_from_netlist(netlist_data: Dict) -> PinLevelGraph:
    """
    Convenience function to build graph from parsed netlist
    
    Args:
        netlist_data: Output from VerilogParser
        
    Returns:
        PinLevelGraph object
    """
    builder = GraphBuilder()
    return builder.build(netlist_data)