#convert gpx to panda


import gpxpy
import pandas as pd

colors = [
    "#FF0000",  # rot
    "#00AA00",  # grün
    "#0000FF",  # blau
    "#FFFF00",  # gelb
    "#FFA500",  # orange
    "#800080"   # lila
]

# Load and parse the GPX file
gpx_file = open('data/Arizona Trail_w_o_POI .gpx', 'r')
gpx = gpxpy.parse(gpx_file)

data = []
i = 0
# Iterate through all tracks
for track in gpx.tracks:
    #print(track.name)
    
    if track.name.startswith('AZT'):
        i = i + 1
        #print(track.name)
        # Iterate through all segments within a track
        for segment in track.segments:
            for point in segment.points:
                data.append({
                    'track_name': track.name,  # Helpful to identify which track
                    #'time': point.time,
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'color' : colors[i % len(colors)]
                    #'elevation': point.elevation
                })

# Create DataFrame
df = pd.DataFrame(data)

df.to_csv('your_file_name.csv', index=False)
#print (df.to_csv())