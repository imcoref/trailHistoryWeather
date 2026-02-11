#convert gpx to csv
# ==========================
# Settings
# ==========================

# set next line to 'False' after making desired changes in row 44
explore_gpx_file_for_multiple_tracks = False
input_file_name = '../data/PCT.gpx'
output_file_name ='../data/track_coordinates_list'




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
gpx_file = open(input_file_name, 'r')
gpx = gpxpy.parse(gpx_file)

data = []
i = 0

if explore_gpx_file_for_multiple_tracks == True:
    for track in gpx.tracks:
        print(track.name)
   
else:
     # Iterate through all tracks
    for track in gpx.tracks:
        # depending on tracks in your file, make changes to next line. 
        # we only want desired tracks from file
        if track.name.startswith('CA') or track.name.startswith('OR') or track.name.startswith('WA') :
            i = i + 1
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

    df.to_csv(output_file_name + '_NOBO' + '.csv', index=False)
     
    # df_reversed = df[::-1]
    # df_reversed.to_csv(output_file_name + '_SOBO' + '.csv', index=False)