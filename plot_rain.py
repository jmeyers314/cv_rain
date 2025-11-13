from datetime import datetime, timedelta
import json

import numpy as np
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import cm

# Constants
MM_TO_INCHES = 25.4

start = datetime(1981, 8, 1)
stop = datetime.today()
latitude = 37.708923
longitude = -122.060333

# Fetch rainfall data from Open-Meteo
print("Fetching data from Open-Meteo...")
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": start.strftime("%Y-%m-%d"),
    "end_date": stop.strftime("%Y-%m-%d"),
    "daily": "precipitation_sum",
    "timezone": "America/Los_Angeles",
    "precipitation_unit": "mm"
}

response = requests.get(url, params=params)
response.raise_for_status()
api_data = response.json()

# Build a dictionary mapping date strings to precipitation values
date_strings = api_data['daily']['time']
precipitation = api_data['daily']['precipitation_sum']
data = {date_strings[i]: precipitation[i] for i in range(len(date_strings))}

print(f"Fetched {len(data)} days of data")

# Calculate water years (Aug 1 to Jul 31)
years = np.arange(
    start.year + (start.month >= 8),
    stop.year + 1 + (stop.month >= 8)
)

# Calculate cumulative precipitation for each water year
cprcp = {}
for year in years:
    year_start = datetime(year - 1, 8, 1)
    year_end = datetime(year, 8, 1)

    # Collect precipitation for all days in this water year
    year_precip = []
    current_date = year_start

    while current_date < year_end:
        # Don't include future dates
        if current_date > stop:
            break

        date_str = current_date.strftime("%Y-%m-%d")
        precip_value = data.get(date_str, 0.0)
        if precip_value is None:
            precip_value = 0.0

        # Handle leap year: add Feb 29 precipitation to Feb 28
        if current_date.month == 2 and current_date.day == 29:
            # Add Feb 29 to the previous day (Feb 28) and skip this day
            year_precip[-1] += precip_value
        else:
            year_precip.append(precip_value)

        current_date += timedelta(days=1)

    cs = np.nancumsum(year_precip)
    if len(cs) > 0:
        cprcp[year] = cs

years = sorted(list(cprcp.keys()))
colors = cm.rainbow(np.linspace(0, 1, len(years)))

# Calculate percentiles for current year
day_num = len(cprcp[years[-1]]) - 1
so_far_this_year = cprcp[years[-1]][day_num]
previous_years_this_date = [cprcp[year][day_num] for year in years[:-1] if day_num < len(cprcp[year])]
previous_years_end_of_year = [cprcp[year][-1] for year in years[:-1]]
frac = np.nanmean(previous_years_this_date < so_far_this_year)
fracyear = np.nanmean(previous_years_end_of_year < so_far_this_year)

# Generate PNG chart
fig = Figure(figsize=(10, 8))
canvas = FigureCanvas(fig)
ax = fig.add_subplot(111)

for year, c in zip(years, colors):
    lw = 2.0 if year == years[-1] else 0.5
    ax.step(
        np.arange(len(cprcp[year])),
        cprcp[year] / MM_TO_INCHES,
        label=str(year),
        lw=lw,
        c=c
    )

ax.set_xticks([0, 31, 61, 92, 123, 151, 182, 212, 243, 273, 304, 334])
ax.set_xticklabels(
    ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
)
ax.legend(fontsize=6)
ax.set_ylabel("cumulative inches")
ax.set_xlim(0, 365)
ax.set_title(
    f"Castro Valley, CA: Cumulative Rainfall by Water Year\n"
    f"Current Date Percentile: {frac:.0%}   "
    f"End of Year Percentile: {fracyear:.0%}"
)
fig.tight_layout()
canvas.print_figure("rain.png", dpi=300)

# Prepare data for D3.js
output_data = {
    "title": "Castro Valley, CA\nCumulative Rainfall by Water Year",
    "stats": {
        "currentDatePercentile": float(frac),
        "endOfYearPercentile": float(fracyear),
        "soFarThisYear": float(so_far_this_year / MM_TO_INCHES),
        "dayNumber": int(day_num)
    },
    "years": []
}

for year, color in zip(years, colors):
    year_data = {
        "year": int(year),
        "isCurrentYear": bool(year == years[-1]),
        "color": f"rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)})",
        "data": [
            {"day": int(i), "cumulative": float(val / MM_TO_INCHES)}
            for i, val in enumerate(cprcp[year])
        ]
    }
    output_data["years"].append(year_data)

# Write JSON file
with open("rain.json", "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Generated rain.json with data for {len(years)} years")
