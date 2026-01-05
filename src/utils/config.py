"""
Configuration File for Hardware Trojan Detection Project

This file contains all paths and settings for the project.
Modify the paths below to match your setup.
"""

import os
from pathlib import Path

# ============================================================================
# PROJECT ROOT (automatically detected)
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SRC_DIR = PROJECT_ROOT / "src"

# ============================================================================
# DATA PATHS
# ============================================================================

# --- RAW DATA (Input files) ---
RAW_DATA_DIR = DATA_DIR / "raw"
NETLIST_DIR = RAW_DATA_DIR / "netlists"
LABEL_DIR = RAW_DATA_DIR / "labels"

# --- PROCESSED DATA (Output files) ---
PROCESSED_DIR = DATA_DIR / "processed"
GRAPHS_DIR = PROCESSED_DIR / "graphs"
PCP_TRACES_DIR = PROCESSED_DIR / "pcp_traces"

# ============================================================================
# DEFAULT FILES (Change these to your actual files!)
# ============================================================================

# Default netlist file - CHANGE THIS to your actual file
DEFAULT_NETLIST = NETLIST_DIR / "s15850_T436.v"
# Alternative: Use your Trust-Hub file
# DEFAULT_NETLIST = NETLIST_DIR / "s15850_T436.v"

# Default label file - CHANGE THIS to match your netlist
DEFAULT_LABEL = LABEL_DIR / "log.txt"
# Alternative: Use your Trust-Hub label file
# DEFAULT_LABEL = LABEL_DIR / "s15850_T436_log.txt"

# ============================================================================
# OUTPUT PATHS
# ============================================================================
LOGS_DIR = OUTPUT_DIR / "logs"
STATISTICS_DIR = OUTPUT_DIR / "statistics"
VISUALIZATIONS_DIR = OUTPUT_DIR / "visualizations"

# ============================================================================
# ALGORITHM PARAMETERS
# ============================================================================

# Step 3: Netlist Block Extraction
LOGIC_LEVEL = 4  # Default logic level (from paper)

# Step 5: Skip-gram Training (for future use)
EMBEDDING_DIM = 100  # PCP embedding dimension
WINDOW_SIZE = 2  # Skip-gram context window
NEGATIVE_SAMPLES = 5  # Negative sampling parameter
EPOCHS = 2  # Training epochs

# ============================================================================
# LOGGING SETTINGS
# ============================================================================
LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
ENABLE_PROGRESS_BAR = True
VERBOSE = True

# ============================================================================
# FILE FORMAT SETTINGS
# ============================================================================
OUTPUT_FORMAT = "json"  # Options: json, pickle
PRETTY_PRINT = True  # Pretty print JSON files

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ensure_directories():
    """Creating all necessary directories if they don't exist"""
    directories = [
        NETLIST_DIR,
        LABEL_DIR,
        PROCESSED_DIR,
        GRAPHS_DIR,
        PCP_TRACES_DIR,
        LOGS_DIR,
        STATISTICS_DIR,
        VISUALIZATIONS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_output_path(netlist_path, suffix="_parsed", extension=".json"):
    """
    Generate output path based on netlist filename
    
    Args:
        netlist_path: Path to the netlist file
        suffix: Suffix to add to filename
        extension: File extension for output
        
    Returns:
        Path to output file
    """
    netlist_name = Path(netlist_path).stem
    return PROCESSED_DIR / f"{netlist_name}{suffix}{extension}"


def validate_config():
    """Validate that required files exist"""
    issues = []
    
    if not DEFAULT_NETLIST.exists():
        issues.append(f"Default netlist not found: {DEFAULT_NETLIST}")
    
    if not DEFAULT_LABEL.exists():
        issues.append(f"Default label file not found: {DEFAULT_LABEL}")
    
    return issues


def print_config():
    """Print current configuration"""
    print("="*80)
    print("HARDWARE TROJAN DETECTION - CONFIGURATION")
    print("="*80)
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"\nDefault Files:")
    print(f"  Netlist: {DEFAULT_NETLIST}")
    print(f"  Labels:  {DEFAULT_LABEL}")
    print(f"\nData Directories:")
    print(f"  Netlists: {NETLIST_DIR}")
    print(f"  Labels:   {LABEL_DIR}")
    print(f"  Output:   {PROCESSED_DIR}")
    print(f"\nAlgorithm Parameters:")
    print(f"  Logic Level: {LOGIC_LEVEL}")
    print(f"  Embedding Dim: {EMBEDDING_DIM}")
    print("="*80)


# ============================================================================
# INITIALIZATION
# ============================================================================

# Create directories on import
ensure_directories()

# Check configuration (warnings only, doesn't stop execution)
config_issues = validate_config()
if config_issues:
    print("\n⚠️  Configuration Warnings:")
    for issue in config_issues:
        print(f"  - {issue}")
    print("\nℹ️  You can still run the tests by providing file paths as arguments.")
    print("   Or update DEFAULT_NETLIST and DEFAULT_LABEL in src/utils/config.py\n")