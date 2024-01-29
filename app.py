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
from src.time_loop import time_loop
from functools import reduce

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
    tab1, tab2 = st.tabs(["Nåtilstand", "Historikk"])
    if state == "Helsetilstand":
        with tab1:
            last_kpa_value = kpa_to_percentage(last_pa_value/1000)
            plot_gauge(value = last_kpa_value, text = "Helsetilstand", name = name)
        with tab2:
            percentage_values = kpa_to_percent(df)
            plot_percentages(x = df.index.values, y = percentage_values)
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
    view.pitch = 140
    view.bearing = 70
    view.zoom = 14.5

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
        get_elevation="verdi_fornybar_energi_number",
        elevation_scale=0.0001,
        radius=10,
        get_fill_color=[0, color, 0],
        pickable=True,
        #auto_highlight=True,
    )
    tooltip = {
        #"html": "<b> Gimse skole </b><br>Fornybar energi er nå verdt {verdi_fornybar_energi} kr.<br>- Grunnvarme: {verdi_grunnvarme} kr<br> - Solceller: {verdi_sol} kr.",
        "html": "<b> Gimse skole </b><br>Fornybar energi<br>er nå verdt {verdi_fornybar_energi} kr<br> - Grunnvarme: {verdi_grunnvarme} kr<br> - Solceller: {verdi_sol} kr.",
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

def format_years(value):
    return f"{int(value)} år"

if __name__ == "__main__":
    streamlit_settings()
    #--
    properate = Properate(ID = "AH_7224_Gammelbakkan_15")
    #--
    df_gshp_value, metadata_gshp_value = properate.get_timeseries("TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001")
    df_gshp_value.rename(columns={'TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001' : 'GSHP_VALUE'}, inplace=True)
    df_solar_value, metadata_solar_value = properate.get_timeseries("TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001")
    df_solar_value.rename(columns={"TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001" : 'SOLAR_VALUE'}, inplace=True)
    df_gshp_energy_1, metadata_gshp_energy_1 = properate.get_timeseries("TS_7224_Gammelbakkan_15+GB15=320.002-LV001-OE001_Geo_heat_energy-OE001") # 320.002
    df_gshp_energy_1.rename(columns={"TS_7224_Gammelbakkan_15+GB15=320.002-LV001-OE001_Geo_heat_energy-OE001" : 'GSHP_ENERGY_1'}, inplace=True)
    df_gshp_energy_2, metadata_gshp_energy_2 = properate.get_timeseries("TS_7224_Gammelbakkan_15+GB15=320.003-LV001-OE001_Geo_heat_energy-OE001") # 320.003
    df_gshp_energy_2.rename(columns={"TS_7224_Gammelbakkan_15+GB15=320.003-LV001-OE001_Geo_heat_energy-OE001" : 'GSHP_ENERGY_2'}, inplace=True)
    df_solar_energy, metadata_solar = properate.get_timeseries("TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001")
    df_solar_energy.rename(columns={"TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001" : 'SOLAR_ENERGY'}, inplace=True)

    df_gshp_value['Timestamp'] = pd.to_datetime(df_gshp_value.index)
    df_solar_value['Timestamp'] = pd.to_datetime(df_solar_value.index)
    df_gshp_energy_1['Timestamp'] = pd.to_datetime(df_gshp_energy_1.index)
    df_gshp_energy_2['Timestamp'] = pd.to_datetime(df_gshp_energy_2.index)
    df_solar_energy['Timestamp'] = pd.to_datetime(df_solar_energy.index)
    
    #df_gshp_value = df_gshp_value.reset_index()
    #df_solar_value = df_solar_value.reset_index()
    #df_gshp_energy_1 = df_gshp_energy_1.reset_index()
    #df_gshp_energy_2 = df_gshp_energy_2.reset_index()
    #df_solar_energy = df_solar_energy.reset_index()

    #new_column_names = ["GSHP_VALUE", "SOLAR_VALUE", "GSHP_ENERGY_1", "GSHP_ENERGY_2", "SOLAR_ENERGY"]
    dataframes = [df_gshp_value, df_solar_value, df_gshp_energy_1, df_gshp_energy_2, df_solar_energy]
    merged_df = pd.merge(df_gshp_value, df_solar_value, on='Timestamp', how='outer')
    merged_df = pd.merge(merged_df, df_gshp_energy_1, on='Timestamp', how='outer')
    merged_df = pd.merge(merged_df, df_gshp_energy_2, on='Timestamp', how='outer')
    merged_df = pd.merge(merged_df, df_solar_energy, on='Timestamp', how='outer')
    merged_df.set_index('Timestamp', inplace=True)
    df = merged_df
    #df = reduce(lambda left, right: pd.merge(left, right, left_index=True, right_index=True), dataframes)
    #df.rename(columns=dict(zip(df.columns, new_column_names)), inplace=True)
    df["ELPRICE"] = df["GSHP_VALUE"] / (df["GSHP_ENERGY_1"] + df["GSHP_ENERGY_2"])
    df["NETTLEIE"] = df["ELPRICE"] / 2 # hvilken modell skal vi gå for?
    df["ELPRICE_WITH_NETTLEIE"] = df["ELPRICE"] + df["NETTLEIE"]
    df["GSHP_VALUE_WITH_NETTLEIE"] = df["ELPRICE_WITH_NETTLEIE"] * (df["GSHP_ENERGY_1"] + df["GSHP_ENERGY_2"])
    df["SOLAR_VALUE_WITH_NETTLEIE"] = df["ELPRICE_WITH_NETTLEIE"] * df["SOLAR_ENERGY"]
    
    cumsum_df = df.cumsum()
    cumsum_df.columns = [col + '_CUMSUM' for col in cumsum_df.columns]
    df = pd.concat([df, cumsum_df], axis=1)
    df = df.round(1)

    #--
    col1, col2 = st.columns(2)
    with col1:        
        pydeck_df = pd.DataFrame({
            "id" : ["Gimse skole"],
            "lat" : [63.286463],
            "lng" : [10.263912],
            "verdi_fornybar_energi" : [f"{int(np.sum(df['GSHP_VALUE_WITH_NETTLEIE']) + np.sum(df['SOLAR_VALUE_WITH_NETTLEIE'])):,}".replace(",", " ")],
            "verdi_fornybar_energi_number" : [int(np.sum(df['GSHP_VALUE_WITH_NETTLEIE']) + np.sum(df['SOLAR_VALUE_WITH_NETTLEIE']))],
            "verdi_sol" : [f"{int(np.sum(df['SOLAR_VALUE_WITH_NETTLEIE'])):,}".replace(",", " ")],
            "verdi_grunnvarme" : [f"{int(np.sum(df['GSHP_VALUE_WITH_NETTLEIE'])):,}".replace(",", " ")]
        })
        r = show_pydeck_map(df = pydeck_df, last_value = 100)
        
        st.pydeck_chart(pydeck_obj = r, use_container_width = True)
        #--
    with col2:
        tab1, tab2, tab3 = st.tabs(["Verdi produsert energi", "Produsert energi", "Fremtidsutsikter"])
        plotting_df = df.copy()
        plotting_df.dropna()
        interval = 5  # Adjust the interval as needed
        plotting_df = plotting_df.iloc[::interval]
        with tab1:
            days_between = (df.index.max() - df.index.min()).days
            total_saving_kWh = int(np.sum(df['GSHP_VALUE_WITH_NETTLEIE']) + np.sum(df['SOLAR_VALUE_WITH_NETTLEIE']))
            st.write(f"**Besparelse: {total_saving_kWh:,} kr | {int(total_saving_kWh/days_between):,} kr/døgn | {int(total_saving_kWh/(days_between*24)):,} kr/time**".replace(",", " "))
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=plotting_df.index,
                y=plotting_df['GSHP_VALUE_WITH_NETTLEIE_CUMSUM'],
                name='Grunnvarme',
                mode='lines+markers',
                line=dict(color='#1d3c34', width=1),
                marker=dict(color='#1d3c34', size=1, symbol='square')
            ))
            fig.add_trace(go.Scatter(
                x=plotting_df.index,
                y=plotting_df['SOLAR_VALUE_WITH_NETTLEIE_CUMSUM'],
                name='Solceller',
                mode='lines+markers',
                line=dict(color='#FFC358', width=1),
                marker=dict(color='#FFD700', size=1, symbol='square'),
            ))
            fig.update_layout(
                xaxis_title='',
                yaxis_title='Kroner',
                yaxis=dict(range=[0, 800000], tickformat=",", ticks="outside", linecolor="black", gridcolor="lightgrey"),
                xaxis=dict(linecolor="black", gridcolor="lightgrey"),
                separators="* .*",
                margin=dict(l=10, r=10, t=10, b=10)
                #barmode='stack',  # This makes the bars stacked
            )
            st.plotly_chart(fig, use_container_width=True, config = {'staticPlot': True})
        with tab2:
            total_saving = int(np.sum((df["GSHP_ENERGY_1"] + df["GSHP_ENERGY_2"])) + np.sum(df['SOLAR_ENERGY']))
            st.write(f"**Besparelse: {total_saving:,} kWh | {int(total_saving/days_between):,} kWh/døgn | {int(total_saving/(days_between*24)):,} kWh/time**".replace(",", " "))
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=plotting_df.index,
                y=(plotting_df["GSHP_ENERGY_1_CUMSUM"] + plotting_df["GSHP_ENERGY_2_CUMSUM"]),
                name='Grunnvarme',
                mode='lines+markers',
                line=dict(color='#1d3c34', width=1),
                marker=dict(color='#1d3c34', size=1, symbol='square')
            ))
            fig.add_trace(go.Scatter(
                x=plotting_df.index,
                y=(plotting_df['SOLAR_ENERGY_CUMSUM']),
                name='Solceller',
                mode='lines+markers',
                line=dict(color='#FFC358', width=1),
                marker=dict(color='#FFD700', size=1, symbol='square'),
            ))
            
            fig.update_layout(
                xaxis_title='',
                yaxis_title='kWh',
                yaxis=dict(range=[0, 800000], tickformat=",", ticks="outside", linecolor="black", gridcolor="lightgrey"),
                xaxis=dict(linecolor="black", gridcolor="lightgrey"),
                separators="* .*",
                margin=dict(l=10, r=10, t=10, b=10)
                #barmode='stack',  # This makes the bars stacked
            )
            st.plotly_chart(fig, use_container_width=True, config = {'staticPlot': True})
                #
        with tab3:
            years = st.slider("Besparelse", min_value=1, value=10, max_value=50, format="Etter %f år", label_visibility="hidden")
            st.write(f"Estimert besparelse etter {years} år: **{int(total_saving/days_between) * 365 * years:,} kr**".replace(",", " "))
            st.write("")
            st.write(f"Estimert besparelse etter {years} år: **{int(total_saving_kWh/days_between) * 365 * years:,} kWh**".replace(",", " "))
#            with c2:
#                fig = px.line(df_merged_production, x=df_merged_production.index, y=df_merged_production['Produsert fornybar energi akkumulert'], title=f'Produsert fornybar energi<br>• Totalt: {int(df_merged_production["Produsert fornybar energi akkumulert"][-1]):,} kWh<br>• Siste 24 timer: {int(np.sum(df_merged_production_last_24["Produsert fornybar energi"])):,} kWh'.replace(",", " "))
#                fig.update_traces(line_color='#1d3c34', line_width=2)
#                fig.update_xaxes(
#                    title_text='',
#                    ticks="outside",
#                    linecolor="black",
#                    gridcolor="lightgrey",
#                    )
#                fig.update_yaxes(
#                    title_text='kWh',
#                    range=[0, maximum_value_produced],
#                    tickformat=",",
#                    ticks="outside",
#                    linecolor="black",
#                    gridcolor="lightgrey",
#                )
#                fig.update_layout(separators="* .*")
#                st.plotly_chart(fig, use_container_width=True) 
      #--
    st.write("")
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        time_series = "TS_7224_Gammelbakkan_15+GB15=320.003-RD001_dP_hot"
        df, metadata = properate.get_timeseries(time_series)
        skoleflata_helsetilstand = varmeveksler(df, series_name = time_series, name = "Skoleflata", state = "Helsetilstand")
    with c2:
        time_series = "TS_7224_Gammelbakkan_15+GB15=320.002-RD001_dP_hot"
        df, metadata = properate.get_timeseries(time_series)
        bankhallen_helsetilstand = varmeveksler(df, series_name = time_series, name = "Bankhallen", state = "Helsetilstand")
    
    with c3:
        time_series = "TS_7224_Gammelbakkan_15+GB15=320.003-RD001_dP_hot-OF001"
        df, metadata = properate.get_timeseries(time_series)
        skoleflata_helsetilstand = varmeveksler(df, series_name = time_series, name = "Lena Terrasse (virtuell)", state = "Helsetilstand")  


    #
    st.caption(f"{days_between} døgn i drift")
    time_loop()
    st.experimental_rerun()

b = """    
    st.line_chart(df["GSHP_VALUE_CUMSUM"] + df["SOLAR_VALUE_CUMSUM"])

    #--
    time_series_gshp = "TS_7224_Gammelbakkan_15+Common=100.001-OC001-BB001"
    time_series_solar = "TS_7224_Gammelbakkan_15+GB15=471.001-OE001-OE001-OF001"
    df_gshp_value, metadata_gshp_value = properate.get_timeseries(time_series_gshp)
    df_solar_value, metadata_solar_value = properate.get_timeseries(time_series_solar)
    df_merged_values = pd.merge(df_solar_value, df_gshp_value, left_index=True, right_index=True, how='outer')
    df_merged_values.fillna(0, inplace=True)
    df_merged_values["Verdi fornybar energi"] = df_merged_values[time_series_gshp] + df_merged_values[time_series_solar]
    df_merged_values = df_merged_values.drop_duplicates(subset=['Verdi fornybar energi'])
    df_merged_values['Verdi fornybar energi akkumulert'] = df_merged_values["Verdi fornybar energi"].cumsum()
    maximum_value_accumulated = int(np.max(df_merged_values['Verdi fornybar energi akkumulert'])*1.1) 

    df_merged_values['Timestamp'] = pd.to_datetime(df_merged_values.index)
    latest_timestamp = df_merged_values['Timestamp'].max()
    twenty_four_hours_ago = latest_timestamp - pd.DateOffset(hours=24)
    df_merged_values_last_24 = df_merged_values[df_merged_values['Timestamp'] >= twenty_four_hours_ago]

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

    df_merged_production['Timestamp'] = pd.to_datetime(df_merged_production.index)
    latest_timestamp = df_merged_production['Timestamp'].max()
    twenty_four_hours_ago = latest_timestamp - pd.DateOffset(hours=24)
    df_merged_production_last_24 = df_merged_production[df_merged_production['Timestamp'] >= twenty_four_hours_ago]
    #--

"""
    





  

a = """       
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

    
