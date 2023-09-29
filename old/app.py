import folium
import random
import time
import streamlit as st
import requests
import folium
from folium import plugins, branca
from streamlit_folium import st_folium
import leafmap.foliumap as leafmap
import geopandas
from IPython.display import display, HTML
import base64
from folium import IFrame

# Create a map instance
m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

# Create a marker with initial location
marker = folium.Marker([51.5074, -0.1278])
marker.add_to(m)

# Function to update the marker's location
def update_marker_location():
    lat = random.uniform(51.5, 51.6)
    lon = random.uniform(-0.2, -0.1)
    marker.location = [lat, lon]

# Update the marker's location every second
#while True:
#    update_marker_location()
#    time.sleep(10)

# Display the map
m.to_streamlit(700, 600)