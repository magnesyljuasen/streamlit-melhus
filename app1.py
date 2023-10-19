# https://leafmap.org/notebooks/01_leafmap_intro/
import streamlit as st
import leafmap.deck as leafmap
import geopandas as gpd
import pandas as pd

initial_view_state = {
    "latitude": 63.3124,
    "longitude": 10.3057,
    "zoom": 10,
    "pitch": 45,
    "bearing": 10,
}

m = leafmap.Map(initial_view_state=initial_view_state)
m.add_basemap("HYBRID")

#filename = ("https://github.com/giswqs/streamlit-geospatial/raw/master/data/us_states.geojson")
#m.add_vector(filename, random_color_column="STATEFP", pickable = True)


#gdf = gpd.read_file("https://github.com/giswqs/streamlit-geospatial/raw/master/data/us_counties.geojson")
#m.add_gdf(gdf, random_color_column="STATEFP")

data = {
    'Name': ['Point A', 'Point B', 'Point C'],
    'Latitude': [63.28555, 63.28655, 63.28455],
    'Longitude': [10.27806, 10.27806, 10.27806],
    'ALAND' : [1000, 2000, 3000]
}
#gdf = "https://github.com/giswqs/streamlit-geospatial/raw/master/data/us_states.geojson"
df = pd.DataFrame(data)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))
#gdf.to_file('output.geojson', driver='GeoJSON')

m.add_gdf(
    gdf, 
    random_color_column="Name",
    #extruded=True,
    #get_elevation="ALAND",
    #elevation_scale=1
    )

"""
m.add_vector(
    filename = gdf,
    random_color_column="ALAND",
    extruded=True,
    get_elevation="ALAND",
    elevation_scale=1
)
"""

st.pydeck_chart(pydeck_obj = m, use_container_width = True)

#--
import pandas as pd
import pydeck as pdk

DATA_URL = "https://raw.githubusercontent.com/ajduberstein/geo_datasets/master/housing.csv"
df = pd.read_csv(DATA_URL)
st.write(df)

view = pdk.data_utils.compute_view(df[["lng", "lat"]])
view.pitch = 75
view.bearing = 60

column_layer = pdk.Layer(
    "ColumnLayer",
    data=df,
    get_position=["lng", "lat"],
    get_elevation="price_per_unit_area",
    elevation_scale=100,
    radius=50,
    get_fill_color=["mrt_distance * 10", "mrt_distance", "mrt_distance * 10", 140],
    pickable=True,
    auto_highlight=True,
)

tooltip = {
    "html": "<b>{mrt_distance}</b> meters away from an MRT station, costs <b>{price_per_unit_area}</b> NTD/sqm",
    "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"},
}

r = pdk.Deck(
    column_layer,
    initial_view_state=view,
    tooltip=tooltip,
    map_provider="mapbox",
    map_style=pdk.map_styles.SATELLITE,
)
st.pydeck_chart(r)