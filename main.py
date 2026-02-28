#!/usr/bin/env python3
import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
import os
from retry_requests import retry
import folium
from streamlit_folium import st_folium

from data.weatherData_decoded import wmoData
from datetime import timedelta, date as Date
#import sys



def find_nearest_index(lat, lon, df):
    distances = np.sqrt(
        (df["latitude"] - lat) ** 2 +
        (df["longitude"] - lon) ** 2
    )
    return distances.idxmin()

@st.cache_data(show_spinner=False)
def fetch_weather(latitudes, longitudes, start_date, end_date, temp_unit):
    url = "https://archive-api.open-meteo.com/v1/archive"
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily": ["weather_code","temperature_2m_max","temperature_2m_min","rain_sum","snowfall_sum","precipitation_hours","daylight_duration"],
        "temperature_unit": temp_unit,
        "timezone": "America/Phoenix"
    }
    return openmeteo.weather_api(url, params=params)

def main():
    # -------------------------------------------------
    # File Variables
    # -------------------------------------------------

    #trail_name = sys.argv[1]
    #trail_name = st.secrets["TRAIL_NAME"]
    trail_name = 'CDT'
    emblem_image = 'data/' + trail_name + '_emblem.png'
    if not os.path.isfile(emblem_image):
        emblem_image = False

    POI_file = './data/' + trail_name + '_POI.csv'
    if not os.path.isfile(POI_file):
        POI_file = False

    Trackpoints_file = './data/' + trail_name + '_trackpoints.csv'
    MM_file_NOBO = './data/' + trail_name + '_MM_points_list_NOBO.csv' 
    MM_file_SOBO = './data/' + trail_name + '_MM_points_list_SOBO.csv' 
    
    

    
    # -----------------------------------
    # Initialisierung Session-State
    # -----------------------------------
    if "start_date" not in st.session_state:
        st.session_state.start_date = Date.today() - timedelta(days=365)

    if "end_date" not in st.session_state:
        st.session_state.end_date = None

    if "last_start_date" not in st.session_state:
        st.session_state.last_start_date = None

    if "mm_weather_df" not in st.session_state:
        st.session_state.mm_weather_df = None

    if "mm_range_coords" not in st.session_state:
        st.session_state.mm_range_coords = None

    if "clicked_location" not in st.session_state:
        st.session_state.clicked_location = None

    if "clicked_weather_df" not in st.session_state:
        st.session_state.clicked_weather_df = None


    # -------------------------------------------------
    # Map-Layout: Settings
    # -------------------------------------------------
    st.set_page_config(page_title= trail_name +" History Weather", page_icon="desert" ,layout="wide")
    #st.title("🏔 " + trail_name +"  History Weather")
    #st.logo(("data/AZT_emblem.png"))

    # -------------------------------------------------
    # Sidebar: Beautyfier
    # -------------------------------------------------

    with st.sidebar.container(border=False):
        left, center, right = st.columns([1, 2, 1])  # 25% / 50% / 25%
        with center:
            if emblem_image:
                st.image(emblem_image)
    st.sidebar.header("History Weather")

    # -----------------------------------
    # Sidebar: Settings Start/End Date Input
    # -----------------------------------

    # Start Date Input
    start_date = st.sidebar.date_input(
        "Start Date",
        key="start_date",
        max_value=Date.today()

    )
    # End-Date Logic
    if start_date != st.session_state.last_start_date:

        st.session_state.end_date = start_date 
        st.session_state.last_start_date = start_date


    # End Date Input
    end_date = st.sidebar.date_input(
        "End Date",
        key="end_date",
        max_value=Date.today() 
    )

    # Hardcoded Dates for Test
    # start_date = "2025-04-15"
    # end_date = "2025-05-04"

    # -----------------------------------
    # Sidebar: Settings Temperature °C or F / Direction NOBO or SOBO
    # -----------------------------------

    with st.sidebar.container(border=False):
        left, right = st.columns([1, 1])  # 50% / 50% 
        with left:
            temperature_unit_input = st.radio("Temperature Unit", ["Celsius", "Fahrenheit"])
            temperature_unit = "celsius" if temperature_unit_input == "Celsius" else "fahrenheit"
            temp_symbol = "°C" if temperature_unit == "celsius" else "°F"
        with right:
            direction = st.radio("Direction", ["NOBO", "SOBO"])
            nobo = True if direction == "NOBO" else False

        
    with st.sidebar.container(border=False):
        left, right = st.columns([1, 1])  # 50% / 50% 
        with left:
            show_MM_input = st.radio("Show MM in map", ["Yes", "No"], index=1)
            show_MM = True if show_MM_input == "Yes" else False
        with right:
            if POI_file:
                show_POI_input = st.radio("Show POIs in map", ["Yes", "No"], index=1)
                show_POI = True if show_POI_input == "Yes" else False
            else:
                show_POI = False
    # when temp_unit is changed in sidebar after weather has been loaded, clear loaded wx. New load has to be performed    
    if "last_temp_unit" not in st.session_state:
        st.session_state.last_temp_unit = temperature_unit

    if temperature_unit != st.session_state.last_temp_unit:
        st.session_state.mm_weather_df = None
        st.session_state.last_temp_unit = temperature_unit
    # when direction is changed in sidebar after weather has been loaded, clear loaded wx. New load has to be performed
    if "last_nobo" not in st.session_state:
        st.session_state.last_nobo = nobo

    if nobo != st.session_state.last_nobo:
        st.session_state.mm_weather_df = None
        st.session_state.last_nobo = nobo
    
    # -----------------------------------
    # Sidebar: Settings Mile Marker Range
    # -----------------------------------

    # Load MM File depending on direction
    MM_file = MM_file_NOBO if nobo else MM_file_SOBO
    MM_df = pd.read_csv(MM_file)

    st.sidebar.subheader("Mile Marker Range")

    mm_options = MM_df["mile_marker"].tolist()


    # Reset Mile Marker if flag is set ( Start= 0, Stop= Last)
    if st.session_state.get("reset_mm_range", False):

        st.session_state.start_mm = mm_options[0]
        st.session_state.end_mm = mm_options[-1]

        st.session_state.reset_mm_range = False

    start_mm = st.sidebar.selectbox(
        "Start Mile Marker",
        mm_options,
        index=0,
        key="start_mm"
    )

    end_mm = st.sidebar.selectbox(
        "End Mile Marker",
        mm_options,
        index=len(mm_options)-1,
        key="end_mm"
    )
    # ensure correct order
    if start_mm > end_mm:
        start_mm, end_mm = end_mm, start_mm

    selected_points = MM_df[
        (MM_df["mile_marker"] >= start_mm) &
        (MM_df["mile_marker"] <= end_mm)
    ]





    # -----------------------------------
    # Sidebar: Load Button
    # -----------------------------------
    if st.sidebar.button("Load Weather for MM Range"):

        with st.spinner("Loading weather for selected range..."):

            latitudes = selected_points["latitude"].tolist()
            longitudes = selected_points["longitude"].tolist()
            mile_markers = selected_points["mile_marker"].tolist()

            responses = fetch_weather(
                latitudes,
                longitudes,
                start_date,
                end_date,
                temperature_unit
            )

        all_rows = []

        for i, response in enumerate(responses):

            daily = response.Daily()

            dates = pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s"),
                end=pd.to_datetime(daily.TimeEnd(), unit="s"),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            )
            daily_weather_code = daily.Variables(0).ValuesAsNumpy()
            daily_weather_human = [wmoData.get(code, f"Unknown ({code})") for code in daily_weather_code]
            df_point = pd.DataFrame({
                "Date": dates,
                "Mile Marker": mile_markers[i],
                "Latitude": latitudes[i],
                "Longitude": longitudes[i],
                f"Temp Max ({temp_symbol})": daily.Variables(1).ValuesAsNumpy(),
                f"Temp Min ({temp_symbol})": daily.Variables(2).ValuesAsNumpy(),
                "Rain (mm)": daily.Variables(3).ValuesAsNumpy(),
                "Worst weather": daily_weather_human,
                "Snow (cm)": daily.Variables(4).ValuesAsNumpy(),
            })

            all_rows.append(df_point)

        final_df = pd.concat(all_rows, ignore_index=True)

        # Formatierung
        final_df["Date"] = final_df["Date"].dt.strftime("%b-%d-%Y")
        numeric_cols = final_df.select_dtypes(include=[np.number]).columns
        final_df[numeric_cols] = np.round(final_df[numeric_cols]).astype("Int64")

        # In Session-State speichern
        st.session_state.mm_weather_df = final_df

        # -------------------------------------------------
        # calculate route between chosen MM. Needed for highlightning this part of the whole trail
        # -------------------------------------------------

        route_df = pd.read_csv(Trackpoints_file)

        start_row = MM_df[MM_df["mile_marker"] == start_mm].iloc[0]
        end_row = MM_df[MM_df["mile_marker"] == end_mm].iloc[0]

        start_idx = find_nearest_index(start_row["latitude"], start_row["longitude"], route_df)
        end_idx = find_nearest_index(end_row["latitude"], end_row["longitude"], route_df)

        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        selected_route_section = route_df.iloc[start_idx:end_idx+1]

        st.session_state.mm_range_coords = list(
            zip(selected_route_section["latitude"],
                selected_route_section["longitude"])
        )

    # -----------------------------------
    # Sidebar: Clear Button (only visible when active)
    # -----------------------------------
    if st.session_state.mm_range_coords is not None:
        if st.sidebar.button("Clear MM Range"):

            st.session_state.mm_range_coords = None
            st.session_state.mm_weather_df = None

            # set Reset-Flag for MM-selectbox
            st.session_state.reset_mm_range = True

            st.rerun()


    st.sidebar.caption("Proudly presented by Shepherd 🇩🇪 🍺 🥨")

    ## -------------------------------------------------
    # Create Map 
    # -------------------------------------------------
    #st.subheader("🗺 " + trail_name + " Trail Map")


    route_df = pd.read_csv(Trackpoints_file)

    mean_lat = route_df["latitude"].mean()
    mean_lon = route_df["longitude"].mean()

    # Zooming : if Range is active → NO fixed Center-Location
    if st.session_state.mm_range_coords:
        m = folium.Map(zoom_start=9)
    else:
        m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7)

    # prepare complete route (grey)

    all_coordinates = list(zip(route_df["latitude"], route_df["longitude"]))
    folium.PolyLine(
        all_coordinates,
        weight=4,
        color="grey"
    ).add_to(m)

    # prepare route between selected MM-area (bold + blue)
    if st.session_state.mm_range_coords:

        folium.PolyLine(
            st.session_state.mm_range_coords,
            weight=10,
            color="blue",
            opacity=0.85
        ).add_to(m)

        # zoom in automatically
        m.fit_bounds(st.session_state.mm_range_coords)

    # UNCOMMENT FOR WEATHER AT CLICKED LOCATION
    # ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓

    # if st.session_state.clicked_location:
    #     folium.Marker(
    #         location=st.session_state.clicked_location,
    #         icon=folium.Icon(color='blue',icon="cloud", prefix='fa'),        
    #     ).add_to(m)

    # ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

    # -----------------   
    # show MM in map
    # -----------------

    if show_MM:
        mm_group = folium.FeatureGroup(name="Mile Marker")

        for _, row in MM_df.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4,
                color="red",
                fill=False,
                fill_opacity=0.9,
                tooltip=f"{direction} Mile {row['mile_marker']}"
            ).add_to(mm_group)

        mm_group.add_to(m)

    # -----------------   
    # show POIs in map
    # -----------------

    if show_POI:
        POI_group = folium.FeatureGroup(name="POIs")
        POI_df = pd.read_csv(POI_file)
        for _, row in POI_df.iterrows():
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=folium.Popup(
                    f"<b>{row['name']}</b>",
                    max_width=300
                ),
                tooltip=row["name"],
                icon=folium.CustomIcon(
                    emblem_image,
                    icon_size=(22, 22),
                    icon_anchor=(1, 22),
                    popup_anchor=(-3, -76),
                )
            ).add_to(POI_group)
        POI_group.add_to(m)
    # -----------------   
    # show map finally
    # -----------------
    st_data = st_folium(m, use_container_width=True, height=600)

    # -------------------------
    # Format of WX data, 1 table/day
    # -------------------------
    if st.session_state.mm_weather_df is not None:

        df = st.session_state.mm_weather_df

        unique_dates = df["Date"].unique()

        for date in unique_dates:
            st.subheader(f"Weather for {date}")
            daily_df = df[df["Date"] == date].copy()

            st.dataframe(daily_df[[
                "Mile Marker",
                f"Temp Max ({temp_symbol})",
                f"Temp Min ({temp_symbol})",
                "Rain (mm)", "Snow (cm)", "Worst weather"
            ]].reset_index(drop=True), width="stretch")


    # UNCOMMENT FOR WEATHER AT CLICKED LOCATION
    # ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓

    # if st_data and st_data.get("last_clicked"):

    #     clicked_lat = st_data["last_clicked"]["lat"]
    #     clicked_lon = st_data["last_clicked"]["lng"]

    #     new_click = (clicked_lat, clicked_lon)
    #     st.success(f"Selected Location: {clicked_lat:.5f}, {clicked_lon:.5f}")

    #     # if new point is present
    #     if new_click != st.session_state.clicked_location:
    #         st.session_state.clicked_location = new_click
    #         st.rerun()

    # # -------------------------------------------------
    # # load WX for clicked position
    # # -------------------------------------------------
    # if st.session_state.clicked_location:

    #     lat, lon = st.session_state.clicked_location
    #     st.success(f"Selected Location: {lat:.5f}, {lon:.5f}")

    #     if st.button("Load weather for clicked location"):

    #         with st.spinner("Loading weather data..."):
    #             response = fetch_weather(
    #                 [lat],
    #                 [lon],
    #                 start_date,
    #                 end_date,
    #                 temperature_unit
    #             )[0]

    #         daily = response.Daily()
    #         daily_weather_code = daily.Variables(0).ValuesAsNumpy()
    #         daily_weather_human = [wmoData.get(code, f"Unknown ({code})") for code in daily_weather_code]

    #         df = pd.DataFrame({
    #             "Date": pd.date_range(
    #                 start=pd.to_datetime(daily.Time(), unit="s"),
    #                 end=pd.to_datetime(daily.TimeEnd(), unit="s"),
    #                 freq=pd.Timedelta(seconds=daily.Interval()),
    #                 inclusive="left"
    #             ),
    #             f"Temp Max ({temp_symbol})": daily.Variables(1).ValuesAsNumpy(),
    #             f"Temp Min ({temp_symbol})": daily.Variables(2).ValuesAsNumpy(),
    #             "Rain (mm)": daily.Variables(3).ValuesAsNumpy(),
    #             "Snow (cm)": daily.Variables(4).ValuesAsNumpy(),
    #             "Worst weather": daily_weather_human
    #         })

    #         df["Date"] = df["Date"].dt.strftime("%b-%d-%Y")

    #         numeric_cols = df.select_dtypes(include=[np.number]).columns
    #         df[numeric_cols] = np.round(df[numeric_cols]).astype("Int64")

    #         st.session_state.clicked_weather_df = df

    #         if st.session_state.clicked_weather_df is not None:

    #             st.subheader("📍 Weather for selected map location")

    #             st.dataframe(
    #                 st.session_state.clicked_weather_df,
    #                 width="stretch"
    #             )
    # ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
if __name__ == "__main__":
    main()
