# core/map_utils.py

import json
import pydeck as pdk

def color_scale(val, min_val, max_val):
    """
    Red->Green scale. val=NaN => Gray.
    """
    if val is None:
        return [200, 200, 200]
    if max_val == min_val:
        return [0, 255, 0]
    ratio = (val - min_val) / (max_val - min_val)
    r = int(255 * (1 - ratio))
    g = int(255 * ratio)
    return [r, g, 0]

def build_choropleth_map(geojson_path: str, df_map):
    """
    df_map has columns:
      - regionkey
      - species_count
      - Threshold_ha
    We'll color polygons by species_count,
    and label them with rounded threshold in the tooltip.
    """
    with open(geojson_path, "r") as f:
        geojson_data = json.load(f)

    # 1) min/max for species_count
    min_count = df_map['species_count'].min()
    max_count = df_map['species_count'].max()

    # 2) lookups
    count_dict = dict(zip(df_map['regionkey'], df_map['species_count']))
    th_dict = dict(zip(df_map['regionkey'], df_map['Threshold_ha']))

    # 3) update each feature's properties
    for feature in geojson_data["features"]:
        props = feature["properties"]
        rk = props["regionkey"]

        sc_val = count_dict.get(rk, None)
        fill_c = color_scale(sc_val, min_count, max_count)
        props["fill_color"] = fill_c

        th_val = th_dict.get(rk, None)
        props["threshold_ha"] = round(th_val, 1) if th_val is not None else None

         # Add species_count to properties for tooltip
        props["species_count"] = sc_val if sc_val is not None else "N/A"


    layer = pdk.Layer(
        "GeoJsonLayer",
        geojson_data,
        pickable=True,
        get_fill_color="properties.fill_color",
        get_line_color=[0, 0, 0],
        line_width_min_pixels=1,
        auto_highlight=True
    )

    tooltip = {
        "html": "<b>regionkey:</b> {regionkey}<br/>"
                "<b>Threshold_ha:</b> {threshold_ha}<br/>"
                "<b>Plantable species:</b> {species_count}",
        "style": {"backgroundColor": "white", "color": "black"}
    }

    view_state = pdk.ViewState(latitude=-14.2350, longitude=-51.9253, zoom=4)
    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
    return deck
