# config/config.py

import os

# Default file paths (adjust to your actual paths)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

SPECIES_DATA_CSV = os.path.join(DATA_DIR, "species_data.csv")
STOCKS_DATA_CSV = os.path.join(DATA_DIR, "stocks_data.csv")
AREA_DATA_CSV = os.path.join(DATA_DIR, "areas_data.csv")
REGION_TOP30_CSV = os.path.join(DATA_DIR, "region_data_top30.csv")
REGION_TOP60_CSV = os.path.join(DATA_DIR, "region_data_top60.csv")
GEOJSON_FILE = os.path.join(DATA_DIR, "state_biome.geojson")

# Default parameters
DEFAULT_TARGET_DENSITY = 250000.0
DEFAULT_CHUNK_SIZE = 30
DEFAULT_SUPPLIERS = ["supplier_top"]
