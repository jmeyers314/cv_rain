from datetime import datetime
from time import sleep
import json

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import cm
from meteostat import Daily, Point

# Constants
MM_TO_INCHES = 25.4

start = datetime(1981, 10, 1)
stop = datetime.today()
cv = Point(37.708923, -122.060333, 124.0)  # Castro Valley, CA

# Fetch rainfall data (fetch twice with delay for better reliability)
data = Daily(cv, start, stop).fetch()
sleep(5)
data = Daily(cv, start, stop).fetch()

# Calculate water years (Oct 1 to Sep 30)
years = np.arange(
    start.year + (start.month >= 10),
    stop.year + 1 + (stop.month >= 10)
)

# Calculate cumulative precipitation for each water year
cprcp = {}
for year in years:
    tmin = datetime(year - 1, 10, 1)
    tmax = datetime(year, 10, 1)
    cs = np.nancumsum(data[tmin:tmax]["prcp"])
    if len(cs) > 0:
        cprcp[year] = cs

years = sorted(list(cprcp.keys()))
colors = cm.rainbow(np.linspace(0, 1, len(years)))

# Calculate percentiles for current year
day_num = len(cprcp[years[-1]]) - 1
so_far_this_year = cprcp[years[-1]][day_num]
previous_years_this_date = [cprcp[year][day_num] for year in years[:-1]]
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

ax.set_xticks([0, 31, 61, 92, 123, 151, 182, 212, 243, 274, 305, 335])
ax.set_xticklabels(
    ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
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
