from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import cm
from meteostat import Daily, Point

start = datetime(1982, 1, 1)
stop = datetime.today()
data = Daily(
    Point(37.708923, -122.060333, 124),
    start,
    stop,
).fetch()

years = np.arange(start.year, stop.year + 1 + (stop.month >= 10))
cprcp = {}

for year in years:
    tmin = datetime(year - 1, 10, 1)
    tmax = datetime(year, 10, 1)
    cs = np.nancumsum(data[tmin:tmax]["prcp"])
    if len(cs) > 0:
        cprcp[year] = cs

years = sorted(list(cprcp.keys()))
colors = cm.rainbow(np.linspace(0, 1, len(years)))

day_num = len(cprcp[years[-1]])-1
date_dist = [cprcp[year][day_num] for year in years]
frac = np.nanmean(cprcp[years[-1]][day_num] > date_dist)
fracyear = np.nanmean(cprcp[years[-1]][day_num] > [cprcp[year][-1] for year in years[:-1]])
fig = Figure(figsize=(10, 8))
canvas = FigureCanvas(fig)
ax = fig.add_subplot(111)

for year, c in zip(years, colors):
    if year == years[-1]:
        lw = 2.0
    else:
        lw = 0.5
    ax.plot(cprcp[year] / 25.4, label=str(year), lw=lw, c=c)

ax.set_xticks([0, 31, 61, 92, 123, 151, 182, 212, 243, 274, 305, 335])
ax.set_xticklabels(
    [
        "Oct",
        "Nov",
        "Dec",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
    ]
)
ax.legend(fontsize=6)
ax.set_ylabel("cumulative inches")
ax.set_xlim(0, 365)
ax.set_title(f"Castro Valley, CA: Cumulative Rainfall by Water Year\nCurrent Date Percentile: {frac:.0%}   End of Year Percentile: {fracyear:.0%}")
fig.tight_layout()
canvas.print_figure("rain.png", dpi=300)
