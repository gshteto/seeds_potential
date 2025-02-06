import streamlit as st
import pandas as pd

from config import config
from core.data_processing import (
    load_and_compute_kg_per_ha,
    load_stocks_data,
    combine_suppliers,
    merge_stock_and_kg_per_ha,
    load_area_data,
    distribute_stock,
    compute_threshold_factor,
    compute_species_count
)
from core.map_utils import build_choropleth_map

def main():
    st.title("Seeds Potential per State and Biome")

    # --------------------------
    # 1) Widget Controls
    # --------------------------
    # 1) First Row: Region + Suppliers
    col_region, col_suppliers = st.columns([1, 1.5])
    with col_region:
        st.subheader("Target Species")
        region_choice = st.radio(
            "Pick target species:",
            ("Top 30", "Top 60"),
            index=0
        )
        if region_choice == "Top 30":
            region_csv_path = config.REGION_TOP30_CSV
        else:
            region_csv_path = config.REGION_TOP60_CSV

    with col_suppliers:
        st.subheader("Suppliers")
        supplier_options = ["supplier_top", "supplier_2ry", "pilot_top", "pilot_2ry"]
        chosen_suppliers = st.multiselect(
            "Select suppliers to use:",
            supplier_options,
            default=config.DEFAULT_SUPPLIERS
        )

    # 2) Second Row: Distribution + Target Density + Threshold
    col_dist, col_density, col_threshold = st.columns([1.2, 1, 1])
    with col_dist:
        st.subheader("Distribution")
        use_species_count = st.checkbox("Divide by species count?", value=False)

        # Single checkbox: do we want to distribute by area at all?
        distribute_area = st.checkbox("Distribute through surface area?", value=False)
        
        # If user checks "Distribute through surface area?", 
        # show a radio to pick which area column: "Area" or "Potential"
        area_method = None
        if distribute_area:
            area_method = st.radio("Area column:", ["Total state areas", "Potential reforestation areas"], index=0)

    with col_density:
        st.subheader("Target seeding density")
        target_density = st.number_input(
            "Seeds/ha:",
            value=config.DEFAULT_TARGET_DENSITY,
            min_value=0.0,
            step=1000.0
        )

    with col_threshold:
        st.subheader("Species threshold")
        n_species = st.number_input(
            "Top N species:",
            value=20,
            min_value=1,
            step=1
        )


    # --------------------------
    # 2) Data Pipeline Execution (auto-runs on every widget change)
    # --------------------------
    # (a) Load species data & compute kg/ha
    df_species_req = load_and_compute_kg_per_ha(
        config.SPECIES_DATA_CSV,
        target_density,
        chunk_size=config.DEFAULT_CHUNK_SIZE
    )

    # (b) Load & combine stocks
    df_stocks = load_stocks_data(config.STOCKS_DATA_CSV)
    df_stocks_combined = combine_suppliers(df_stocks, chosen_suppliers)
    df_merged = merge_stock_and_kg_per_ha(df_species_req, df_stocks_combined)

    # (c) region data + area => merged
    df_region = pd.read_csv(region_csv_path, sep=",")
    df_area = load_area_data(config.AREA_DATA_CSV)
    df_region_areas = pd.merge(df_region, df_area, on='regionkey', how='left')

    # --------------------------
    # Decide how to distribute based on user choices
    # --------------------------
    if distribute_area:
        use_relative_area = True  # we do want area-based distribution
        # If user picked "Potential", then we use area_potential
        use_area_potential = (area_method == "Potential reforestation areas")
    else:
        use_relative_area = False
        use_area_potential = False

    # --------------------------
    # 3) Distribute
    # --------------------------
    df_distributed = distribute_stock(
        df_merged,
        df_region_areas,
        use_species_count=use_species_count,
        use_relative_area=use_relative_area,
        use_area_potential=use_area_potential
    )

    # --------------------------
    # 4) Compute threshold, species counts, final df
    # --------------------------
    df_threshold = compute_threshold_factor(df_distributed, n_species=n_species)
    df_count = compute_species_count(df_distributed)

    df_map = pd.merge(df_threshold, df_count, on='regionkey', how='left')
    # columns: [regionkey, Threshold_ha, NumSpeciesUsed, species_count]

    # --------------------------
    # 5) Display Table in Real Time
    # --------------------------
    st.subheader("Results table")
    st.dataframe(df_map.head(30))

    # --------------------------
    # 6) On-Demand Map Generation
    # --------------------------
    if st.button("Show Map"):
        st.subheader("Map: Colored by Number of Plantable Species per Biome")
        deck = build_choropleth_map(config.GEOJSON_FILE, df_map)
        st.pydeck_chart(deck)

if __name__ == "__main__":
    main()
