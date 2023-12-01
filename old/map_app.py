import os
import requests
from time import time
from jose import jwt
from cognite.client import ClientConfig, CogniteClient
from cognite.client.credentials import Token
from _map import Map
from bs4 import BeautifulSoup
from pathlib import Path
import base64
from folium import IFrame
import imageio as iio
import numpy as np

#--
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_extras.chart_container import chart_container
import plotly.express as px

st.set_page_config(
    page_title="Case Melhus",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="collapsed")

#with open("main.css") as f:
#    st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

#------- live count
count = st_autorefresh(interval=2 * 60 * 1000, limit=100, key="fizzbuzzcounter")

#-------
def token_expired(token):
    header = jwt.get_unverified_claims(token)
    exp = header.get("exp")
    if not exp:
        return True
    exp = int(exp)
    # Renew if token has less than 2 min lifetime left
    remaining = exp - time()
    return remaining < 120

def request_token():
    parameters = {
        "client_id": client_name,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }
    url =  "%s/realms/%s/%s" % (server_url, realm[project], "protocol/openid-connect/token")
    resp = requests.post(url, data=parameters, headers=headers)
    result = resp.json()
    return result.get("access_token")

def token():
    global _last_token
    if _last_token is None or token_expired(_last_token):
        _last_token = request_token()
    return _last_token

#-------
# A standalone example of using keycloak to authenticate to cdf and verify that we are logged inn
project = "energima"
server_url = "https://auth.properate.com"

realm = {
    "energima": "prod",
    "energima-dev": "dev",
    "energima-test": "test"
}

_last_token = None

client_name="asplan_viak"
client_secret = "xdevIMhUEpqWjGxjzELJ0Xfof8QVfktx"
# Set this variable to an app specific name:
cdf_client_name = os.environ.get("AH_7224_Gammelbakkan_15", client_name)

cfg = ClientConfig(client_name=cdf_client_name, project=project,
                credentials=Token(token))
cdf = CogniteClient(cfg)
#--------------------------------------------------------------------------------------------------------------
external_id_list = cdf.time_series.list().to_pandas()["external_id"]
#


# Kart
st.title("Fra datainnsamling til kartfremvisning")
c1, c2 = st.columns(2)
with c2:
    st.header("Behandlede data")
    time_series_list = ["TS_7224_Gammelbakkan_15+GB15=320.002-LV001-RE001_Geo_heat_power-RF001", "TS_7224_Gammelbakkan_15+GB15=320.003-LV001-RE001_Geo_heat_power-RF001"]
    tab1, tab2 = st.tabs(["Gjennomstrømningsmåler 1 [kW]", "Gjennomstrømningsmåler 2 [kW]"])
    with tab1:
        selected_time_series = time_series_list[0]
        df = cdf.time_series.data.retrieve(external_id=selected_time_series).to_pandas()
        metadata = cdf.time_series.retrieve(external_id=selected_time_series).to_pandas().T
        data = df[selected_time_series]
        st.subheader("Siste 20 datapunkter")
        new_data = data[-20:]
        fig = px.line(x=new_data.index.values, y=new_data, width=600, height=300)
        fig.update_traces(line_color='#1d3c34')
        fig.update_layout(xaxis_title="Tid", yaxis_title="kW")
        st.plotly_chart(fig)

        st.subheader("Alle datapunkter")
        new_data = data
        fig = px.line(x=new_data.index.values, y=new_data, width=600, height=300)
        fig.update_traces(line_color='#1d3c34')
        fig.update_layout(xaxis_title="Tid", yaxis_title="kW")
        st.plotly_chart(fig)
    with tab2:
        selected_time_series = time_series_list[1]
        df = cdf.time_series.data.retrieve(external_id=selected_time_series).to_pandas()
        metadata = cdf.time_series.retrieve(external_id=selected_time_series).to_pandas().T
        data = df[selected_time_series]
        st.subheader("Siste 20 datapunkter")
        new_data = data[-20:]
        fig = px.line(x=new_data.index.values, y=new_data, width=600, height=300)
        fig.update_traces(line_color='#1d3c34')
        fig.update_layout(xaxis_title="Tid", yaxis_title="kW")
        st.plotly_chart(fig)

        st.subheader("Alle datapunkter")
        new_data = data
        fig = px.line(x=new_data.index.values, y=new_data, width=600, height=300)
        fig.update_traces(line_color='#1d3c34')
        fig.update_layout(xaxis_title="Tid", yaxis_title="kW")
        st.plotly_chart(fig)
    if new_data[-1] > 20:
        selected_color = "green"
    else:
        selected_color = "red"

#with c1:
#    st.header("Case Melhus")
#    lat, lon = 63.28629, 10.26335 
#    map_obj = Map()
#    map_obj.address_lat = lat
#    map_obj.address_long = lon
#    map_obj.address_name = "Gammelbakkan 15"
#    map_obj.create_wms_map(selected_zoom = 14, selected_display=False, popup_data= "Gammelbakkan 15", selected_color = selected_color)
#    map_obj.show_map()

    




