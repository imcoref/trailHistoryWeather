### get data from external file

import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
from retry_requests import retry
import folium
from streamlit_folium import st_folium

from data.weatherData_decoded import wmoData
from datetime import timedelta, date


# -------------------------------------------------
# File Variables
# -------------------------------------------------

trail_name = 'AZT'

## do not change next lines!
POI_icon_image = 'data/' + trail_name + '_emblem.png'
POI_file = './data/' + trail_name + '_POI.csv'

Trackpoints_file = './data/' + trail_name + '_trackpoints.csv'
MM_file_NOBO = './data/' + trail_name + '_MM_points_list_NOBO.csv' 
MM_file_SOBO = './data/' + trail_name + '_MM_points_list_SOBO.csv' 

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


# -----------------------------------
# Initialisierung Session-State
# -----------------------------------
if "start_date" not in st.session_state:
    st.session_state.start_date = date.today() - timedelta(days=365)

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
st.logo(("data/AZT_emblem.png"))

# -------------------------------------------------
# Sidebar: Settings
# -------------------------------------------------
st.sidebar.header("🏔 " + trail_name +"  History Weather")

#st.sidebar.image("data/AZT_emblem.png")



# -----------------------------------
# Sidebar: Settings Start/End Date Input
# -----------------------------------

# Start Date Input
start_date = st.sidebar.date_input(
    "Start Date",
    key="start_date",
    max_value=date.today() - timedelta(days=1)

)
# End-Date Logic
if start_date != st.session_state.last_start_date:

    st.session_state.end_date = start_date + timedelta(days=1)
    st.session_state.last_start_date = start_date


# End Date Input
end_date = st.sidebar.date_input(
    "End Date",
    key="end_date"
)

# Hardcoded Dates for Test
# start_date = "2025-04-15"
# end_date = "2025-05-04"

# -----------------------------------
# Sidebar: Settings Temperature °C or F
# -----------------------------------
temperature_unit_input = st.sidebar.selectbox(
    "Temperature Unit",
    ["Celsius", "Fahrenheit"]
)
temperature_unit = "celsius" if temperature_unit_input == "Celsius" else "fahrenheit"
temp_symbol = "°C" if temperature_unit == "celsius" else "°F"

# -----------------------------------
# Sidebar: Settings Direction NOBO or SOBO
# -----------------------------------
direction = st.sidebar.radio("Direction", ["NOBO", "SOBO"])
nobo = True if direction == "NOBO" else False


# -----------------------------------
# Sidebar: Settings Mile Marker Range
# -----------------------------------

# Load MM File depending on direction
MM_file = MM_file_NOBO if nobo else MM_file_SOBO
MM_df = pd.read_csv(MM_file)

st.sidebar.subheader("Mile Marker Range")

mm_options = MM_df["mile_marker"].tolist()


# Reset Mile Marker if flag is set ( Start= 0, Stop= LasT)
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
            "WorstWX": daily_weather_human,
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
    # Route-Abschnitt über Distanzindex bestimmen
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
# -------------------------
# Format of WX data, 1 table/day
# -------------------------
if st.session_state.mm_weather_df is not None:

    df = st.session_state.mm_weather_df

    unique_dates = df["Date"].unique()

    for date in unique_dates:
        st.subheader(f"📅 Weather for {date}")
        daily_df = df[df["Date"] == date].copy()

        st.dataframe(daily_df[[
            "Mile Marker",
            f"Temp Max ({temp_symbol})",
            f"Temp Min ({temp_symbol})",
            "Rain (mm)", "Snow (cm)", "WorstWX"
        ]].reset_index(drop=True), width="stretch")
        

st.sidebar.caption("Proudly presented by Shepherd")

## -------------------------------------------------
# Create Map 
# -------------------------------------------------
#st.subheader("🗺 " + trail_name + " Trail Map")

POI_df = pd.read_csv(POI_file)
route_df = pd.read_csv(Trackpoints_file)

mean_lat = POI_df["latitude"].mean()
mean_lon = POI_df["longitude"].mean()

# Wenn Range aktiv → keine feste Center-Location
if st.session_state.mm_range_coords:
    m = folium.Map(zoom_start=9)
else:
    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7)

# complete route (grey)

all_coordinates = list(zip(route_df["latitude"], route_df["longitude"]))
folium.PolyLine(
    all_coordinates,
    weight=4,
    color="grey"
).add_to(m)

# selected MM-area (bold + blue)
if st.session_state.mm_range_coords:

    folium.PolyLine(
        st.session_state.mm_range_coords,
        weight=10,
        color="blue",
        opacity=0.85
    ).add_to(m)

    # zoom in automatically
    m.fit_bounds(st.session_state.mm_range_coords)

# POI Marker
for _, row in POI_df.iterrows():
    folium.Marker(
        location=[row["latitude"], row["longitude"]],
        popup=folium.Popup(
            f"<b>{row['name']}</b>",
            max_width=300
        ),
        tooltip=row["name"],
        icon=folium.CustomIcon(
            POI_icon_image,
            icon_size=(22, 22),
            icon_anchor=(1, 22),
            popup_anchor=(-3, -76),
        )
    ).add_to(m)

if st.session_state.clicked_location:
    folium.Marker(
        location=st.session_state.clicked_location,
        icon=folium.Icon(color='blue',icon="cloud", prefix='fa'),
        
    ).add_to(m)
# show map finally
#st_data = st_folium(m, width=800, height=500)

st_data = st_folium(m, use_container_width=True, height=600)


if st_data and st_data.get("last_clicked"):

    clicked_lat = st_data["last_clicked"]["lat"]
    clicked_lon = st_data["last_clicked"]["lng"]

    new_click = (clicked_lat, clicked_lon)
    st.success(f"Selected Location: {clicked_lat:.5f}, {clicked_lon:.5f}")

    # Nur wenn wirklich neuer Punkt
    if new_click != st.session_state.clicked_location:
        st.session_state.clicked_location = new_click
        st.rerun()

# Wetter für geklickte Position abrufen
# -------------------------------------------------
if st.session_state.clicked_location:

    lat, lon = st.session_state.clicked_location
    st.success(f"Selected Location: {lat:.5f}, {lon:.5f}")

    if st.button("Load weather for clicked location"):

        with st.spinner("Loading weather data..."):

            #lat, lon = st.session_state.clicked_location

            response = fetch_weather(
                [lat],
                [lon],
                start_date,
                end_date,
                temperature_unit
            )[0]

        daily = response.Daily()
        daily_weather_code = daily.Variables(0).ValuesAsNumpy()
        daily_weather_human = [wmoData.get(code, f"Unknown ({code})") for code in daily_weather_code]

        df = pd.DataFrame({
            "Date": pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s"),
                end=pd.to_datetime(daily.TimeEnd(), unit="s"),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            ),
            f"Temp Max ({temp_symbol})": daily.Variables(1).ValuesAsNumpy(),
            f"Temp Min ({temp_symbol})": daily.Variables(2).ValuesAsNumpy(),
            "Rain (mm)": daily.Variables(3).ValuesAsNumpy(),
            "Snow (cm)": daily.Variables(4).ValuesAsNumpy(),
            "WorstWX": daily_weather_human
        })

        df["Date"] = df["Date"].dt.strftime("%b-%d-%Y")

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = np.round(df[numeric_cols]).astype("Int64")

        st.session_state.clicked_weather_df = df

        if st.session_state.clicked_weather_df is not None:

            st.subheader("📍 Weather for selected map location")

            st.dataframe(
                st.session_state.clicked_weather_df,
                width="stretch"
            )

# 