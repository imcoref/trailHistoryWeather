# trailHistoryWeather

pip freeze > requirements.txt

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
