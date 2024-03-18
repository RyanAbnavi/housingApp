# Data Source: https://public.tableau.com/app/profile/federal.trade.commission/viz/FraudandIDTheftMaps/AllReportsbyState
# US State Boundaries: https://public.opendatasoft.com/explore/dataset/us-state-boundaries/export/

import streamlit as st    
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
import requests

PAGE_TITLE = 'US HOUSING DATA'
PAGE_SUB_TITLE = 'DAYS ON MARKET ANALYSIS'

def get_cities_data(df, date):
    cities_data = df[['RegionName', 'StateName', 'population', 'density', 'lng', 'lat', date]]
    cities_data.dropna(inplace=True)
    # Create Point geometries from latitude and longitude
    geometry = [Point(xy) for xy in zip(cities_data['lng'], cities_data['lat'])]
    # Convert DataFrame to GeoDataFrame
    cities_geoPandas = gpd.GeoDataFrame(cities_data, geometry=geometry)
    # Set the CRS for the GeoDataFrame
    cities_geoPandas.crs = 'EPSG:4326'  # Assuming WGS84 coordinate reference system
    # Drop the latitude and longitude columns if needed
    cities_geoPandas = cities_geoPandas.drop(['lat', 'lng'], axis=1)
    cities_geoPandas = cities_geoPandas.rename(columns={date:'DaysOnMarket'})
    return cities_geoPandas

def get_states_geoJson():
    states_geoJson = requests.get(
    "https://raw.githubusercontent.com/python-visualization/folium-example-data/main/us_states.json"
    ).json()
    return states_geoJson
    
def get_state_level_data(df, date):
    state_level_data = df.groupby(['StateName']) \
            .apply(lambda x: pd.Series({
                'DaysOnMarket': x[date].mean(),
                'Population': x['population'].mean(),
                'Density': x['density'].mean(),
                }))\
            .reset_index()
    return state_level_data
    
def plot_map(states_geoJson, state_level_data, cities_geoPandas):
    m = folium.Map(location=[38, -102], zoom_start=4, scrollWheelZoom=False)

    choropleth = folium.Choropleth(
        geo_data=states_geoJson,
        name="choropleth",
        data=state_level_data,
        columns=["StateName", "DaysOnMarket"],
        key_on="feature.id",
        fill_color="PuBuGn",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Day On Market",
    )

    choropleth.geojson.add_to(m)

    for feature in choropleth.geojson.data['features']:
        state_name = feature['id']
        DaysOnMarket = state_level_data.loc[state_level_data['StateName']==state_name, 'DaysOnMarket'].values[0]
        feature['properties']['DaysOnMarket'] = f'State Avg DaysOnMarket: {DaysOnMarket:.2f}'
        

    choropleth.geojson.add_child(
        folium.features.GeoJsonTooltip(['name', 'DaysOnMarket'], labels=False)
    )

    folium.GeoJson(
        cities_geoPandas,
        name="Subway Stations",
        marker=folium.Circle(radius=4, fill_color="orange", fill_opacity=0.4, color="black", weight=1),
        tooltip=folium.GeoJsonTooltip(fields=["RegionName", 'population', 'density', 'DaysOnMarket']),
        popup=folium.GeoJsonPopup(fields=["RegionName", 'population', 'density', 'DaysOnMarket']),
        style_function=lambda x: {
            "radius": (x['properties']['DaysOnMarket'])*400,
        },
        highlight_function=lambda x: {"fillOpacity": 0.8},
        zoom_on_click=False,
    ).add_to(m)

    # Add dark and light mode. 
    folium.TileLayer('cartodbdark_matter',name="dark mode",control=True).add_to(m)
    folium.TileLayer('cartodbpositron',name="light mode",control=True).add_to(m)

    # We add a layer controller. 
    folium.LayerControl(collapsed=True).add_to(m)
    st_map = st_folium(m, width=700, height=450)
    
    state = 'USA'
    city = ''
    if st_map['last_active_drawing']:
        try:
            city = st_map['last_active_drawing']['properties']['RegionName']
            state = st_map['last_active_drawing']['properties']['StateName'] 
        except:
            # It's Satte
            # state_id = st_map['last_active_drawing']
            state = st_map['last_active_drawing']['properties']['name']
        # st_map['last_active_drawing']
    return state, city

def display_state_filter(df, state_name):
    state_list = ['USA'] + sorted(df.state_name.unique().tolist())
    state_index = state_list.index(state_name)
    return st.sidebar.selectbox("State", state_list, state_index)
    

def display_date_filter(df):
    col1, col2 = st.columns([24, 8])
    date_list = df.Date.tolist()[::-1]
    return col1.selectbox("Date", date_list, 0)


def main():
    st.set_page_config(
     page_title=PAGE_TITLE,
     layout="wide",
     initial_sidebar_state="expanded",
    )
    st.title(PAGE_TITLE)
    st.caption(PAGE_SUB_TITLE)

    #Load Data
    df_daysOnMarket_states = pd.read_csv('data/states_data.csv')
    df_daysOnMarket_US = pd.read_csv('data/us_data.csv')
    date = display_date_filter(df_daysOnMarket_US)
    
    cities_geoPandas = get_cities_data(df_daysOnMarket_states, date)
    states_geoJson = get_states_geoJson()
    state_level_data = get_state_level_data(df_daysOnMarket_states, date)


    # Create two columns with width ratios 3:1
    col1, col2, col3 = st.columns([24, 1, 7])
    # Add content to the first column (3/4 page width)
    with col1:
        st.header("Main Content")
        # Add your content here for the main column
        state, city = plot_map(states_geoJson, state_level_data, cities_geoPandas)
        if city:
            state = df_daysOnMarket_states.loc[df_daysOnMarket_states['StateName']==state]['state_name'].values[0]

    with col3:
        st.header("Side ")
        if state == 'USA':
            US_DaysOnMarket = df_daysOnMarket_US['DaysOnMarket'].mean()
            st.metric(label="COUNTRY", value="USA")
            st.metric(label="AVG DAYS ON MARKET", value=f"{US_DaysOnMarket:,.2f}")
            st.metric(label="POPULATION", value="341,814,420")
            st.metric(label="DENCITY / Km2", value=f"{37.1:,.2f}")
        else:
            if city == '':
                df = df_daysOnMarket_states[(df_daysOnMarket_states['state_name']==state)]
                state_data = get_state_level_data(df, date)
                st.metric(label="STATE", value=state)
                st.metric(label="AVG DAYS ON MARKET", value=f"{state_data['DaysOnMarket'].values[0]:,.2f}")
                st.metric(label="POPULATION", value=f"{state_data['Population'].values[0]:,.2f}")
                st.metric(label="DENCITY / Km2", value=f"{state_data['Density'].values[0]:,.2f}")
            else:
                df = df_daysOnMarket_states.loc[(df_daysOnMarket_states['RegionName']==city) &\
                                                 (df_daysOnMarket_states['state_name']==state)]
                st.metric(label="CITY", value=city)
                st.metric(label="AVG DAYS ON MARKET", value=f"{df[date].values[0]:,.2f}")
                st.metric(label="POPULATION", value=f"{df['population'].values[0]:,.2f}")
                st.metric(label="DENCITY / Km2", value=f"{df['density'].values[0]:,.2f}")

        
    # Add your content here for the side column
    if state == 'USA':
        st.line_chart(data = df_daysOnMarket_US, x='Date', y='DaysOnMarket', height=250, use_container_width=True)
    else:
        if city == '':
            df = df_daysOnMarket_states[(df_daysOnMarket_states['state_name']==state)]
            df = pd.DataFrame(df.iloc[:, 5:-8].mean()).reset_index(drop=False).rename(columns={'index':'Date', 0: 'DaysOnMarket'})
        else:
            df = df_daysOnMarket_states.loc[(df_daysOnMarket_states['RegionName']==city) &\
                                            (df_daysOnMarket_states['state_name']==state)]
            df = pd.DataFrame(df.iloc[:, 5:-8].T).reset_index(drop=False)
            df.columns = ['Date', 'DaysOnMarket']        
        st.line_chart(data = df, x='Date', y='DaysOnMarket', height=250, use_container_width=True)


    #Display Filters and Map

    #Display Metrics
    col1, col2, col3 = st.columns(3)


if __name__ == "__main__":
    

    main()
