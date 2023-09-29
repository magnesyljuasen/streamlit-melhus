# app
st.title("Fra datainnsamling til kartfremvisning")
c1, c2 = st.columns(2)
with c2:
    st.header("Behandlede data")
    time_series_list = ["TS_7224_Gammelbakkan_15+GB15=320.002-LV001-RE001_Geo_heat_power-RF001", "TS_7224_Gammelbakkan_15+GB15=320.003-LV001-RE001_Geo_heat_power-RF001"]
    tab1, tab2 = st.tabs(["Gjennomstrømningsmåler 1 [kW]", "Gjennomstrømningsmåler 2 [kW]"])
    with tab1:
        selected_time_series = time_series_list[0]
        #df = cdf.time_series.data.retrieve(external_id=selected_time_series).to_pandas()
        #metadata = cdf.time_series.retrieve(external_id=selected_time_series).to_pandas().T
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

with c1:
    st.header("Case Melhus")
    lat, lon = 63.28629, 10.26335 
    map_obj = Map()
    map_obj.address_lat = lat
    map_obj.address_long = lon
    map_obj.address_name = "Gammelbakkan 15"
    map_obj.create_wms_map(selected_zoom = 14, selected_display=False, popup_data= "Gammelbakkan 15", selected_color = selected_color)
    map_obj.show_map()
