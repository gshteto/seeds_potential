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
    col1, col2 = st.columns(2)
    with col1:
        region_choice = st.radio(
            "Pick target species",
            ("Top 30", "Top 60"),
            index=0
        )
        if region_choice == "Top 30":
            region_csv_path = config.REGION_TOP30_CSV
        else:
            region_csv_path = config.REGION_TOP60_CSV

    with col2:
        supplier_options = ["supplier_top", "supplier_2ry", "pilot_top", "pilot_2ry"]
        chosen_suppliers = st.multiselect(
            "Suppliers to Use",
            supplier_options,
            default=config.DEFAULT_SUPPLIERS
        )

    col3, col4, col5 = st.columns(3)
    with col3:
        st.write("**Distribution**")
        use_species_count = st.checkbox("Divide by species count?", value=False)
        use_relative_area = st.checkbox("Use relative area?", value=False)

    with col4:
        st.write("**Target Density**")
        target_density = st.number_input(
            "Seeds/ha",
            value=config.DEFAULT_TARGET_DENSITY,
            min_value=0.0,
            step=1000.0
        )

    with col5:
        st.write("**Minimum species threshold for a project**")
        n_species = st.number_input(
            "Top N species",
            value=20,
            min_value=1,
            step=1
        )

    # --------------------------
    # 2) Data Pipeline Execution (auto-runs on every widget change)
    # --------------------------
    # 1) species data + kg/ha
    df_species_req = load_and_compute_kg_per_ha(
        config.SPECIES_DATA_CSV,
        target_density,
        chunk_size=config.DEFAULT_CHUNK_SIZE
    )

    # 2) stocks data => combine chosen
    df_stocks = load_stocks_data(config.STOCKS_DATA_CSV)
    df_stocks_combined = combine_suppliers(df_stocks, chosen_suppliers)
    df_merged = merge_stock_and_kg_per_ha(df_species_req, df_stocks_combined)

    # 3) region data + area => region_areas
    df_region = pd.read_csv(region_csv_path, sep=",")
    df_area = load_area_data(config.AREA_DATA_CSV)
    df_region_areas = pd.merge(df_region, df_area, on='regionkey', how='left')

    # 4) Distribute
    df_distributed = distribute_stock(
        df_merged,
        df_region_areas,
        use_species_count=use_species_count,
        use_relative_area=use_relative_area
    )

    # 5) Compute threshold
    df_threshold = compute_threshold_factor(df_distributed, n_species=n_species)
    # => [regionkey, Threshold_ha, NumSpeciesUsed]

    # 6) Compute species_count
    df_count = compute_species_count(df_distributed)
    # => [regionkey, species_count]

    # Merge them so each regionkey has both threshold & species_count
    df_map = pd.merge(df_threshold, df_count, on='regionkey', how='left')
    # => columns: [regionkey, Threshold_ha, NumSpeciesUsed, species_count]

    # --------------------------
    # 3) Display Table in Real Time
    # --------------------------
    st.subheader("Results table")
    st.dataframe(df_map.head(30))

    # --------------------------
    # 4) On-Demand Map Generation
    # --------------------------
    if st.button("Show Map"):
        st.subheader("Map: Colored by Number of Plantable Species per Biome")
        deck = build_choropleth_map(config.GEOJSON_FILE, df_map)
        st.pydeck_chart(deck)


if __name__ == "__main__":
    main()
