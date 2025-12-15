from datetime import datetime, timedelta
import json

import numpy as np
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import cm
from zoneinfo import ZoneInfo

# Constants
MM_TO_INCHES = 25.4

start = datetime(1981, 8, 1)
stop = datetime.today()
latitude = 37.708923
longitude = -122.060333

# Fetch rainfall data from Open-Meteo
print("Fetching historical data from Open-Meteo...")
# Use historical API for data up to 2 days ago
historical_end = stop - timedelta(days=2)
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "start_date": start.strftime("%Y-%m-%d"),
    "end_date": historical_end.strftime("%Y-%m-%d"),
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

print(f"Fetched {len(data)} days of historical data")

# Fetch recent data from forecast API (past 7 days)
print("Fetching recent data from forecast API...")
forecast_url = "https://api.open-meteo.com/v1/forecast"
forecast_params = {
    "latitude": latitude,
    "longitude": longitude,
    "past_days": 7,
    "forecast_days": 0,
    "daily": "precipitation_sum",
    "timezone": "America/Los_Angeles",
    "precipitation_unit": "mm"
}

forecast_response = requests.get(forecast_url, params=forecast_params)
forecast_response.raise_for_status()
forecast_data = forecast_response.json()

# Add recent data to the dictionary (will overwrite any overlapping dates)
forecast_dates = forecast_data['daily']['time']
forecast_precip = forecast_data['daily']['precipitation_sum']
for i in range(len(forecast_dates)):
    data[forecast_dates[i]] = forecast_precip[i]

# Fetch hourly data for today
print("Fetching hourly data for today...")
hourly_params = {
    "latitude": latitude,
    "longitude": longitude,
    "past_hours": 48,  # Get enough hours to cover full current day
    "forecast_hours": 0,  # No forecast data
    "hourly": "precipitation",
    "timezone": "America/Los_Angeles",
    "precipitation_unit": "mm"
}

hourly_response = requests.get(forecast_url, params=hourly_params)
hourly_response.raise_for_status()
hourly_data = hourly_response.json()

# Calculate today's precipitation from hourly data (only actual observations, not forecasts)
today_str = stop.strftime("%Y-%m-%d")
hourly_times = hourly_data['hourly']['time']
hourly_precip = hourly_data['hourly']['precipitation']

# Get current hour in America/Los_Angeles timezone
la_tz = ZoneInfo("America/Los_Angeles")
current_hour = datetime.now(la_tz).hour

today_total = 0.0
today_hours = []

for i in range(len(hourly_times)):
    hour_time = hourly_times[i]
    if hour_time.startswith(today_str):
        # Extract hour from the time string (format: "YYYY-MM-DDTHH:MM")
        hour = int(hour_time.split('T')[1].split(':')[0])

        # Only include hours that have already passed
        if hour <= current_hour:
            precip = hourly_precip[i] if hourly_precip[i] is not None else 0.0
            today_total += precip
            if precip > 0 or len(today_hours) > 0:  # Show all hours once rain starts
                today_hours.append(f"{hour_time}: {precip:.1f} mm")

if today_total > 0 or len(today_hours) > 0:
    data[today_str] = today_total
    print(f"\nToday's hourly data ({today_str}):")
    for hour_info in today_hours:
        print(f"  {hour_info}")
    print(f"  Total so far today: {today_total:.1f} mm ({today_total/MM_TO_INCHES:.2f} inches)")

print(f"\nTotal data points: {len(data)}")
print(f"\nRecent daily data from forecast API:")
for i in range(len(forecast_dates)):
    precip_inches = forecast_precip[i] / MM_TO_INCHES if forecast_precip[i] else 0.0
    print(f"  {forecast_dates[i]}: {forecast_precip[i]:.1f} mm ({precip_inches:.2f} inches)")

# Fetch 16-day precipitation forecast
print("\nFetching 16-day precipitation forecast...")
forecast_precip_params = {
    "latitude": latitude,
    "longitude": longitude,
    "daily": "precipitation_sum",
    "forecast_days": 16,
    "timezone": "America/Los_Angeles",
    "precipitation_unit": "mm"
}

forecast_precip_response = requests.get(forecast_url, params=forecast_precip_params)
forecast_precip_response.raise_for_status()
forecast_precip_data = forecast_precip_response.json()

print("\n16-Day Precipitation Forecast:")
forecast_days = forecast_precip_data['daily']['time']
forecast_amounts = forecast_precip_data['daily']['precipitation_sum']
forecast_total = 0.0
forecast_cumulative = []  # Store cumulative forecast starting from current total
for i in range(len(forecast_days)):
    amount_mm = forecast_amounts[i] if forecast_amounts[i] else 0.0
    amount_inches = amount_mm / MM_TO_INCHES
    forecast_total += amount_mm
    forecast_cumulative.append(forecast_total)
    print(f"  {forecast_days[i]}: {amount_mm:.1f} mm ({amount_inches:.2f} inches)")
print(f"  Total forecast: {forecast_total:.1f} mm ({forecast_total/MM_TO_INCHES:.2f} inches)")

# Calculate water years (Aug 1 to Jul 31)
years = np.arange(
    start.year + (start.month >= 8),
    stop.year + 1 + (stop.month >= 8)
)

# Calculate cumulative precipitation for each water year
cprcp = {}
water_year_dates = {}  # Store dates for each water year
for year in years:
    year_start = datetime(year - 1, 8, 1)
    year_end = datetime(year, 8, 1)

    # Collect precipitation for all days in this water year
    year_precip = []
    year_dates = []
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
            year_dates.append(date_str)

        current_date += timedelta(days=1)

    cs = np.nancumsum(year_precip)
    if len(cs) > 0:
        cprcp[year] = cs
        water_year_dates[year] = year_dates

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
            {
                "day": int(i),
                "date": water_year_dates[year][i],
                "cumulative": float(val / MM_TO_INCHES)
            }
            for i, val in enumerate(cprcp[year])
        ]
    }

    # Add forecast data for current year
    if year == years[-1]:
        current_cumulative = cprcp[year][-1] / MM_TO_INCHES
        current_day = len(cprcp[year]) - 1
        year_data["forecast"] = [
            {
                "day": int(current_day + i + 1),
                "date": forecast_days[i],
                "cumulative": float(current_cumulative + forecast_cumulative[i] / MM_TO_INCHES)
            }
            for i in range(len(forecast_days))
            if current_day + i + 1 < 365  # Don't go past end of water year
        ]

    output_data["years"].append(year_data)

# Write JSON file
with open("rain.json", "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Generated rain.json with data for {len(years)} years")
