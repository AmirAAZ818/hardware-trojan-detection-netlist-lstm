"""
Flexible PCP Trace Extraction with Checkpointing

Extracts PCP traces from Trust-Hub datasets with:
- Configurable benchmark/T-ID filtering  
- Checkpoint saving every N files
- Minimal logging for speed
- Accumulative statistics tracking

Based on existing TrustHubDatasetExtractor
"""

import sys
import os
from pathlib import Path
import json
from typing import List, Dict, Tuple
import time
from datetime import datetime

# Setup path
current_dir = Path(__file__).resolve().parent
project_root = current_dir
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import with CORRECT paths from your codebase
from src.parser.verilog_parser import VerilogParser
from src.parser.label_parser import LabelParser
from src.graph.graph_builder import GraphBuilder
from src.extraction.block_tree_extractor import BlockTreeExtractor
from src.traces.pcp_trace_generator import PCPTraceGenerator


class FlexibleTraceExtractor:
    """Flexible trace extraction with checkpointing and filtering"""
    
    def __init__(
        self,
        dataset_root: str,
        output_file: str = "combined_traces.txt",
        logic_level: int = 4,
        checkpoint_every: int = 50,
        verbose: bool = False
    ):
        self.dataset_root = Path(dataset_root)
        self.output_file = output_file
        self.logic_level = logic_level
        self.checkpoint_every = checkpoint_every
        self.verbose = verbose
        
        # Parsers and generators (reused)
        self.verilog_parser = VerilogParser()
        self.label_parser = LabelParser()  
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_components': 0,
            'total_traces': 0,
            'failed_files': [],
            'start_time': None,
            'checkpoints': []
        }
        
        # Setup logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"extraction_log_{timestamp}.txt"
        self.checkpoint_dir = Path("checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Initialize log file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"TRACE EXTRACTION LOG - {timestamp}\n")
            f.write(f"{'='*80}\n\n")
    
    def log(self, message: str, force: bool = False):
        """Log message to file and optionally to console"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
        
        if self.verbose or force:
            print(message)
    
    def find_verilog_files(
        self,
        datasets: List[str],
        benchmarks: List[str],
        t_id_ranges: Dict[str, List[Tuple[int, int]]]
    ) -> List[Tuple[Path, Path]]:
        """
        Find Verilog files matching the specified criteria
        
        Args:
            datasets: List of dataset names (e.g., ['TRIT-TC', 'TRIT-TS'])
            benchmarks: List of benchmark names (e.g., ['c2670', 'c3540'])
            t_id_ranges: Dict mapping dataset -> list of (start, end) T-ID ranges
        
        Returns:
            List of (netlist_path, label_path) tuples
        """
        verilog_files = []
        
        for dataset_name in datasets:
            dataset_path = self.dataset_root / dataset_name / dataset_name
            
            if not dataset_path.exists():
                self.log(f"Warning: Dataset not found: {dataset_path}", force=True)
                continue
            
            self.log(f"\nScanning dataset: {dataset_name}")
            
            # Get T-ID ranges for this dataset
            ranges = t_id_ranges.get(dataset_name, [])
            
            # Find all matching benchmark directories
            for benchmark in benchmarks:
                for start_id, end_id in ranges:
                    for t_id in range(start_id, end_id + 1):
                        folder_name = f"{benchmark}_T{t_id:03d}"
                        folder_path = dataset_path / folder_name
                        
                        if folder_path.exists():
                            verilog_file = folder_path / f"{folder_name}.v"
                            label_file = folder_path / "log.txt"
                            
                            if verilog_file.exists():
                                verilog_files.append((
                                    verilog_file,
                                    label_file if label_file.exists() else None
                                ))
            
            self.log(f"  Found {len(verilog_files)} files so far")
        
        return sorted(verilog_files, key=lambda x: x[0])
    
    def extract_traces_from_file(
        self, 
        netlist_path: Path, 
        label_path: Path = None
    ) -> Tuple[List[str], int, int]:
        """
        Extract traces from a single Verilog file
        
        Returns:
            (traces_list, num_components, num_trojans)
        """
        try:
            # Parse netlist
            netlist_data = self.verilog_parser.parse(str(netlist_path))
            num_components = len(netlist_data['components'])
            
            # Parse labels (resets per file automatically now!)
            num_trojans = 0
            if label_path and label_path.exists():
                labels = self.label_parser.parse(str(label_path))
                num_trojans = labels['num_trojans']
            
            # Build graph
            builder = GraphBuilder()
            graph = builder.build(netlist_data)
            
            # Extract block trees
            extractor = BlockTreeExtractor(graph, logic_level=self.logic_level)
            blocks = extractor.extract_all_blocks(verbose=False)
            
            # Generate PCP traces
            generator = PCPTraceGenerator(graph)
            generator.generate_all_traces(blocks, verbose=False)
            
            # Convert traces to strings
            traces_strings = [trace.to_string() for trace in generator.all_traces]
            
            return traces_strings, num_components, num_trojans
            
        except Exception as e:
            self.log(f"ERROR processing {netlist_path.name}: {e}")
            self.stats['failed_files'].append(str(netlist_path))
            return [], 0, 0
    
    def save_checkpoint(self, file_index: int, total_files: int):
        """Save checkpoint with current statistics"""
        checkpoint_data = {
            'file_index': file_index,
            'total_files': total_files,
            'progress_percent': (file_index / total_files * 100) if total_files > 0 else 0,
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats.copy(),
            'accumulative_label_stats': self.label_parser.get_accumulative_statistics()
        }
        
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{file_index:04d}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        self.stats['checkpoints'].append(str(checkpoint_file))
        self.log(f" Checkpoint saved: {checkpoint_file.name}", force=True)
    
    def extract_all(self, verilog_files: List[Tuple[Path, Path]]):
        """Extract traces from all files with checkpointing"""
        self.stats['start_time'] = time.time()
        total_files = len(verilog_files)
        
        # Clear output file
        open(self.output_file, 'w').close()
        
        self.log(f"\n{'='*80}", force=True)
        self.log(f"STARTING TRACE EXTRACTION", force=True)
        self.log(f"{'='*80}", force=True)
        self.log(f"Total files: {total_files}", force=True)
        self.log(f"Logic level: {self.logic_level}", force=True)
        self.log(f"Output: {self.output_file}", force=True)
        self.log(f"Checkpoints: Every {self.checkpoint_every} files", force=True)
        self.log(f"Log file: {self.log_file}", force=True)
        self.log(f"{'='*80}\n", force=True)
        
        # Open output file for appending
        with open(self.output_file, 'a', encoding='utf-8') as out_f:
            
            for i, (netlist_path, label_path) in enumerate(verilog_files, 1):
                # Minimal progress indicator
                if i % 10 == 0 or i == 1:
                    elapsed = time.time() - self.stats['start_time']
                    rate = self.stats['total_traces'] / max(1, elapsed)
                    print(f"[{i}/{total_files}] {netlist_path.name} | "
                          f"Traces: {self.stats['total_traces']:,} | "
                          f"Rate: {rate:.0f}/s", end='\r')
                
                self.log(f"[{i}/{total_files}] Processing: {netlist_path.name}")
                
                # Extract traces
                traces, num_comp, num_troj = self.extract_traces_from_file(
                    netlist_path, label_path
                )
                
                if traces:
                    # Write traces immediately
                    for trace in traces:
                        out_f.write(trace + '\n')
                    
                    # Update statistics
                    self.stats['files_processed'] += 1
                    self.stats['total_components'] += num_comp
                    self.stats['total_traces'] += len(traces)
                    
                    self.log(f"  Comp: {num_comp}, Troj: {num_troj}, Traces: {len(traces)}")
                else:
                    self.stats['files_failed'] += 1
                    self.log(f"  FAILED")
                
                # Checkpoint
                if i % self.checkpoint_every == 0:
                    self.save_checkpoint(i, total_files)
        
        # Final checkpoint
        print()  # New line after progress
        self.save_checkpoint(total_files, total_files)
        
        # Calculate elapsed time
        elapsed = time.time() - self.stats['start_time']
        self.stats['elapsed_time'] = elapsed
        
        # Final summary
        self.print_final_summary()
    
    def print_final_summary(self):
        """Print final extraction summary"""
        
        acc_stats = self.label_parser.get_accumulative_statistics()
        
        summary = f"""
{'='*80}
EXTRACTION COMPLETE
{'='*80}
Files processed: {self.stats['files_processed']}
Files failed: {self.stats['files_failed']}

Total components: {self.stats['total_components']:,}
Total traces: {self.stats['total_traces']:,}

Accumulative Label Statistics:
  Files with Trojans: {acc_stats['total_files_processed']}
  Total Trojan components: {acc_stats['total_trojan_components']}
  Avg Trojans per file: {acc_stats['avg_trojans_per_file']:.1f}

Elapsed time: {self.stats['elapsed_time']:.1f} seconds
Traces per second: {self.stats['total_traces'] / self.stats['elapsed_time']:.1f}

Output file: {self.output_file}
Log file: {self.log_file}
Checkpoints: {len(self.stats['checkpoints'])}
{'='*80}
"""
        self.log(summary, force=True)
        
        # Save final metadata
        metadata_file = self.output_file.replace('.txt', '_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump({
                'extraction_stats': self.stats,
                'label_stats': acc_stats,
                'logic_level': self.logic_level,
            }, f, indent=2)
        
        self.log(f"\nMetadata saved to: {metadata_file}", force=True)


def main():
    """Main extraction function with flexible configuration"""
    
    # ========================================================================
    # CONFIGURATION - MODIFY HERE FOR DIFFERENT EXTRACTION SCENARIOS
    # ========================================================================
    
    # Dataset root directory
    DATASET_ROOT = r"E:\University of Kerman\Term 9\VHDL\Datasets"
    
    # Output configuration
    OUTPUT_FILE = "vocabulary_traces_small.txt"
    LOGIC_LEVEL = 4
    CHECKPOINT_EVERY = 50
    VERBOSE = False  # Set to True for detailed logging
    
    # Datasets to include
    DATASETS = ['TRIT-TC']  # Only combinational for vocabulary
    
    # Benchmarks to include
    BENCHMARKS = ['c2670']  # First 3 benchmarks
    
    # T-ID ranges for each dataset
    T_ID_RANGES = {
        'TRIT-TC': [(0, 70)],  # T000-T070 only
    }
    
    # ========================================================================
    # SCENARIO 1: VOCABULARY EXTRACTION (Small subset for fast Word2Vec)
    # ========================================================================
    
    # # Datasets to include
    # DATASETS = ['TRIT-TC']  # Only combinational for vocabulary
    
    # # Benchmarks to include
    # BENCHMARKS = ['c2670', 'c3540', 'c5315']  # First 3 benchmarks
    
    # # T-ID ranges for each dataset
    # T_ID_RANGES = {
    #     'TRIT-TC': [(0, 99)],  # T000-T099 only
    # }
    
    # ========================================================================
    # SCENARIO 2: FULL EXTRACTION (Uncomment to use)
    # ========================================================================
    
    # DATASETS = ['TRIT-TC', 'TRIT-TS']  # Both datasets
    #
    # BENCHMARKS = ['c2670', 'c3540', 'c5315', 'c6288', 
    #               's1423', 's13207', 's15850', 's35932']  # All benchmarks
    #
    # T_ID_RANGES = {
    #     'TRIT-TC': [(0, 99), (200, 219)],     # Combinational
    #     'TRIT-TS': [(400, 489), (600, 619)]   # Sequential
    # }
    
    # ========================================================================
    # RUN EXTRACTION
    # ========================================================================
    
    print("\n" + "="*80)
    print("FLEXIBLE TRACE EXTRACTOR WITH CHECKPOINTING")
    print("="*80)
    print(f"\nDatasets: {', '.join(DATASETS)}")
    print(f"Benchmarks: {', '.join(BENCHMARKS)}")
    print(f"T-ID Ranges: {T_ID_RANGES}")
    print(f"Output: {OUTPUT_FILE}")
    print("="*80 + "\n")
    
    # Create extractor
    extractor = FlexibleTraceExtractor(
        dataset_root=DATASET_ROOT,
        output_file=OUTPUT_FILE,
        logic_level=LOGIC_LEVEL,
        checkpoint_every=CHECKPOINT_EVERY,
        verbose=VERBOSE
    )
    
    # Find files
    print("Finding Verilog files...")
    verilog_files = extractor.find_verilog_files(
        datasets=DATASETS,
        benchmarks=BENCHMARKS,
        t_id_ranges=T_ID_RANGES
    )
    
    if not verilog_files:
        print("ERROR: No Verilog files found!")
        return
    
    print(f"Found {len(verilog_files)} files\n")
    
    # Extract traces
    extractor.extract_all(verilog_files)
    
    print("\n✅ EXTRACTION COMPLETE!")
    print(f"   Traces: {OUTPUT_FILE}")
    print(f"   Log: {extractor.log_file}")
    print(f"   Checkpoints: {extractor.checkpoint_dir}/\n")


if __name__ == "__main__":
    main()