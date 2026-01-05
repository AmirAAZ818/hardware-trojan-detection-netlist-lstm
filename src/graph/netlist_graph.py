"""
Pin-Level Graph Data Structures

This module provides the core graph data structures for representing
netlists at the pin level (Step 2).

Key Concepts:
- Vertex: Represents a cell, pin, or port
- PinLevelGraph: Complete graph with vertices and edges
- Each component is split into: cell vertex + pin vertices
- Edges connect: cell ↔ pins, and pin → pin (through nets)
"""

from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from enum import Enum


class VertexType(Enum):
    """Type of vertex in the pin-level graph"""
    CELL = "cell"       # Component/gate instance (e.g., U1, U2)
    PIN = "pin"         # Pin of a component (e.g., U1.DIN1, U1.Q)
    PORT = "port"       # Module I/O port (e.g., clk, rst, out)


class Vertex:
    """
    Represents a vertex in the pin-level graph
    
    A vertex can be:
    - CELL: A component instance (e.g., "U1")
    - PIN: A pin of a component (e.g., "U1.DIN1")
    - PORT: A module input/output port (e.g., "clk")
    """
    
    def __init__(self, name: str, vertex_type: VertexType, 
                 parent_cell: Optional[str] = None):
        """
        Initialize a vertex
        
        Args:
            name: Unique name of the vertex
            vertex_type: Type of vertex (CELL, PIN, or PORT)
            parent_cell: For PINs, the cell they belong to
        """
        self.name = name
        self.type = vertex_type
        self.parent_cell = parent_cell  # For pins: which cell they belong to
        
        # Additional attributes
        self.cell_type = None       # For cells: gate type (e.g., "and2s1")
        self.pin_direction = None   # For pins: "input" or "output"
        self.pin_name = None        # For pins: pin name without cell (e.g., "DIN1")
        self.net = None             # For pins: which net they're connected to
        
    def __repr__(self):
        if self.type == VertexType.CELL:
            return f"Cell({self.name}, {self.cell_type})"
        elif self.type == VertexType.PIN:
            return f"Pin({self.name}, {self.pin_direction})"
        else:
            return f"Port({self.name})"
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Vertex):
            return self.name == other.name
        return False


class PinLevelGraph:
    """
    Pin-level graph representation of a netlist
    
    Structure:
    - Vertices: Cells, pins, and ports
    - Edges: Connections between vertices
    - Adjacency lists: For efficient traversal
    
    Example for component: and2s1 U1 (.DIN1(a), .DIN2(b), .Q(out));
    
    Vertices:
    - Cell: "U1"
    - Pins: "U1.DIN1", "U1.DIN2", "U1.Q"
    
    Edges:
    - U1 ↔ U1.DIN1 (bidirectional: cell connects to its pins)
    - U1 ↔ U1.DIN2
    - U1 ↔ U1.Q
    - (other components' output) → U1.DIN1 (through net "a")
    - U1.Q → (other components' inputs) (through net "out")
    """
    
    def __init__(self):
        """Initialize an empty pin-level graph"""
        self.vertices = {}  # {vertex_name: Vertex}
        self.edges = []     # [(from_vertex, to_vertex), ...]
        
        # Adjacency lists for efficient traversal
        self.adjacency = defaultdict(set)  # {vertex_name: {neighbor_names}}
        
        # Reverse adjacency for backward traversal
        self.reverse_adjacency = defaultdict(set)
        
        # Index structures for quick lookup
        self.cells = {}      # {cell_name: Vertex}
        self.pins = {}       # {pin_full_name: Vertex}
        self.ports = {}      # {port_name: Vertex}
        
        # Net-based index: {net_name: {pin_vertices}}
        self.nets = defaultdict(set)
        
        # Cell-based index: {cell_name: {pin_vertices}}
        self.cell_pins = defaultdict(set)
    
    def add_vertex(self, vertex: Vertex):
        """
        Add a vertex to the graph
        
        Args:
            vertex: Vertex to add
        """
        self.vertices[vertex.name] = vertex
        
        # Update indexes
        if vertex.type == VertexType.CELL:
            self.cells[vertex.name] = vertex
        elif vertex.type == VertexType.PIN:
            self.pins[vertex.name] = vertex
            if vertex.parent_cell:
                self.cell_pins[vertex.parent_cell].add(vertex)
            if vertex.net:
                self.nets[vertex.net].add(vertex)
        elif vertex.type == VertexType.PORT:
            self.ports[vertex.name] = vertex
    
    def add_edge(self, from_vertex: str, to_vertex: str):
        """
        Add a directed edge from one vertex to another
        
        Args:
            from_vertex: Name of source vertex
            to_vertex: Name of target vertex
        """
        # Check vertices exist
        if from_vertex not in self.vertices:
            raise ValueError(f"Vertex not found: {from_vertex}")
        if to_vertex not in self.vertices:
            raise ValueError(f"Vertex not found: {to_vertex}")
        
        # Add edge
        edge = (from_vertex, to_vertex)
        if edge not in self.edges:
            self.edges.append(edge)
        
        # Update adjacency lists
        self.adjacency[from_vertex].add(to_vertex)
        self.reverse_adjacency[to_vertex].add(from_vertex)
    
    def add_bidirectional_edge(self, vertex1: str, vertex2: str):
        """
        Add bidirectional edges between two vertices
        
        Args:
            vertex1: Name of first vertex
            vertex2: Name of second vertex
        """
        self.add_edge(vertex1, vertex2)
        self.add_edge(vertex2, vertex1)
    
    def get_neighbors(self, vertex_name: str, direction: str = "both") -> Set[str]:
        """
        Get neighbors of a vertex
        
        Args:
            vertex_name: Name of the vertex
            direction: "forward", "backward", or "both"
            
        Returns:
            Set of neighbor vertex names
        """
        if direction == "forward":
            return self.adjacency.get(vertex_name, set())
        elif direction == "backward":
            return self.reverse_adjacency.get(vertex_name, set())
        else:  # both
            forward = self.adjacency.get(vertex_name, set())
            backward = self.reverse_adjacency.get(vertex_name, set())
            return forward | backward
    
    def get_cell_pins(self, cell_name: str) -> Set[Vertex]:
        """
        Get all pin vertices for a given cell
        
        Args:
            cell_name: Name of the cell
            
        Returns:
            Set of pin Vertex objects
        """
        return self.cell_pins.get(cell_name, set())
    
    def get_cell_input_pins(self, cell_name: str) -> List[Vertex]:
        """
        Get input pins of a cell
        
        Args:
            cell_name: Name of the cell
            
        Returns:
            List of input pin Vertex objects
        """
        pins = self.get_cell_pins(cell_name)
        return [p for p in pins if p.pin_direction == "input"]
    
    def get_cell_output_pins(self, cell_name: str) -> List[Vertex]:
        """
        Get output pins of a cell
        
        Args:
            cell_name: Name of the cell
            
        Returns:
            List of output pin Vertex objects
        """
        pins = self.get_cell_pins(cell_name)
        return [p for p in pins if p.pin_direction == "output"]
    
    def get_pins_by_net(self, net_name: str) -> Set[Vertex]:
        """
        Get all pins connected to a specific net
        
        Args:
            net_name: Name of the net
            
        Returns:
            Set of pin Vertex objects
        """
        return self.nets.get(net_name, set())
    
    def get_vertex(self, name: str) -> Optional[Vertex]:
        """Get a vertex by name"""
        return self.vertices.get(name)
    
    def has_edge(self, from_vertex: str, to_vertex: str) -> bool:
        """Check if an edge exists"""
        return to_vertex in self.adjacency.get(from_vertex, set())
    
    def get_statistics(self) -> Dict:
        """Get statistics about the graph"""
        return {
            'num_vertices': len(self.vertices),
            'num_cells': len(self.cells),
            'num_pins': len(self.pins),
            'num_ports': len(self.ports),
            'num_edges': len(self.edges),
            'num_nets': len(self.nets),
        }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (f"PinLevelGraph("
                f"vertices={stats['num_vertices']}, "
                f"cells={stats['num_cells']}, "
                f"pins={stats['num_pins']}, "
                f"edges={stats['num_edges']})")


def create_pin_name(cell_name: str, pin_name: str) -> str:
    """
    Create a full pin name from cell name and pin name
    
    Args:
        cell_name: Name of the cell (e.g., "U1")
        pin_name: Name of the pin (e.g., "DIN1")
        
    Returns:
        Full pin name (e.g., "U1.DIN1")
    """
    return f"{cell_name}.{pin_name}"