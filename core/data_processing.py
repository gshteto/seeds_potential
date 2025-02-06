# core/data_processing.py

import pandas as pd

def clean_number(num_str: str) -> float:
    """Cleans a numeric string with commas, spaces, etc. and returns float."""
    if pd.isna(num_str):
        return float('nan')
    num_str = (
        num_str.replace('\u202f', '')
               .replace('\u00a0', '')
               .replace(' ', '')
               .replace(',', '.')
               .replace(' ', '')
    )
    return float(num_str)

def get_weight(seeds_per_kg: float) -> float:
    """Piecewise function for computing weight based on Seeds/kg."""
    if seeds_per_kg <= 0:
        return 0.0
    elif seeds_per_kg <= 500:
        return 0.5
    elif seeds_per_kg <= 2000:
        return 1.0
    elif seeds_per_kg <= 5000:
        return 2.0
    elif seeds_per_kg <= 10000:
        return 4.0
    elif seeds_per_kg <= 20000:
        return 8.0
    elif seeds_per_kg <= 80000:
        return 10.0
    elif seeds_per_kg <= 200000:
        return 12.0
    else:
        return 14.0

def load_and_compute_kg_per_ha(species_csv: str, target_density: float, chunk_size: int = 30) -> pd.DataFrame:
    df = pd.read_csv(species_csv, sep=",")
    
    # Clean numeric columns
    df['Seeds/kg'] = df['Seeds/kg'].astype(str).apply(clean_number)
    df['Germination Rate (%)'] = df['Germination Rate (%)'].astype(str).apply(clean_number)
    df['chunk_index'] = df.index // chunk_size

    # Weight
    df['Weight'] = df['Seeds/kg'].apply(get_weight)
    df['sum_of_weights'] = df.groupby('chunk_index')['Weight'].transform('sum')

    # Seeds/ha
    df['Seeds/ha'] = (
        target_density
        / df['sum_of_weights']
        * df['Weight']
        / df['Germination Rate (%)']
    )

    # kg/ha
    df['kg/ha'] = df['Seeds/ha'] / df['Seeds/kg']
    return df

def load_stocks_data(stocks_csv: str) -> pd.DataFrame:
    df = pd.read_csv(stocks_csv, sep=",")
    df['Total_MORFO_Supply_Kg'] = df['Total_MORFO_Supply_Kg'].astype(str).apply(clean_number)
    return df

def combine_suppliers(df_stocks: pd.DataFrame, chosen_suppliers: list) -> pd.DataFrame:
    df_filtered = df_stocks[df_stocks['Supply_Type'].isin(chosen_suppliers)].copy()
    df_grouped = df_filtered.groupby('Specie', as_index=False)['Total_MORFO_Supply_Kg'].sum()
    df_grouped.rename(columns={'Total_MORFO_Supply_Kg': 'Combined_Stock'}, inplace=True)
    return df_grouped

def merge_stock_and_kg_per_ha(df_species_req: pd.DataFrame, df_stock_combined: pd.DataFrame) -> pd.DataFrame:
    df_sreq_renamed = df_species_req.rename(columns={'Species': 'Specie'})
    df_merged = pd.merge(df_sreq_renamed, df_stock_combined, on='Specie', how='left')
    return df_merged

def load_area_data(area_csv: str) -> pd.DataFrame:
    df = pd.read_csv(area_csv, sep=",")
    df['Area'] = df['Area'].astype(str).apply(clean_number)
    return df

def distribute_stock(df_merged: pd.DataFrame,
                     df_region_areas: pd.DataFrame,
                     use_species_count: bool = True,
                     use_relative_area: bool = True) -> pd.DataFrame:
    df_dist = pd.merge(df_region_areas, df_merged, on='Specie', how='left')

    grp = df_dist.groupby('Specie', as_index=False).agg({
        'STATE': 'count',
        'Area': 'sum'
    })
    grp.rename(columns={'STATE': 'CountAppearances', 'Area': 'SumArea'}, inplace=True)
    df_dist = pd.merge(df_dist, grp, on='Specie', how='left')

    df_dist['Combined_Stock'] = df_dist['Combined_Stock'].fillna(0)
    df_dist['allocated_stock'] = df_dist['Combined_Stock']

    if use_species_count:
        df_dist['allocated_stock'] = df_dist['allocated_stock'] / df_dist['CountAppearances']
    if use_relative_area:
        df_dist['allocated_stock'] = df_dist['allocated_stock'] * (df_dist['Area'] / df_dist['SumArea'])

    df_dist['Possible_ha_distributed'] = df_dist['allocated_stock'] / df_dist['kg/ha']
    return df_dist

def compute_threshold_factor(df_distributed: pd.DataFrame, n_species: int = 5) -> pd.DataFrame:
    df_valid = df_distributed.dropna(subset=['Possible_ha_distributed']).copy()
    df_valid = df_valid[df_valid['Possible_ha_distributed'] > 0]

    df_valid.sort_values(['regionkey', 'Possible_ha_distributed'],
                         ascending=[True, False],
                         inplace=True)

    def pick_top_n(group):
        return group.head(n_species)

    df_top_n = df_valid.groupby('regionkey', as_index=False).apply(pick_top_n)
    df_min = df_top_n.groupby('regionkey', as_index=False)['Possible_ha_distributed'].min()
    df_min.rename(columns={'Possible_ha_distributed': 'Threshold_ha'}, inplace=True)
    df_min['NumSpeciesUsed'] = n_species
    return df_min

def compute_species_count(df_distributed: pd.DataFrame) -> pd.DataFrame:
    """For each regionkey, compute how many unique species appear."""
    df_count = df_distributed.groupby('regionkey')['Specie'].nunique().reset_index()
    df_count.rename(columns={'Specie': 'species_count'}, inplace=True)
    return df_count
