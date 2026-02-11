
## Create a list with coordinates for Milemarkers at every x-Mile interval
## Input file: csv with all coordinates of trail
## Output file: csv with coordinates for Milemarkers at every x-Mile interval
## Uses the more precise calculation with pseudo- geodid distances (not simple sinus-like)
## imperial Miles!! 
import pandas as pd
from pyproj import Geod

# ==========================
# Settings
# ==========================
input_csv = "../data/track_coordinates_list_NOBO.csv"
output_csv = "../data/MM_points_list.csv"
interval_miles = 10

interval_meters = interval_miles * 1609.344
geod = Geod(ellps="WGS84")

# ==========================
# import CSV
# ==========================
df = pd.read_csv(input_csv)

# Spaltennamen ggf. anpassen:
latitudes = df["latitude"].values
longitudes = df["longitude"].values

if len(df) < 2:
    raise ValueError("not enough trackpoints.")

# ==========================
# x-milemarker calculation
# ==========================
result = []
total_distance = 0.0
next_target = interval_meters

for i in range(1, len(df)):
    lon1 = longitudes[i - 1]
    lat1 = latitudes[i - 1]
    lon2 = longitudes[i]
    lat2 = latitudes[i]

    az12, az21, segment_length = geod.inv(lon1, lat1, lon2, lat2)

    while total_distance + segment_length >= next_target:
        remaining = next_target - total_distance
        lon_new, lat_new, _ = geod.fwd(lon1, lat1, az12, remaining)

        result.append({
            "mile_marker": round(next_target / 1609.344),
            "latitude": lat_new,
            "longitude": lon_new
        })

        next_target += interval_meters

    total_distance += segment_length

# ==========================
# export new CSV
# ==========================
out_df = pd.DataFrame(result)
out_df.to_csv(output_csv, index=False)

print(f"{len(out_df)} Filename {output_csv}")
print(f"Total lengzh of track: {total_distance / 1609.344:.2f} miles")
