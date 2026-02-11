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


st.set_page_config(page_title="AZT History Weather", page_icon="desert" ,layout="wide")
st.title("🏔 AZT  History Weather")

# -------------------------------------------------
# Sidebar: Settings
# -------------------------------------------------
st.sidebar.header("Settings")

start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")

# Hardcoded Dates für Test
# start_date = "2025-04-15"
# end_date = "2025-05-04"

temperature_unit_input = st.sidebar.selectbox(
    "Temperature Unit",
    ["Celsius", "Fahrenheit"]
)
temperature_unit = "celsius" if temperature_unit_input == "Celsius" else "fahrenheit"
temp_symbol = "°C" if temperature_unit == "celsius" else "°F"

direction = st.sidebar.radio("Direction", ["NOBO", "SOBO"])
nobo = True if direction == "NOBO" else False

# -------------------------------------------------
# Trail Data (may be move to file)
# -------------------------------------------------
locationsNOBO = ["Southern terminus","Sunnyside Canyon","Xing Canelo Pass Rd","Hwy 82 to Patagonia",\
				"Fish Canyon","Interstate 10","Collosal Cave","Grass Shack Campground Saguaro",\
				"Trail Junction  near Mica Mountain","Redington Pass Trailhead resupply box",\
				"Bug Spring Trail Junction","Summerhaven","HWY77 to Oracle","Kelvin Trailhead Parking to Kearny",\
				"HWY 60 to Superior","Roosevelt","Milepost 400","Pine","Xing Hwy87","Mormon Lake","hwy 40 Flagstaff",\
				"Merge of FLG Detour","Milepost 632 near US-180","Mather CG South Rim","Bright Angel CG in GC",\
				"Cottonwood CG in GC","North Rim","Trailhead Telephone near Hwy67","Junction US-89-ALT","Northern Terminus"]
latitudeNOBO = [31.3336136,31.4290650,31.5096048,31.5967690,31.7365750,31.9954083,32.0614502,\
				32.1839456,32.2165171,32.3192480,32.3360443,32.4443565,32.6324577,33.1062821,\
				33.2758827,33.6662847,33.9877172,34.3706765,34.6056473,34.9312582,35.2118000,\
				35.2725260,35.5599078,36.0410005,36.1068106,36.1699952,36.2208716,36.5502691,\
				36.7373770,37.0011160]
longitudeNOBO = [-110.2827364,-110.3679495,-110.5569114,-110.7253987,-110.7300444,-110.6541197,\
				-110.6278259,-110.5927495,-110.5426607,-110.6328970,-110.7193060,-110.7604813,\
				-110.7396259,-110.9782006,-111.1826182,-111.1404035,-111.4832206,-111.4525051,\
				-111.1995434,-111.4954774,-111.5070620,-111.6535303,-111.8205135,-112.1225879,\
				-112.0939578,-112.0410114,-112.0621101,-112.1784389,-112.1881385,-112.0349900]
milemarkerNOBO = [0,13,34,52,75,111,119,135,141,150,164,184,205,263,300,344,400,455,496,535,550,\
					597,632,694,703,711,718,750,767,795]



# SOBO Listen
locationsSOBO = list(reversed(locationsNOBO))
latitudeSOBO = list(reversed(latitudeNOBO))
longitudeSOBO = list(reversed(longitudeNOBO))
milemarkerSOBO = [0]
reversed_milemarkerNOBO = list(reversed(milemarkerNOBO))
for each in range(len(reversed_milemarkerNOBO)-1):
    x = reversed_milemarkerNOBO[each] - reversed_milemarkerNOBO[each+1]
    x += milemarkerSOBO[each]
    milemarkerSOBO.append(x)

if nobo:
    locations, latitude, longitude, milemarker = locationsNOBO, latitudeNOBO, longitudeNOBO, milemarkerNOBO
else:
    locations, latitude, longitude, milemarker = locationsSOBO, latitudeSOBO, longitudeSOBO, milemarkerSOBO

# -------------------------------------------------
# Weather API  Cache
# -------------------------------------------------
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

# -------------------------------------------------
# Create Map
# -------------------------------------------------
st.subheader("🗺 Trail Map")
center_lat, center_lon = np.mean(latitude), np.mean(longitude)
m = folium.Map(location=[center_lat, center_lon], zoom_start=7)


# create Marker
icon_image = 'data/AZT_emblem.png'
for i, loc in enumerate(locations):
    folium.Marker(
        location=[latitude[i], longitude[i]],
        popup=f"{locations[i]} (Mile {milemarker[i]})",
        tooltip=f"{locations[i]}",
        #icon=folium.Icon(color="blue", icon="glyphicon-record")
        icon = folium.CustomIcon(
            icon_image,
            icon_size=(22, 22),
            icon_anchor=(1, 22),
            # shadow_image=shadow_image,
            # shadow_size=(50, 64),
            # shadow_anchor=(4, 62),
            popup_anchor=(-3, -76),
        )
    ).add_to(m)

# # create route sections
route_df = pd.read_csv('./data/track_coordinates_list.csv')

### one Polyline
route_df.head()
coordinates = [tuple(x) for x in route_df[['latitude', 'longitude']].to_numpy()]
folium.PolyLine(coordinates, weight=6).add_to(m)



# ### Nach track_name gruppieren
# for track_name, group in route_df.groupby("track_name"):

#     group = group.reset_index(drop=True)

#     # Segmente innerhalb dieses Tracks zeichnen
#     for i in range(len(group) - 1):
#         start = group.iloc[i]
#         end = group.iloc[i + 1]

#         segment = [
#             (start["latitude"], start["longitude"]),
#             (end["latitude"], end["longitude"])
#         ]

#         folium.PolyLine(
#             segment,
#             weight=6,
#             color=start["color"]  # Farbe vom Startpunkt
#         ).add_to(m)

# Add popup on click
#m.add_child(folium.LatLngPopup())

# Display or save
# m.save("click_picker.html")


# show Map
st_data = st_folium(m, width=800, height=500)


# -------------------------------------------------
# Klick on map- fetch data for that point
# -------------------------------------------------

if st_data and st_data.get("last_clicked"):

    clicked_lat = st_data["last_clicked"]["lat"]
    clicked_lon = st_data["last_clicked"]["lng"]

    st.subheader("📍 Selected Map Location")
    st.write(f"Latitude: {clicked_lat:.5f}")
    st.write(f"Longitude: {clicked_lon:.5f}")

    if st.button("Fetch Weather for Clicked Location"):

        with st.spinner("Fetching weather data..."):

            response = fetch_weather(
                [clicked_lat],
                [clicked_lon],
                start_date,
                end_date,
                temperature_unit
            )[0]

        daily = response.Daily()
        daily_weather_code = daily.Variables(0).ValuesAsNumpy()
        daily_weather_code_human_readable = [wmoData[each] for each in daily_weather_code]

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
            "Worst weather": daily_weather_code_human_readable
        })

        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%b-%d-%Y")

        temp_max_col = f"Temp Max ({temp_symbol})"
        temp_min_col = f"Temp Min ({temp_symbol})"
        rain_col, snow_col = "Rain (mm)", "Snow (cm)"

        for col in [temp_max_col, temp_min_col, rain_col, snow_col]:
            df[col] = np.round(df[col]).astype("Int64")

        st.dataframe(df, width="stretch")
        st.line_chart(df.set_index("Date")[[temp_max_col, temp_min_col]])


# -------------------------------------------------
# Button 1: single Point selection from sidebar - 
# -------------------------------------------------
selected_index = st.sidebar.selectbox(
    "Select Trail Point",
    range(len(locations)),
    format_func=lambda x: f"{locations[x]} (Mile {milemarker[x]})"
)

#  Einzelner Punkt
if st.sidebar.button("Fetch Weather Data for Selected Point"):
    with st.spinner("Fetching weather data for selected point..."):
        response = fetch_weather(
            [latitude[selected_index]],
            [longitude[selected_index]],
            start_date,
            end_date,
            temperature_unit
        )[0]

    daily = response.Daily()
    daily_weather_code = daily.Variables(0).ValuesAsNumpy()
    daily_weather_code_human_readable = [wmoData[each] for each in daily_weather_code]

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
        "Worst weather": daily_weather_code_human_readable
    })

    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%b-%d-%Y")
    temp_max_col = f"Temp Max ({temp_symbol})"
    temp_min_col = f"Temp Min ({temp_symbol})"
    rain_col, snow_col = "Rain (mm)", "Snow (cm)"

    for col in [temp_max_col, temp_min_col, rain_col, snow_col]:
        df[col] = np.round(df[col]).astype("Int64")

    # Farbe
    def color_temp(val):
        if temperature_unit == 'celsius':
            if val <= 0: return "background-color: #4da6ff; color: white"
            elif val >= 30: return "background-color: #ff704d; color: white"
        else:
            if val <= 32: return "background-color: #4da6ff; color: white"
            elif val >= 90: return "background-color: #ff704d; color: white"
        return ""

    def color_rain(val): return "background-color: #80c1ff" if val > 0 else ""
    def color_snow(val): return "background-color: #d9d9d9" if val > 0 else ""

    styled_df = df.style.map(color_temp, subset=[temp_max_col,temp_min_col])\
                        .map(color_rain, subset=[rain_col])\
                        .map(color_snow, subset=[snow_col])

    st.subheader(f"📍 {locations[selected_index]} Mile: {milemarker[selected_index]}")
    st.dataframe(styled_df, width="stretch")
    st.line_chart(df.set_index("Date")[[temp_max_col,temp_min_col]])
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"{locations[selected_index]}_weather.csv",
        mime="text/csv"
    )

# -------------------------------------------------
# Button 2: get all points
# -------------------------------------------------
if st.sidebar.button("Fetch Weather Data for All Points"):
    with st.spinner("Fetching weather data for all points..."):
        responses = fetch_weather(
            latitude,
            longitude,
            start_date,
            end_date,
            temperature_unit
        )

    for i, response in enumerate(responses):
        daily = response.Daily()
        daily_weather_code = daily.Variables(0).ValuesAsNumpy()
        daily_weather_code_human_readable = [wmoData[each] for each in daily_weather_code]

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
            "Worst weather": daily_weather_code_human_readable
        })

        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%b-%d-%Y")
        temp_max_col = f"Temp Max ({temp_symbol})"
        temp_min_col = f"Temp Min ({temp_symbol})"
        rain_col, snow_col = "Rain (mm)", "Snow (cm)"

        for col in [temp_max_col, temp_min_col, rain_col, snow_col]:
            df[col] = np.round(df[col]).astype("Int64")

        #Farbe
        def color_temp(val):
            if temperature_unit == 'celsius':
                if val <= 0: return "background-color: #4da6ff; color: white"
                elif val >= 30: return "background-color: #ff704d; color: white"
            else:
                if val <= 32: return "background-color: #4da6ff; color: white"
                elif val >= 90: return "background-color: #ff704d; color: white"
            return ""

        def color_rain(val): return "background-color: #80c1ff" if val > 0 else ""
        def color_snow(val): return "background-color: #d9d9d9" if val > 0 else ""
        # Styling
        styled_df = df.style.map(color_temp, subset=[temp_max_col,temp_min_col])\
                            .map(color_rain, subset=[rain_col])\
                            .map(color_snow, subset=[snow_col])

        # Akkordeon-Widget
        with st.expander(f"📍 {locations[i]} Mile: {milemarker[i]}", expanded=False):
            st.dataframe(styled_df, width="stretch")
            st.line_chart(df.set_index("Date")[[temp_max_col,temp_min_col]])
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"Download CSV {locations[i]}",
                data=csv,
                file_name=f"{locations[i]}_weather.csv",
                mime="text/csv"
            )
        st.divider()

