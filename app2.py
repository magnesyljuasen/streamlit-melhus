import os
import requests
from time import time
from jose import jwt
from cognite.client import ClientConfig, CogniteClient
from cognite.client.credentials import Token
from bs4 import BeautifulSoup
from pathlib import Path
import base64
import folium
from folium.plugins import HeatMapWithTime
from streamlit_folium import st_folium
import imageio as iio
import numpy as np
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_extras.chart_container import chart_container
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import pandas as pd
from streamlit_autorefresh import st_autorefresh




def streamlit_settings():
    st.set_page_config(
        page_title="Case Melhus",
        page_icon="📟",
        layout="wide",
        initial_sidebar_state="collapsed")

    with open("src/styles/main.css") as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

    #count = st_autorefresh(interval=5 * 60 * 1000, limit=100, key="fizzbuzzcounter")
    hide_img_fs = '''
        <style>
        button[title="View fullscreen"]{
            visibility: hidden;}
        </style>
        '''
    st.markdown(hide_img_fs, unsafe_allow_html=True)

class Properate:
    def __init__(self, ID = "AH_7224_Gammelbakkan_15"):
        self.ID = ID
        self.authentication()
        
    def token_expired(self, token):
        header = jwt.get_unverified_claims(token)
        exp = header.get("exp")
        if not exp:
            return True
        exp = int(exp)
        # Renew if token has less than 2 min lifetime left
        remaining = exp - time()
        return remaining < 120

    def request_token(self):
        parameters = {
            "client_id": self.client_name,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        headers = {
            "content-type": "application/x-www-form-urlencoded"
        }
        url =  "%s/realms/%s/%s" % (self.server_url, self.realm[self.project], "protocol/openid-connect/token")
        resp = requests.post(url, data=parameters, headers=headers)
        result = resp.json()
        return result.get("access_token")

    def token(self):
        #global self._last_token
        if self._last_token is None or self.token_expired(self._last_token):
            self._last_token = self.request_token()
        return self._last_token

    def authentication(self):
        self.project = "energima"
        self.server_url = "https://auth.properate.com"
        self.realm = {"energima": "prod", "energima-dev": "dev", "energima-test": "test"}
        self._last_token = None

        self.client_name="asplan_viak"
        self.client_secret = "xdevIMhUEpqWjGxjzELJ0Xfof8QVfktx"

        cdf_client_name = os.environ.get(self.ID, self.client_name)
        cfg = ClientConfig(client_name=cdf_client_name, project=self.project, credentials=Token(self.token))
        self.cdf = CogniteClient(cfg)
        self.external_id_list = self.cdf.time_series.list().to_pandas()["external_id"]

    def get_timeseries(self, external_id):
        series = self.cdf.time_series.data.retrieve(external_id=external_id).to_pandas()
        metadata = self.cdf.time_series.retrieve(external_id=external_id).to_pandas().T
        return series, metadata
    
    def show_all_timeseries(self):
        external_id_list = self.external_id_list
        for i in range(0, len(external_id_list)):
            st.write(f"**{external_id_list[i]}**")
            df, metadata = self.get_timeseries(external_id_list[i])
            st.write(metadata)
            st.line_chart(df.to_numpy())
            st.markdown("---")

def plot_percentages(x, y):
    fig = px.line(x=x, y=y)
    fig.update_traces(line_color='#1d3c34')
    fig.update_layout(xaxis_title="Tid", yaxis_title="Prosent [%]")
    fig["data"][0]["showlegend"] = False
    fig.update_layout(
    margin=dict(l=50,r=50,b=10,t=10,pad=0),
    yaxis_title="Prosent [%]",
    legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)")
    )

    fig.update_xaxes(
        ticks="outside",
        linecolor="black",
        gridcolor="lightgrey",
    )
    fig.update_yaxes(
        range=[0,100],
        ticks="outside",
        linecolor="black",
        gridcolor="lightgrey",
    )
    st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False,})# 'staticPlot': True})

def plot_kpa(x, y):
    fig = px.line(x=x, y=y)
    fig.update_traces(line_color='#1d3c34')
    fig.update_layout(xaxis_title="Tid", yaxis_title="Prosent [%]")
    fig["data"][0]["showlegend"] = False
    fig.update_layout(
    margin=dict(l=50,r=50,b=10,t=10,pad=0),
    yaxis_title="kPa",
    legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0)")
    )

    fig.update_xaxes(
        ticks="outside",
        linecolor="black",
        gridcolor="lightgrey",
    )
    fig.update_yaxes(
        #range=[0,100],
        ticks="outside",
        linecolor="black",
        gridcolor="lightgrey",
    )
    st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False,})# 'staticPlot': True})

def kpa_to_percentage(kpa):
    x0, y0 = 10, 100
    x1, y1 = 30, 0
    a = (y1 - y0) / (x1 - x0)
    if kpa <= 10:
        percentage = 100
    elif kpa >= 30:
        percentage = 0
    else:
        percentage = int(a * (kpa - 10) + 100)
    return percentage

def kpa_to_percent(df):
    array = df.to_numpy()
    kpa_array = array / 1000
    
    percentage_values = []
    for kpa in kpa_array:
        percentage = kpa_to_percentage(kpa)
        percentage_values.append(percentage)
    return percentage_values

def plot_gauge(value, text):
    if text == "Helsetilstand":
        gauge_range = {
            'axis' : {'range': [None, 100]},
            'steps' : [
                {'range' : [0, 50], 'color' : 'lightgray'},
                {'range' : [50, 100], 'color' : 'gray'}
            ],
            }
    else:
        gauge_range = {
            'axis' : {'range': [None, 50000]}
            }
    fig = go.Figure(go.Indicator(
        domain = {'x': [0, 1], 'y': [0, 1]},
        mode = "gauge+number",
        value = value,
        gauge = gauge_range,
        title = {'text': text}))

    st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False,})# 'staticPlot': True})

def varmeveksler(df, series_name):
    st.write(f"**{series_name}**")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Siste verdi")
        last_pa_value = int(df.to_numpy()[-1])
        tab1, tab2 = st.tabs(["Helsetilstand", "Trykkdifferanse"])
        with tab1:
            last_kpa_value = kpa_to_percentage(last_pa_value/1000)
            plot_gauge(value = last_kpa_value, text = "Helsetilstand")
        with tab2:
            plot_gauge(value = last_pa_value, text = "Trykkdifferanse")
    with c2:
        st.subheader("Historikk")
        tab1, tab2 = st.tabs(["Helsetilstand", "Trykkdifferanse"])
        with tab1:
            percentage_values = kpa_to_percent(df)
            plot_percentages(x = df.index.values, y = percentage_values)
        with tab2:
            y = df[series_name].to_numpy()
            plot_kpa(x = df.index.values, y = y)
    return last_kpa_value

def get_last_week(time_series, properate):
    df, metadata = properate.get_timeseries(time_series)
    return df.to_numpy()[-(24 * 7):], df, metadata

def show_pydeck_map(df):
    view = pdk.data_utils.compute_view(df[["lng", "lat"]])
    view.pitch = 45
    view.bearing = 10
    view.zoom = 14
    
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["lng", "lat"],
        get_elevation="verdi_fornybar_energi",
        elevation_scale=0.0001,
        radius=10,
        get_fill_color=["255/verdi_fornybar_energi", 255, 0],
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": "Fornybar energi produsert hittil er verdt {verdi_fornybar_energi} kr",
        "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial', "z-index": "10000"},
    }

    r = pdk.Deck(
        column_layer,
        initial_view_state=view,
        tooltip=tooltip,
        map_provider="mapbox",
        map_style=None
        #map_style=pdk.map_styles.SATELLITE,
    )
    
    return r


if __name__ == "__main__":
    # update every 5 mins
    st_autorefresh(interval=1 * 15 * 1000, key="dataframerefresh")
    properate = Properate(ID = "AH_7224_Gammelbakkan_15")
    time_series_gshp = "TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001"
    df_gshp, metadata = properate.get_timeseries(time_series_gshp)
    
    time_series_solar = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001"
    df_solar, metadata = properate.get_timeseries(time_series_solar)
    
    total_value = int(np.sum(df_gshp.to_numpy()) + np.sum(df_solar.to_numpy()))
    df = pd.DataFrame({
        "id" : ["Bankhallen"],
        "lat" : [63.284776],
        "lng" : [10.265611],
        "verdi_fornybar_energi" : [total_value],
        "verdi_sol" : [int(np.sum(df_solar.to_numpy()))],
        "verdi_grunnvarme" : [int(np.sum(df_gshp.to_numpy()))]
    })
    r = show_pydeck_map(df = df)
    
    st.pydeck_chart(pydeck_obj = r, use_container_width = True)