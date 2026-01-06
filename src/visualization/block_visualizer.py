"""
Netlist Block Visualizer

Visualize netlist blocks as directed graphs to understand:
- Local topology around components
- Hierarchical structure (logic levels)
- Differences between Normal vs Trojan blocks
"""

import os
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("Warning: networkx not installed. Install with: pip install networkx")

# ==========================================
# FIX: Use full path starting with src
# ==========================================
from src.extraction.netlist_block import NetlistBlock
from src.graph.netlist_graph import PinLevelGraph


class BlockVisualizer:
    """
    Visualize netlist blocks as directed graphs 
    
    Shows:
    - Center component
    - Input side (backward BFS)
    - Output side (forward BFS)
    - Hierarchical levels
    """
    
    def __init__(self, graph: PinLevelGraph):
        """
        Initialize visualizer
        
        Args:
            graph: Pin-level graph (for getting component details)
        """
        if not HAS_NETWORKX:
            raise ImportError("networkx is required for visualization. Install with: pip install networkx")
        
        self.graph = graph
    
    def visualize_block(self, block: NetlistBlock, output_path: str,
                        title: Optional[str] = None, show_nets: bool = True):
        """
        Visualize a single netlist block
        
        Args:
            block: NetlistBlock to visualize
            output_path: Path to save the visualization
            title: Optional title for the plot
            show_nets: Whether to show net names on edges
        """
        # Create directed graph
        G = nx.DiGraph()
        
        # Add center node
        center = f"{block.center_cell}\n({block.center_cell_type})"
        G.add_node(center, level='center', node_type='center')
        
        # Track unique nets and their positions
        net_nodes = set()
        
        # Add input side
        for pin_idx, path in enumerate(block.input_side):
            pin_label = f"IN{pin_idx}"
            G.add_node(pin_label, level='center', node_type='pin')
            G.add_edge(pin_label, center)
            
            for level_idx, nets in enumerate(path):
                for net in nets:
                    if net not in net_nodes:
                        G.add_node(net, level=f'input-{level_idx}', node_type='net')
                        net_nodes.add(net)
                    
                    # Connect: net → previous level (or pin if level 0)
                    if level_idx == 0:
                        G.add_edge(net, pin_label)
                    # For deeper levels, nets connect to other nets
        
        # Add output side
        for pin_idx, path in enumerate(block.output_side):
            pin_label = f"OUT{pin_idx}"
            G.add_node(pin_label, level='center', node_type='pin')
            G.add_edge(center, pin_label)
            
            for level_idx, nets in enumerate(path):
                for net in nets:
                    if net not in net_nodes:
                        G.add_node(net, level=f'output-{level_idx}', node_type='net')
                        net_nodes.add(net)
                    
                    # Connect: previous level → net
                    if level_idx == 0:
                        G.add_edge(pin_label, net)
        
        # Layout
        pos = self._hierarchical_layout(G, block)
        
        # Draw
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Node colors
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            node_type = G.nodes[node].get('node_type', 'net')
            if node_type == 'center':
                node_colors.append('#FF6B6B')  # Red for center
                node_sizes.append(3000)
            elif node_type == 'pin':
                node_colors.append('#4ECDC4')  # Teal for pins
                node_sizes.append(1500)
            else:
                node_colors.append('#95E1D3')  # Light green for nets
                node_sizes.append(1000)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_sizes, alpha=0.9, ax=ax)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, edge_color='gray', 
                              arrows=True, arrowsize=15, 
                              width=1.5, alpha=0.6, ax=ax,
                              arrowstyle='->', connectionstyle='arc3,rad=0.1')
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold', ax=ax)
        
        # Title
        if title is None:
            title = f"Netlist Block: {block.center_cell} ({block.center_cell_type})\nLogic Level: {block.logic_level}"
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend
        legend_elements = [
            mpatches.Patch(color='#FF6B6B', label='Center Component'),
            mpatches.Patch(color='#4ECDC4', label='I/O Pins'),
            mpatches.Patch(color='#95E1D3', label='Nets (Signals)')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        
        ax.axis('off')
        plt.tight_layout()
        
        # Save
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Visualization saved: {output_path}")
    
    def _hierarchical_layout(self, G: nx.DiGraph, block: NetlistBlock) -> Dict:
        """
        Create hierarchical layout for the graph
        
        Args:
            G: NetworkX graph
            block: NetlistBlock
            
        Returns:
            Dictionary of node positions
        """
        pos = {}
        
        # Center component
        center = f"{block.center_cell}\n({block.center_cell_type})"
        pos[center] = (0, 0)
        
        # Input pins (left side)
        num_input_pins = len(block.input_side)
        for i in range(num_input_pins):
            pin_label = f"IN{i}"
            y = (i - (num_input_pins - 1) / 2) * 0.5
            pos[pin_label] = (-1.5, y)
        
        # Output pins (right side)
        num_output_pins = len(block.output_side)
        for i in range(num_output_pins):
            pin_label = f"OUT{i}"
            y = (i - (num_output_pins - 1) / 2) * 0.5
            pos[pin_label] = (1.5, y)
        
        # Collect nets by level
        input_nets_by_level = {}
        output_nets_by_level = {}
        
        for pin_idx, path in enumerate(block.input_side):
            for level_idx, nets in enumerate(path):
                if level_idx not in input_nets_by_level:
                    input_nets_by_level[level_idx] = []
                input_nets_by_level[level_idx].extend(nets)
        
        for pin_idx, path in enumerate(block.output_side):
            for level_idx, nets in enumerate(path):
                if level_idx not in output_nets_by_level:
                    output_nets_by_level[level_idx] = []
                output_nets_by_level[level_idx].extend(nets)
        
        # Position input nets
        for level_idx, nets in input_nets_by_level.items():
            x = -3.0 - level_idx * 2.0
            unique_nets = list(set(nets))
            for i, net in enumerate(unique_nets):
                y = (i - (len(unique_nets) - 1) / 2) * 0.8
                pos[net] = (x, y)
        
        # Position output nets
        for level_idx, nets in output_nets_by_level.items():
            x = 3.0 + level_idx * 2.0
            unique_nets = list(set(nets))
            for i, net in enumerate(unique_nets):
                y = (i - (len(unique_nets) - 1) / 2) * 0.8
                pos[net] = (x, y)
        
        return pos
    
    def compare_blocks(self, normal_block: NetlistBlock, trojan_block: NetlistBlock,
                       output_path: str):
        """
        Create side-by-side comparison of Normal vs Trojan block
        
        Args:
            normal_block: Normal component block
            trojan_block: Trojan component block
            output_path: Path to save comparison
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        
        # Visualize normal block
        self._visualize_block_on_axis(normal_block, ax1, "Normal Component")
        
        # Visualize trojan block
        self._visualize_block_on_axis(trojan_block, ax2, "Trojan Component")
        
        plt.suptitle("Normal vs Trojan Block Comparison", 
                    fontsize=16, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Comparison saved: {output_path}")
    
    def _visualize_block_on_axis(self, block: NetlistBlock, ax, title: str):
        """Helper to visualize block on a specific axis"""
        # Create graph
        G = nx.DiGraph()
        center = f"{block.center_cell}\n({block.center_cell_type})"
        G.add_node(center, node_type='center')
        
        net_nodes = set()
        
        # Add input side (simplified)
        for pin_idx, path in enumerate(block.input_side):
            pin_label = f"IN{pin_idx}"
            G.add_node(pin_label, node_type='pin')
            G.add_edge(pin_label, center)
            
            # Just show first level nets
            if path and path[0]:
                for net in path[0][:3]:  # Max 3 nets
                    if net not in net_nodes:
                        G.add_node(net, node_type='net')
                        net_nodes.add(net)
                    G.add_edge(net, pin_label)
        
        # Add output side (simplified)
        for pin_idx, path in enumerate(block.output_side):
            pin_label = f"OUT{pin_idx}"
            G.add_node(pin_label, node_type='pin')
            G.add_edge(center, pin_label)
            
            # Just show first level nets
            if path and path[0]:
                for net in path[0][:3]:  # Max 3 nets
                    if net not in net_nodes:
                        G.add_node(net, node_type='net')
                        net_nodes.add(net)
                    G.add_edge(pin_label, net)
        
        # Layout and draw
        pos = self._hierarchical_layout(G, block)
        
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            node_type = G.nodes[node].get('node_type', 'net')
            if node_type == 'center':
                node_colors.append('#FF6B6B')
                node_sizes.append(2000)
            elif node_type == 'pin':
                node_colors.append('#4ECDC4')
                node_sizes.append(1000)
            else:
                node_colors.append('#95E1D3')
                node_sizes.append(700)
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                              node_size=node_sizes, alpha=0.9, ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='gray',
                              arrows=True, arrowsize=12, width=1.5, 
                              alpha=0.6, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=7, font_weight='bold', ax=ax)
        
        ax.set_title(f"{title}\n{block.center_cell} ({block.center_cell_type})",
                    fontsize=12, fontweight='bold')
        ax.axis('off')


def visualize_sample_blocks(blocks: Dict[str, NetlistBlock], 
                            labels: Optional[Dict],
                            graph: PinLevelGraph,
                            output_dir: str,
                            num_samples: int = 3):
    """
    Visualize sample normal and trojan blocks
    
    Args:
        blocks: Dictionary of all blocks
        labels: Label data (with trojan_components)
        graph: Pin-level graph
        output_dir: Directory to save visualizations
        num_samples: Number of samples to visualize
    """
    if not HAS_NETWORKX:
        print("Skipping visualization: networkx not installed")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    visualizer = BlockVisualizer(graph)
    
    print(f"\nGenerating visualizations...")
    
    # Visualize normal blocks
    normal_count = 0
    for cell_name, block in blocks.items():
        if labels and cell_name in labels['trojan_components']:
            continue
        
        if normal_count < num_samples:
            output_path = os.path.join(output_dir, f"normal_{cell_name}.png")
            visualizer.visualize_block(block, output_path, 
                                      title=f"Normal Component: {cell_name}")
            normal_count += 1
    
    # Visualize trojan blocks
    if labels:
        trojan_count = 0
        for cell_name in labels['trojan_components']:
            if cell_name in blocks and trojan_count < num_samples:
                output_path = os.path.join(output_dir, f"trojan_{cell_name}.png")
                visualizer.visualize_block(blocks[cell_name], output_path,
                                         title=f"Trojan Component: {cell_name}")
                trojan_count += 1
        
        # Create comparison
        if normal_count > 0 and trojan_count > 0:
            normal_name = [n for n in blocks.keys() 
                          if n not in labels['trojan_components']][0]
            trojan_name = labels['trojan_components'][0]
            
            if trojan_name in blocks:
                output_path = os.path.join(output_dir, "comparison_normal_vs_trojan.png")
                visualizer.compare_blocks(blocks[normal_name], blocks[trojan_name],
                                        output_path)
    
    print(f"✓ Visualizations saved to: {output_dir}")