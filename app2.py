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
from time_loop import time_loop

def streamlit_settings():
    st.set_page_config(
        page_title="Case Melhus",
        page_icon="📟",
        layout="wide",
        initial_sidebar_state="collapsed")

    with open("src/styles/main.css") as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)

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
    margin=dict(l=0,r=0,b=0,t=0,pad=0),
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
    margin=dict(l=0,r=0,b=0,t=0,pad=0),
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

def plot_gauge(value, text, name):
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
        title = {'text': name}))
    
    fig.update_layout(margin=dict(l=50, r=50, t=50, b=50))

    st.plotly_chart(fig, use_container_width=True, config = {'displayModeBar': False,})# 'staticPlot': True})

def varmeveksler(df, series_name, name, state):
    last_pa_value = int(df.to_numpy()[-1])
    if state == "Helsetilstand":
        last_kpa_value = kpa_to_percentage(last_pa_value/1000)
        plot_gauge(value = last_kpa_value, text = "Helsetilstand", name = name)
#        percentage_values = kpa_to_percent(df)
#        plot_percentages(x = df.index.values, y = percentage_values)
    elif state == "Trykkdifferanse":
        plot_gauge(value = last_pa_value, text = "Trykkdifferanse", name = name)
        y = df[series_name].to_numpy()
        plot_kpa(x = df.index.values, y = y)
    return last_kpa_value

def get_last_week(time_series, properate):
    df, metadata = properate.get_timeseries(time_series)
    return df.to_numpy()[-(24 * 7):], df, metadata


def show_pydeck_map(df, last_value):
    view = pdk.data_utils.compute_view(df[["lng", "lat"]])
    view.pitch = 45
    view.bearing = 10
    view.zoom = 14

    color = 0
    if last_value > 10 and last_value < 20:
        color = 60
    if last_value > 20 and last_value < 30:
        color = 120
    if last_value > 30 and last_value < 40:
        color = 180
    if last_value > 40:
        color = 255 
    
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["lng", "lat"],
        get_elevation="verdi_fornybar_energi",
        elevation_scale=0.0001,
        radius=10,
        get_fill_color=[0, color, 0],
        pickable=True,
        #auto_highlight=True,
    )
    tooltip = {
        "html": "<b> Gimse skole </b><br>Fornybar energi er nå verdt {verdi_fornybar_energi} kr.<br>- Grunnvarme: {verdi_grunnvarme} kr<br> - Solceller: {verdi_sol} kr.",
        "style": {
        "backgroundColor": "white",
        "color": "black"
    },
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
    streamlit_settings()
    #st_autorefresh(interval=1 * 15 * 1000, key="dataframerefresh")
    #--
    col1, col2 = st.columns(2)
    with col1:
        properate = Properate(ID = "AH_7224_Gammelbakkan_15")
        time_series_gshp = "TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001"
        df_gshp, metadata = properate.get_timeseries(time_series_gshp)
        
        time_series_solar = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001"
        df_solar, metadata = properate.get_timeseries(time_series_solar)
        
        last_value = int(float(df_gshp.to_numpy()[-1]) + float(df_solar.to_numpy()[-1]))
        total_value = int(np.sum(df_gshp.to_numpy()) + np.sum(df_solar.to_numpy()))
        solar_value = int(np.sum(df_solar.to_numpy()))
        gshp_value = int(np.sum(df_gshp.to_numpy()))
        
        df = pd.DataFrame({
            "id" : ["Gimse skole"],
            "lat" : [63.286463],
            "lng" : [10.263912],
            "verdi_fornybar_energi" : [total_value],
            "verdi_fornybar_momentan" : [last_value],
            "verdi_sol" : [solar_value],
            "verdi_grunnvarme" : [gshp_value]
        })
        r = show_pydeck_map(df = df, last_value = last_value)
        
        st.pydeck_chart(pydeck_obj = r, use_container_width = True)
        #--
    with col2:
        with st.expander("Gimse skole", expanded = True):
            c1, c2 = st.columns(2)
            with c1:
                #--
                time_series_gshp = "TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001"
                time_series_solar = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001"
                df_gshp_value, metadata_gshp_value = properate.get_timeseries(time_series_gshp)
                df_solar_value, metadata_solar_value = properate.get_timeseries(time_series_solar)
                df_merged_values = pd.merge(df_solar_value, df_gshp_value, left_index=True, right_index=True, how='outer')
                df_merged_values.fillna(0, inplace=True)
                df_merged_values["Verdi fornybar energi"] = df_merged_values[time_series_gshp] + df_merged_values[time_series_solar]
                df_merged_values['Verdi fornybar energi akkumulert'] = df_merged_values["Verdi fornybar energi"].cumsum()
                maximum_value_accumulated = int(np.max(df_merged_values['Verdi fornybar energi akkumulert'])*1.1) 

                fig = px.line(df_merged_values, x=df_merged_values.index, y=df_merged_values["Verdi fornybar energi akkumulert"], title=f'Besparelse<br>• Totalt: {int(df_merged_values["Verdi fornybar energi akkumulert"][-1]):,} kr<br>• Siste 24 timer: {int(np.sum(df_merged_values["Verdi fornybar energi"][-288:-1])):,} kr'.replace(",", " "))
                maximum_value = int(np.max(df_merged_values["Verdi fornybar energi akkumulert"])*1.1)
                fig.update_traces(line_color='#1d3c34', line_width=2)
                fig.update_xaxes(
                    title_text='',
                    ticks="outside",
                    linecolor="black",
                    gridcolor="lightgrey",
                    )
                fig.update_yaxes(
                    title_text='Kroner',
                    range=[0, maximum_value_accumulated],
                    tickformat=",",
                    ticks="outside",
                    linecolor="black",
                    gridcolor="lightgrey",
                ) 
                fig.update_layout(separators="* .*")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                #--
                time_series_1 = "TS_7224_Gammelbakkan_15+GB15=320.002-LV001-OE001_Geo_heat_energy-OE001"
                df_gshp_production_1, metadata_gshp_production_1 = properate.get_timeseries(time_series_1)
                time_series_2 = "TS_7224_Gammelbakkan_15+GB15=320.003-LV001-OE001_Geo_heat_energy-OE001"
                df_gshp_production_2, metadata_gshp_production_1 = properate.get_timeseries(time_series_2)

                df_gshp_production = pd.merge(df_gshp_production_1, df_gshp_production_2, left_index=True, right_index=True, how='outer')
                df_gshp_production["Produsert grunnvarme"] = df_gshp_production[time_series_1] + df_gshp_production[time_series_2]
                
                time_series_solar_production = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001"
                df_solar_production, metadata_solar = properate.get_timeseries(time_series_solar_production)

                df_merged_production = pd.merge(df_gshp_production, df_solar_production, left_index=True, right_index=True, how='outer')
                df_merged_production.fillna(0, inplace=True)
                df_merged_production["Produsert fornybar energi"] = df_merged_production["Produsert grunnvarme"] + df_merged_production[time_series_solar_production]
                df_merged_production['Produsert fornybar energi akkumulert'] = df_merged_production["Produsert fornybar energi"].cumsum()
                maximum_value_produced = int(np.max(df_merged_production['Produsert fornybar energi akkumulert'])*1.1)

                fig = px.line(df_merged_production, x=df_merged_production.index, y=df_merged_production['Produsert fornybar energi akkumulert'], title=f'Produsert fornybar energi<br>• Totalt: {int(df_merged_production["Produsert fornybar energi akkumulert"][-1]):,} kWh<br>• Siste 24 timer: {int(np.sum(df_merged_production["Produsert fornybar energi"][-24:-1])):,} kW'.replace(",", " "))
                fig.update_traces(line_color='#1d3c34', line_width=2)
                fig.update_xaxes(
                    title_text='',
                    ticks="outside",
                    linecolor="black",
                    gridcolor="lightgrey",
                    )
                fig.update_yaxes(
                    title_text='kWh',
                    range=[0, maximum_value_produced],
                    tickformat=",",
                    ticks="outside",
                    linecolor="black",
                    gridcolor="lightgrey",
                )
                fig.update_layout(separators="* .*")
                st.plotly_chart(fig, use_container_width=True) 

    time_loop()
    st.experimental_rerun()




a = """
    #--
    c1, c2 = st.columns(2)
    with c1:
        time_series = "TS_7224_Gammelbakkan_15+GB15=320.003-RD001_dP_hot"
        df, metadata = properate.get_timeseries(time_series)
        skoleflata_helsetilstand = varmeveksler(df, series_name = time_series, name = "Bankhallen", state = "Helsetilstand")
    with c2:
        time_series = "TS_7224_Gammelbakkan_15+GB15=320.002-RD001_dP_hot"
        df, metadata = properate.get_timeseries(time_series)
        bankhallen_helsetilstand = varmeveksler(df, series_name = time_series, name = "Lena Terrasse", state = "Helsetilstand")
    
#    with c3:
#        time_series = "TS_7224_Gammelbakkan_15+GB15=320.003-RD001_dP_hot-OF001"
#        df, metadata = properate.get_timeseries(time_series)
#        skoleflata_helsetilstand = varmeveksler(df, series_name = time_series, name = "Lena Terrasse (virtuell)", state = "Helsetilstand")  


       
    c1, c2 = st.columns(2)
    with c1:
        #-- grunnvarme verdi
        time_series = "TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001"
        df_gshp_value, metadata_gshp_value = properate.get_timeseries(time_series)
        df_gshp_value_last = df_gshp_value[-(1400):]
        fig = px.line(df_gshp_value_last, x=df_gshp_value_last.index, y=time_series, title='Verdi grunnvarme')
        maximum_value = int(np.max(df_gshp_value_last[time_series])*1.1) 
        fig.update_xaxes(
            title_text='')
        fig.update_yaxes(
            title_text='Kroner',
            range=[0, maximum_value]
        )
        st.plotly_chart(fig, use_container_width=True)

        #-- grunnvarme akkumulurt
        df_gshp_value['akkumulert'] = df_gshp_value[time_series].cumsum()
        maximum_value_accumulated = int(np.max(df_gshp_value['akkumulert'])*1.1) 
        fig = px.line(df_gshp_value, x=df_gshp_value.index, y=df_gshp_value["akkumulert"], title='Verdi grunnvarme ')
        fig.update_xaxes(
            title_text=''
            )
        fig.update_yaxes(
            title_text='Kroner',
            range=[0, maximum_value_accumulated])
        st.plotly_chart(fig, use_container_width=True)

        #--grunnvarme produksjon
        time_series_1 = "TS_7224_Gammelbakkan_15+GB15=320.002-LV001-OE001_Geo_heat_energy-OE001"
        df_gshp_production_1, metadata_gshp_production_1 = properate.get_timeseries(time_series_1)
        #--
        time_series_2 = "TS_7224_Gammelbakkan_15+GB15=320.003-LV001-OE001_Geo_heat_energy-OE001"
        df_gshp_production_2, metadata_gshp_production_1 = properate.get_timeseries(time_series_2)
        
        df_gshp_production = pd.merge(df_gshp_production_1, df_gshp_production_2, left_index=True, right_index=True, how='outer')
        df_gshp_production["varmeproduksjon"] = df_gshp_production[time_series_1] + df_gshp_production[time_series_2]

        df_gshp_production_last = df_gshp_production[-(1400):]
        fig = px.line(df_gshp_production_last, x=df_gshp_production_last.index, y=df_gshp_production_last["varmeproduksjon"], title='Grunnvarmeproduksjon')
        fig.update_xaxes(title_text='Tid')
        fig.update_yaxes(title_text='Effekt [kW]')
        st.plotly_chart(fig, use_container_width=True)

        #-- grunnvarme produksjon akkumulurt
        df_gshp_production['akkumulert'] = df_gshp_production["varmeproduksjon"].cumsum()
        fig = px.line(df_gshp_production, x=df_gshp_production.index, y=df_gshp_production["akkumulert"], title='Grunnvarmeproduksjon')
        fig.update_xaxes(
            title_text=''
            )
        fig.update_yaxes(
            title_text='kWh',
            range=[0, maximum_value_accumulated])
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        #-- solceller verdi
        time_series = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001"
        df_solar_value, metadata_solar_value = properate.get_timeseries(time_series)
        df_solar_value_last = df_solar_value[-(1400):]
        fig = px.line(df_solar_value_last, x=df_solar_value_last.index, y=time_series, title='Verdi solceller')
        fig.update_xaxes(
            title_text=''
            )
        fig.update_yaxes(
            title_text='Kroner',
            range=[0, maximum_value])
        st.plotly_chart(fig, use_container_width=True)

        #-- solceller akkumulurt
        df_solar_value['akkumulert'] = df_solar_value[time_series].cumsum()
        fig = px.line(df_solar_value, x=df_solar_value.index, y=df_solar_value["akkumulert"], title='Verdi solceller')
        fig.update_xaxes(
            title_text=''
            )
        fig.update_yaxes(
            title_text='Kroner',
            range=[0, maximum_value_accumulated])
        st.plotly_chart(fig, use_container_width=True)

        #--solceller produksjon
        time_series = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001"
        df_solar_production, metadata_solar = properate.get_timeseries(time_series)
        df_solar_production_last = df_solar_production[-(1400):]
        fig = px.line(df_solar_production_last, x=df_solar_production_last.index, y=time_series, title='Solcelleproduksjon')
        fig.update_xaxes(title_text='Tid')
        fig.update_yaxes(title_text='Effekt [kW]')
        st.plotly_chart(fig, use_container_width=True)


        #--
        #-- akkumulert
#        df_cost_accumulated = pd.merge(df_gshp_, df_gshp_production_2, left_index=True, right_index=True, how='outer')
#        df_gshp_production["akkumulert_verdi"] = df_gshp_production[time_series_1] + df_gshp_production[time_series_2]
#        df_solar_value['akkumulert'] = df_solar_value[time_series].cumsum()
#        fig = px.line(df_solar_value, x=df_solar_value.index, y=df_solar_value["akkumulert"], title='Verdi solceller')
#        fig.update_xaxes(
#            title_text=''
#            )
#        fig.update_yaxes(
#            title_text='Kroner',
#            range=[0, maximum_value_accumulated])
#        st.plotly_chart(fig, use_container_width=True)

#    df_merge = pd.merge(df_solar_value, df_gshp_value, left_index=True, right_index=True, how='outer')
#    df_merge.fillna(0, inplace=True)
#    fig = px.bar(df_merge, x=df_merge.index, y=df_merge.columns, title='Verdi fornybar energi')
#    fig.update_xaxes(title_text='Tid')
#    fig.update_yaxes(title_text='Kroner')
#    fig.update_layout(barmode='stack')
#    st.plotly_chart(fig)
       
"""   

    