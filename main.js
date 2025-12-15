// Load and visualize the rainfall data
d3.json('rain.json?v=' + Date.now()).then(data => {
    createChart(data, false); // Initially don't include forecast

    // Handle forecast checkbox
    d3.select('#include-forecast').on('change', function() {
        d3.select('#chart').selectAll('*').remove();
        createChart(data, this.checked);
    });

    // Redraw on window resize with debounce
    const RESIZE_DEBOUNCE_DELAY = 250;
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const includeForecast = d3.select('#include-forecast').property('checked');
            d3.select('#chart').selectAll('*').remove();
            createChart(data, includeForecast);
        }, RESIZE_DEBOUNCE_DELAY);
    });
}).catch(error => {
    console.error('Error loading data:', error);
});

function createChart(data, includeForecast) {
    // Constants
    const MOBILE_BREAKPOINT = 768;
    const HOVER_DISTANCE_THRESHOLD = 30;
    const DEBOUNCE_DELAY = 250;

    // Detect mobile
    const isMobile = window.innerWidth <= MOBILE_BREAKPOINT;

    // Set up dimensions
    const margin = isMobile
        ? { top: 60, right: 20, bottom: 60, left: 50 }
        : { top: 60, right: 150, bottom: 60, left: 60 };

    const container = d3.select('#chart');
    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = isMobile ? 500 : 800;
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG
    const totalHeight = isMobile
        ? containerHeight + 140  // Extra space for legend below (8 rows * 14px = 112px + padding)
        : containerHeight;

    const svg = container.append('svg')
        .attr('width', containerWidth)
        .attr('height', totalHeight);

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Add title (split into multiple lines if contains \n)
    const titleLines = data.title.split('\n');
    const titleGroup = svg.append('g')
        .attr('transform', `translate(${containerWidth / 2}, 12)`);

    titleLines.forEach((line, i) => {
        titleGroup.append('text')
            .attr('x', 0)
            .attr('y', i * 16)
            .attr('text-anchor', 'middle')
            .style('font-size', '18px')
            .style('font-weight', 'bold')
            .text(line);
    });

    // Prepare data with optional forecast inclusion
    const yearsData = data.years.map(year => {
        if (includeForecast && year.isCurrentYear && year.forecast && year.forecast.length > 0) {
            // Combine observed and forecast data
            return {
                ...year,
                data: [...year.data, ...year.forecast],
                lastObservedDay: year.data.length - 1  // Track where observations end
            };
        }
        return year;
    });

    // Recalculate stats if forecast is included
    let currentStats = data.stats;
    if (includeForecast) {
        const currentYear = yearsData.find(y => y.isCurrentYear);
        if (currentYear && currentYear.lastObservedDay !== undefined) {
            const dayNum = currentYear.data.length - 1;
            const soFarThisYear = currentYear.data[dayNum].cumulative;

            // Calculate percentiles with forecast included
            const completedYears = yearsData.filter(y => !y.isCurrentYear);
            const previousYearsThisDate = completedYears
                .filter(y => dayNum < y.data.length)
                .map(y => y.data[dayNum].cumulative);
            const previousYearsEndOfYear = completedYears.map(y => y.data[y.data.length - 1].cumulative);

            currentStats = {
                currentDatePercentile: previousYearsThisDate.filter(v => v < soFarThisYear).length / previousYearsThisDate.length,
                endOfYearPercentile: previousYearsEndOfYear.filter(v => v < soFarThisYear).length / previousYearsEndOfYear.length,
                soFarThisYear: soFarThisYear,
                dayNumber: dayNum
            };
        }
    }

    // Add stats (recalculated if forecast included)
    const statsText = includeForecast
        ? `Projected Date Percentile (with forecast): ${(currentStats.currentDatePercentile * 100).toFixed(0)}%   Projected End of Year Percentile: ${(currentStats.endOfYearPercentile * 100).toFixed(0)}%`
        : `Current Date Percentile: ${(currentStats.currentDatePercentile * 100).toFixed(0)}%   End of Year Percentile: ${(currentStats.endOfYearPercentile * 100).toFixed(0)}%`;

    svg.append('text')
        .attr('x', containerWidth / 2)
        .attr('y', 12 + titleLines.length * 16 + 8)
        .attr('text-anchor', 'middle')
        .style('font-size', '12px')
        .style('fill', '#666')
        .text(statsText);

    // Set up scales (need to consider forecast data for maxY)
    const xScale = d3.scaleLinear()
        .domain([0, 365])
        .range([0, width]);

    const maxY = d3.max(yearsData, year => d3.max(year.data, d => d.cumulative));
    const yScale = d3.scaleLinear()
        .domain([0, maxY])
        .range([height, 0]);

    // Add alternating horizontal background bands
    const yTicks = yScale.ticks();
    for (let i = 0; i < yTicks.length; i++) {
        g.append('rect')
            .attr('x', 0)
            .attr('y', i === yTicks.length - 1 ? 0 : yScale(yTicks[i + 1]))
            .attr('width', width)
            .attr('height', i === yTicks.length - 1 ? yScale(yTicks[i]) : yScale(yTicks[i]) - yScale(yTicks[i + 1]))
            .attr('fill', i % 2 === 0 ? '#eeeeee' : '#f8f8f8')
            .attr('pointer-events', 'none');
    }

    // Create axes
    const monthTicks = [0, 31, 61, 92, 123, 151, 182, 212, 243, 273, 304, 334];
    const monthLabels = ['Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'];

    const xAxis = d3.axisBottom(xScale)
        .tickValues(monthTicks)
        .tickFormat((d, i) => monthLabels[i]);

    const yAxis = d3.axisLeft(yScale);

    g.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(xAxis);

    g.append('g')
        .call(yAxis);

    // Add axis labels
    g.append('text')
        .attr('class', 'axis-label')
        .attr('transform', 'rotate(-90)')
        .attr('x', -height / 2)
        .attr('y', -40)
        .attr('text-anchor', 'middle')
        .text('Cumulative Inches');

    // Add tooltip
    const tooltip = d3.select('.tooltip');

    // Calculate total rainfall for each year and percentiles
    // Exclude current year from percentile calculations since it's incomplete
    const completedYears = data.years.filter(y => !y.isCurrentYear);
    const yearTotals = completedYears.map(y => ({
        year: y.year,
        total: y.data[y.data.length - 1].cumulative
    }));
    const sortedTotals = yearTotals.map(yt => yt.total).sort((a, b) => a - b);

    // Helper function to calculate percentile
    function getPercentile(value) {
        const belowCount = sortedTotals.filter(t => t < value).length;
        const equalCount = sortedTotals.filter(t => t === value).length;
        // Use (rank / n) * 100 formula where rank = below + equal
        // Min: 1/44 = 2.3%, Max: 44/44 = 100%
        const rank = belowCount + equalCount;
        return (rank / sortedTotals.length * 100).toFixed(0);
    }

    // Helper function to calculate percentile for a specific day across all years
    function getDayPercentile(day, currentValue) {
        const valuesAtThisDay = data.years
            .filter(y => day < y.data.length)
            .map(y => y.data[day].cumulative);
        const belowOrEqualCount = valuesAtThisDay.filter(v => v <= currentValue).length;
        return (belowOrEqualCount / valuesAtThisDay.length * 100).toFixed(0);
    }

    // Helper function to generate tooltip HTML for a year
    function generateYearTooltipHTML(yearData, day = null) {
        const lastDay = yearData.data.length - 1;
        const totalRainfall = yearData.data[lastDay].cumulative;
        const yearPercentile = getPercentile(totalRainfall);

        let html = `<strong>${yearData.year}${yearData.isCurrentYear ? ' (current)' : ''}</strong><br/>`;

        if (day !== null) {
            // Check if this day is in the forecast range
            const isForecast = yearData.lastObservedDay !== undefined && day > yearData.lastObservedDay;

            // Detailed tooltip for chart hover
            const currentDayValue = yearData.data[day].cumulative;
            const fractionOfTotal = (currentDayValue / totalRainfall * 100).toFixed(1);
            const dayPercentile = getDayPercentile(day, currentDayValue);

            // Format date as "Mon DD, YYYY" to include the calendar year
            const dateStr = yearData.data[day].date;
            const date = new Date(dateStr + 'T00:00:00');
            const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

            html += `${formattedDate}${isForecast ? ' (forecast)' : ''}<br/>`;
            html += `Cumulative: ${currentDayValue.toFixed(2)}" (${dayPercentile}%ile for this date)<br/>`;
            html += `${fractionOfTotal}% of year total<br/>`;
            html += `Year total: ${totalRainfall.toFixed(2)}" (${yearPercentile}%ile)`;
            if (isForecast) {
                html += `<br/><em>Includes forecast data</em>`;
            }
        } else {
            // Simple tooltip for legend hover
            html += `Total: ${totalRainfall.toFixed(2)}" (${yearPercentile}%ile)`;
            if (yearData.isCurrentYear) {
                html += `<br/>(${lastDay + 1} days)`;
            }
        }

        return html;
    }

    // Create step line generator (matches matplotlib's ax.step)
    const line = d3.line()
        .x(d => xScale(d.day))
        .y(d => yScale(d.cumulative))
        .curve(d3.curveStepAfter);

    // Draw lines for each year
    const lines = g.selectAll('.year-line')
        .data(yearsData)
        .enter()
        .append('path')
        .attr('class', d => d.isCurrentYear ? 'line current-year' : 'line')
        .attr('d', d => line(d.data))
        .attr('stroke', d => d.color)
        .attr('stroke-width', d => d.isCurrentYear ? 3.75 : 1.5)
        .attr('opacity', d => d.isCurrentYear ? 1 : 0.6)
        .style('pointer-events', 'none');

    // Add vertical line at current date to mark forecast start
    if (includeForecast) {
        const currentYear = yearsData.find(y => y.isCurrentYear);
        if (currentYear && currentYear.lastObservedDay !== undefined) {
            g.append('line')
                .attr('class', 'forecast-divider')
                .attr('x1', xScale(currentYear.lastObservedDay))
                .attr('x2', xScale(currentYear.lastObservedDay))
                .attr('y1', 0)
                .attr('y2', height)
                .attr('stroke', '#999')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '5,5')
                .style('opacity', 0.7)
                .style('pointer-events', 'none');
        }
    }

    // Add vertical line indicator (initially hidden)
    const verticalLine = g.append('line')
        .attr('class', 'vertical-indicator')
        .attr('y1', 0)
        .attr('y2', height)
        .attr('stroke', '#666')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,4')
        .style('opacity', 0)
        .style('pointer-events', 'none');

    // Add horizontal line indicator (initially hidden)
    const horizontalLine = g.append('line')
        .attr('class', 'horizontal-indicator')
        .attr('x1', 0)
        .attr('x2', width)
        .attr('stroke', '#666')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,4')
        .style('opacity', 0)
        .style('pointer-events', 'none');

    // Helper function to find nearest year to mouse position
    function findNearestYear(mouseX, mouseY) {
        const day = Math.round(xScale.invert(mouseX));

        if (day < 0 || day > 365) return null;

        let minDistance = Infinity;
        let nearestYear = null;

        yearsData.forEach(yearData => {
            if (day < yearData.data.length) {
                const yValue = yScale(yearData.data[day].cumulative);
                const distance = Math.abs(mouseY - yValue);

                if (distance < minDistance) {
                    minDistance = distance;
                    nearestYear = yearData;
                }
            }
        });

        // Only return if within reasonable distance (30 pixels)
        if (minDistance < HOVER_DISTANCE_THRESHOLD) {
            return { year: nearestYear, day: day, distance: minDistance };
        }

        return null;
    }

    // Helper function to update line highlighting
    function updateLineHighlight(hoveredYear) {
        lines.each(function(d) {
            const line = d3.select(this);
            const isHovered = hoveredYear && hoveredYear.year === d.year;
            const isCurrent = d.isCurrentYear;

            if (isHovered) {
                // Hovered line: thick
                line.attr('stroke-width', 5)
                    .attr('opacity', 1)
                    .style('filter', 'drop-shadow(0px 0px 4px rgba(0,0,0,0.6))');
            } else if (isCurrent) {
                // Current year (when not hovered): always emphasized
                line.attr('stroke-width', 3.75)
                    .attr('opacity', 1)
                    .style('filter', 'drop-shadow(0px 0px 2px rgba(0,0,0,0.3))');
            } else {
                // All other lines
                line.attr('stroke-width', 1.5)
                    .attr('opacity', 0.6)
                    .style('filter', 'none');
            }
        });
    }

    // Helper function to update legend line highlighting (defined here, called after legendLines is created)
    let updateLegendHighlight = null;

    // Add invisible overlay for mouse tracking
    const overlay = g.append('rect')
        .attr('width', width)
        .attr('height', height)
        .attr('fill', 'none')
        .attr('pointer-events', 'all')
        .style('cursor', 'crosshair')
        .on('mousemove', function(event) {
            const [mouseX, mouseY] = d3.pointer(event);
            const nearest = findNearestYear(mouseX, mouseY);

            // Always show and position crosshair lines
            const day = Math.round(xScale.invert(mouseX));
            if (day >= 0 && day <= 365) {
                const xPos = xScale(day);
                verticalLine
                    .attr('x1', xPos)
                    .attr('x2', xPos)
                    .style('opacity', 0.7);

                horizontalLine
                    .attr('y1', mouseY)
                    .attr('y2', mouseY)
                    .style('opacity', 0.7);
            }

            if (nearest) {
                const d = nearest.year;
                const day = nearest.day;

                updateLineHighlight(d);
                updateLegendHighlight(d.year);

                // Update horizontal line to match the curve point
                const yPos = yScale(d.data[day].cumulative);
                horizontalLine
                    .attr('y1', yPos)
                    .attr('y2', yPos);

                tooltip
                    .html(generateYearTooltipHTML(d, day))
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 10) + 'px')
                    .style('opacity', 1);
            } else {
                updateLineHighlight(null);
                updateLegendHighlight(null);
                tooltip.style('opacity', 0);
            }
        })
        .on('mouseout', function() {
            updateLineHighlight(null);
            updateLegendHighlight(null);
            verticalLine.style('opacity', 0);
            horizontalLine.style('opacity', 0);
            tooltip.style('opacity', 0);
        });

    // Create legend
    const legendItemHeight = isMobile ? 14 : 18;

    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', isMobile
            ? `translate(${margin.left},${containerHeight + 20})`
            : `translate(${containerWidth - margin.right + 10},${margin.top})`);

    const legendItems = legend.selectAll('.legend-item')
        .data(yearsData.slice().reverse()) // Reverse to show most recent on top
        .enter()
        .append('g')
        .attr('class', 'legend-item')
        .attr('transform', (d, i) => {
            // Column-major layout (fill columns first)
            const numCols = isMobile ? 6 : 2;
            const colWidth = isMobile ? 65 : 75;
            const totalYears = yearsData.length;
            const rowsPerCol = Math.ceil(totalYears / numCols);
            const col = Math.floor(i / rowsPerCol);
            const row = i % rowsPerCol;
            return `translate(${col * colWidth},${row * legendItemHeight})`;
        })
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            // Highlight the corresponding line
            const yearData = yearsData.find(y => y.year === d.year);
            updateLineHighlight(yearData);
            updateLegendHighlight(d.year);

            tooltip
                .html(generateYearTooltipHTML(yearData))
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('opacity', 1);
        })
        .on('mouseout', function(event, d) {
            // Reset line appearance
            updateLineHighlight(null);
            updateLegendHighlight(null);

            tooltip.style('opacity', 0);
        });

    // Add invisible wider rectangles for easier hovering over legend lines
    legendItems.append('rect')
        .attr('x', -5)
        .attr('y', 0)
        .attr('width', isMobile ? 60 : 30)
        .attr('height', legendItemHeight)
        .attr('fill', 'transparent')
        .style('cursor', 'pointer')
        .style('pointer-events', 'all')
        .on('mouseover', function(event, d) {
            event.stopPropagation(); // Prevent parent group handler from firing

            const yearData = data.years.find(y => y.year === d.year);
            updateLineHighlight(yearData);
            updateLegendHighlight(d.year);

            tooltip
                .html(generateYearTooltipHTML(yearData))
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .style('opacity', 1);
        })
        .on('mouseout', function(event, d) {
            event.stopPropagation(); // Prevent parent group handler from firing

            updateLineHighlight(null);
            updateLegendHighlight(null);
            tooltip.style('opacity', 0);
        });

    const legendLines = legendItems.append('line')
        .attr('x1', 0)
        .attr('x2', 20)
        .attr('y1', 5)
        .attr('y2', 5)
        .attr('stroke', d => d.color)
        .attr('stroke-width', d => d.isCurrentYear ? 2 : 1.5)
        .style('pointer-events', 'none'); // Let the rectangle handle mouse events

    // Define the legend highlight function now that legendLines exists
    updateLegendHighlight = function(hoveredYear) {
        legendLines.each(function(d) {
            const line = d3.select(this);
            const isHovered = hoveredYear !== null && hoveredYear === d.year;
            const isCurrent = d.isCurrentYear;

            if (isHovered) {
                // Hovered legend line: thick
                line.attr('stroke-width', 4);
            } else if (isCurrent) {
                // Current year: medium
                line.attr('stroke-width', 2);
            } else {
                // All other lines: thin
                line.attr('stroke-width', 1.5);
            }
        });
    };

    legendItems.append('text')
        .attr('x', 25)
        .attr('y', isMobile ? 9 : 10)
        .text(d => d.year)
        .style('font-size', isMobile ? '10px' : '11px')
        .style('font-weight', d => d.isCurrentYear ? 'bold' : 'normal');
}
