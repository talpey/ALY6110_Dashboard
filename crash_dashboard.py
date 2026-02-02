import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page config
st.set_page_config(page_title="MA Crash Analysis", layout="wide")

# Load data
@st.cache_data
def load_data():
    all_crashes = pd.read_csv('dashboard_data_all_crashes_ts.csv')
    fatal_serious = pd.read_csv('dashboard_data_fatal_serious_ts.csv')
    main = pd.read_parquet('dashboard_data_main.parquet')
    return all_crashes, fatal_serious, main

all_crashes_ts, fatal_serious_ts, main_data = load_data()

# Title
st.title("Massachusetts Crash Data Analysis (2003-2024)")
st.markdown("**Focus: Fatal and Serious Injury Crashes**")
st.markdown("---")

# Sidebar filters
st.sidebar.header("Filters")

# Year range
year_min = int(main_data['YEAR'].min())
year_max = int(main_data['YEAR'].max())
year_range = st.sidebar.slider(
    "Year Range",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max)
)

# Severity filter
severity_options = ['All', 'Fatal', 'Serious', 'Other']
severity_filter = st.sidebar.multiselect(
    "Severity",
    options=severity_options,
    default=['Fatal', 'Serious']
)

# Urban type filter
urban_types = ['All'] + sorted(main_data['URBAN_TYPE'].dropna().unique().tolist())
urban_filter = st.sidebar.selectbox("Urban Type", urban_types)

# Road surface filter
road_types = ['All'] + sorted(main_data['ROAD_SURF_COND_DESCR'].dropna().unique().tolist())
road_filter = st.sidebar.selectbox("Road Surface", road_types)

# Light condition filter
light_types = ['All'] + sorted(main_data['AMBNT_LIGHT_DESCR'].dropna().unique().tolist())
light_filter = st.sidebar.selectbox("Light Condition", light_types)

# Age of youngest driver
age_types = ['All'] + sorted(main_data['AGE_DRVR_YNGST'].dropna().unique().tolist())
age_filter = st.sidebar.selectbox("Age of Youngest Driver", age_types)

# Apply filters to main data
filtered_data = main_data[
    (main_data['YEAR'] >= year_range[0]) & 
    (main_data['YEAR'] <= year_range[1])
]

if 'All' not in severity_filter and len(severity_filter) > 0:
    filtered_data = filtered_data[filtered_data['SEVERITY_GROUP'].isin(severity_filter)]

if urban_filter != 'All':
    filtered_data = filtered_data[filtered_data['URBAN_TYPE'] == urban_filter]

if road_filter != 'All':
    filtered_data = filtered_data[filtered_data['ROAD_SURF_COND_DESCR'] == road_filter]

if light_filter != 'All':
    filtered_data = filtered_data[filtered_data['AMBNT_LIGHT_DESCR'] == light_filter]

if age_filter != 'All':
    filtered_data = filtered_data[filtered_data['AGE_DRVR_YNGST'] == age_filter]

# Summary stats
col1, col2, col3, col4 = st.columns(4)

# Get total from ALL data (not filtered by severity)
total_all_data = main_data[
    (main_data['YEAR'] >= year_range[0]) & 
    (main_data['YEAR'] <= year_range[1])
]
if urban_filter != 'All':
    total_all_data = total_all_data[total_all_data['URBAN_TYPE'] == urban_filter]

if road_filter != 'All':
    total_all_data = total_all_data[total_all_data['ROAD_SURF_COND_DESCR'] == road_filter]

if light_filter != 'All':
    total_all_data = total_all_data[total_all_data['AMBNT_LIGHT_DESCR'] == light_filter]

total_crashes = total_all_data['crash_count'].sum()
fatal_crashes = total_all_data[total_all_data['SEVERITY_GROUP'] == 'Fatal']['crash_count'].sum()
serious_crashes = total_all_data[total_all_data['SEVERITY_GROUP'] == 'Serious']['crash_count'].sum()
fatal_serious_pct = (fatal_crashes + serious_crashes) / total_crashes * 100 if total_crashes > 0 else 0

col1.metric("Total Crashes", f"{total_crashes:,}")
col2.metric("Fatal Crashes", f"{fatal_crashes:,}")
col3.metric("Serious Crashes", f"{serious_crashes:,}")
col4.metric("Fatal/Serious %", f"{fatal_serious_pct:.2f}%")

st.markdown("---")

# ========== VISUAL 1: DUAL PANEL TIME SERIES ==========
st.header("Crash Trends Over Time")

# Filter time series data
all_crashes_filtered = all_crashes_ts[
    (all_crashes_ts['YEAR'] >= year_range[0]) & 
    (all_crashes_ts['YEAR'] <= year_range[1])
]
fatal_serious_filtered = fatal_serious_ts[
    (fatal_serious_ts['YEAR'] >= year_range[0]) & 
    (fatal_serious_ts['YEAR'] <= year_range[1])
]

# Create subplot
fig = make_subplots(
    rows=2, cols=1,
    subplot_titles=("All Crashes", "Fatal & Serious Crashes"),
    vertical_spacing=0.12,
    row_heights=[0.5, 0.5]
)

# Top panel - all crashes
fig.add_trace(
    go.Scatter(
        x=all_crashes_filtered['YEAR'],
        y=all_crashes_filtered['crash_count'],
        mode='lines',
        line=dict(color='steelblue', width=2),
        name='All Crashes'
    ),
    row=1, col=1
)

# Bottom panel - fatal and serious
for severity in ['Serious', 'Fatal']:
    data = fatal_serious_filtered[fatal_serious_filtered['SEVERITY_GROUP'] == severity]
    color = '#ff7f0e' if severity == 'Serious' else '#d62728'
    fig.add_trace(
        go.Scatter(
            x=data['YEAR'],
            y=data['crash_count'],
            mode='lines',
            fill='tonexty' if severity == 'Fatal' else 'tozeroy',
            line=dict(color=color, width=2),
            name=severity,
            stackgroup='one'
        ),
        row=2, col=1
    )

fig.update_xaxes(title_text="Year", row=2, col=1)
fig.update_yaxes(title_text="Count", row=1, col=1)
fig.update_yaxes(title_text="Count", row=2, col=1)

# Force y-axis to start at 0 for both panels
fig.update_yaxes(rangemode='tozero', row=1, col=1)
fig.update_yaxes(rangemode='tozero', row=2, col=1)

fig.update_layout(height=600, showlegend=True, hovermode='x unified')

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ========== VISUAL 2: GEOGRAPHIC BREAKDOWN ==========
st.header("Geographic Distribution")

# Calculate Fatal/Serious rate by city using ALL severities (not filtered by severity)
# Use total_all_data which has all filters EXCEPT severity
geo_all = total_all_data.groupby('CITY_TOWN_NAME')['crash_count'].sum().reset_index()
geo_all.columns = ['CITY_TOWN_NAME', 'total_crashes']

geo_fatal_serious = total_all_data[total_all_data['SEVERITY_GROUP'].isin(['Fatal', 'Serious'])]
geo_fs = geo_fatal_serious.groupby('CITY_TOWN_NAME')['crash_count'].sum().reset_index()
geo_fs.columns = ['CITY_TOWN_NAME', 'fatal_serious_crashes']

geo_merged = geo_all.merge(geo_fs, on='CITY_TOWN_NAME', how='left').fillna(0)
geo_merged['fatal_serious_rate'] = (geo_merged['fatal_serious_crashes'] / geo_merged['total_crashes'] * 100)

# Filter to cities with at least 100 crashes and get top 20 by rate
geo_merged = geo_merged[geo_merged['total_crashes'] >= 100]
geo_merged = geo_merged.sort_values('fatal_serious_rate', ascending=False).head(20)

fig_geo = px.bar(
    geo_merged,
    x='fatal_serious_rate',
    y='CITY_TOWN_NAME',
    orientation='h',
    title='Fatal/Serious Crash Rate by City (Top 20, min 100 crashes)',
    labels={'fatal_serious_rate': 'Fatal/Serious Rate (%)', 'CITY_TOWN_NAME': 'City/Town'},
    hover_data={'total_crashes': True, 'fatal_serious_crashes': True}
)
fig_geo.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_geo, use_container_width=True)

st.markdown("---")

# ========== VISUAL 3: CONTRIBUTING FACTORS ==========
st.header("Risk Factors Analysis")

# Create a baseline dataset with ONLY year filter (no other filters)
# This ensures risk rates are always calculated against all conditions
baseline_data = main_data[
    (main_data['YEAR'] >= year_range[0]) & 
    (main_data['YEAR'] <= year_range[1])
]

# Calculate Fatal/Serious rate by road surface condition using baseline
road_all = baseline_data.groupby('ROAD_SURF_COND_DESCR')['crash_count'].sum().reset_index()
road_all.columns = ['ROAD_SURF_COND_DESCR', 'total_crashes']

road_fs = baseline_data[baseline_data['SEVERITY_GROUP'].isin(['Fatal', 'Serious'])]
road_fs_grouped = road_fs.groupby('ROAD_SURF_COND_DESCR')['crash_count'].sum().reset_index()
road_fs_grouped.columns = ['ROAD_SURF_COND_DESCR', 'fatal_serious_crashes']

road_merged = road_all.merge(road_fs_grouped, on='ROAD_SURF_COND_DESCR', how='left').fillna(0)
road_merged['fatal_serious_rate'] = (road_merged['fatal_serious_crashes'] / road_merged['total_crashes'] * 100)
road_merged = road_merged[road_merged['total_crashes'] >= 100]  # Min 100 crashes
road_merged = road_merged.sort_values('fatal_serious_rate', ascending=False).head(10)

fig_road = px.bar(
    road_merged,
    x='fatal_serious_rate',
    y='ROAD_SURF_COND_DESCR',
    orientation='h',
    title='Fatal/Serious Rate by Road Surface Condition (baseline rates, min 100 crashes)',
    labels={'fatal_serious_rate': 'Fatal/Serious Rate (%)', 'ROAD_SURF_COND_DESCR': 'Road Surface'},
    hover_data={'total_crashes': True, 'fatal_serious_crashes': True}
)
fig_road.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_road, use_container_width=True)

# Calculate Fatal/Serious rate by light condition using baseline
light_all = baseline_data.groupby('AMBNT_LIGHT_DESCR')['crash_count'].sum().reset_index()
light_all.columns = ['AMBNT_LIGHT_DESCR', 'total_crashes']

light_fs = baseline_data[baseline_data['SEVERITY_GROUP'].isin(['Fatal', 'Serious'])]
light_fs_grouped = light_fs.groupby('AMBNT_LIGHT_DESCR')['crash_count'].sum().reset_index()
light_fs_grouped.columns = ['AMBNT_LIGHT_DESCR', 'fatal_serious_crashes']

light_merged = light_all.merge(light_fs_grouped, on='AMBNT_LIGHT_DESCR', how='left').fillna(0)
light_merged['fatal_serious_rate'] = (light_merged['fatal_serious_crashes'] / light_merged['total_crashes'] * 100)
light_merged = light_merged[light_merged['total_crashes'] >= 100]  # Min 100 crashes
light_merged = light_merged.sort_values('fatal_serious_rate', ascending=False).head(10)

fig_light = px.bar(
    light_merged,
    x='fatal_serious_rate',
    y='AMBNT_LIGHT_DESCR',
    orientation='h',
    title='Fatal/Serious Rate by Light Condition (baseline rates, min 100 crashes)',
    labels={'fatal_serious_rate': 'Fatal/Serious Rate (%)', 'AMBNT_LIGHT_DESCR': 'Light Condition'},
    hover_data={'total_crashes': True, 'fatal_serious_crashes': True}
)
fig_light.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_light, use_container_width=True)

st.markdown("---")

# ========== VISUAL 4: TEMPORAL PATTERNS - HEATMAP ==========
st.header("Temporal Patterns")

# Create heatmap data: Hour vs Day of Week
day_order = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 
             4: 'Friday', 5: 'Saturday', 6: 'Sunday'}

heatmap_data = filtered_data.groupby(['HOUR', 'DAY_OF_WEEK'])['crash_count'].sum().reset_index()
heatmap_pivot = heatmap_data.pivot(index='HOUR', columns='DAY_OF_WEEK', values='crash_count').fillna(0)

# Rename columns to day names
heatmap_pivot.columns = [day_order[col] for col in heatmap_pivot.columns]

fig_heatmap = px.imshow(
    heatmap_pivot,
    labels=dict(x="Day of Week", y="Hour of Day", color="Crash Count"),
    x=heatmap_pivot.columns,
    y=heatmap_pivot.index,
    color_continuous_scale='YlOrRd',
    aspect='auto',
    title='Crash Frequency by Hour and Day of Week'
)
fig_heatmap.update_layout(height=600)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

# ========== VISUAL 5: FATAL VS SERIOUS COMPARISON ==========
st.header("Fatal vs Serious: Pattern Differences")

# Filter to just Fatal and Serious
fatal_serious_data = filtered_data[filtered_data['SEVERITY_GROUP'].isin(['Fatal', 'Serious'])]

# Hour distribution comparison - normalized to show relative frequency
hour_severity = fatal_serious_data.groupby(['HOUR', 'SEVERITY_GROUP'])['crash_count'].sum().reset_index()

# Normalize each severity group to percentage
for severity in ['Fatal', 'Serious']:
    mask = hour_severity['SEVERITY_GROUP'] == severity
    total = hour_severity.loc[mask, 'crash_count'].sum()
    hour_severity.loc[mask, 'percentage'] = (hour_severity.loc[mask, 'crash_count'] / total) * 100

fig_hour_comp = px.line(
    hour_severity,
    x='HOUR',
    y='percentage',
    color='SEVERITY_GROUP',
    title='Fatal vs Serious: Hour of Day Pattern (% of each severity)',
    labels={'percentage': 'Percentage (%)', 'HOUR': 'Hour', 'SEVERITY_GROUP': 'Severity'},
    markers=True,
    color_discrete_map={'Fatal': '#d62728', 'Serious': '#ff7f0e'}
)
fig_hour_comp.update_layout(height=500)
st.plotly_chart(fig_hour_comp, use_container_width=True)

# Light condition comparison - normalized
light_severity = fatal_serious_data.groupby(['AMBNT_LIGHT_DESCR', 'SEVERITY_GROUP'])['crash_count'].sum().reset_index()

# Normalize each severity group to percentage
for severity in ['Fatal', 'Serious']:
    mask = light_severity['SEVERITY_GROUP'] == severity
    total = light_severity.loc[mask, 'crash_count'].sum()
    light_severity.loc[mask, 'percentage'] = (light_severity.loc[mask, 'crash_count'] / total) * 100

# Sort by total percentage
light_severity_sorted = light_severity.groupby('AMBNT_LIGHT_DESCR')['percentage'].sum().reset_index()
light_severity_sorted = light_severity_sorted.sort_values('percentage', ascending=False).head(10)
top_conditions = light_severity_sorted['AMBNT_LIGHT_DESCR'].tolist()
light_severity = light_severity[light_severity['AMBNT_LIGHT_DESCR'].isin(top_conditions)]

fig_light_comp = px.bar(
    light_severity,
    x='percentage',
    y='AMBNT_LIGHT_DESCR',
    color='SEVERITY_GROUP',
    orientation='h',
    title='Fatal vs Serious: Light Conditions (% of each severity)',
    labels={'percentage': 'Percentage (%)', 'AMBNT_LIGHT_DESCR': 'Light Condition'},
    color_discrete_map={'Fatal': '#d62728', 'Serious': '#ff7f0e'},
    barmode='group'
)
fig_light_comp.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_light_comp, use_container_width=True)

# Age group comparison - normalized
st.subheader("Age Group Analysis")

age_severity = fatal_serious_data.groupby(['AGE_DRVR_YNGST', 'SEVERITY_GROUP'])['crash_count'].sum().reset_index()

# Normalize each severity group to percentage
for severity in ['Fatal', 'Serious']:
    mask = age_severity['SEVERITY_GROUP'] == severity
    total = age_severity.loc[mask, 'crash_count'].sum()
    age_severity.loc[mask, 'percentage'] = (age_severity.loc[mask, 'crash_count'] / total) * 100

# Define age order for proper sorting - complete age ranges
age_order = ['Under 16', '16-17', '18-20', '21-24', '25-34', '35-44', '45-54', '55-64', '65-74', '75-84', '85+', 'Unknown']
age_severity['AGE_DRVR_YNGST'] = pd.Categorical(age_severity['AGE_DRVR_YNGST'], categories=age_order, ordered=True)
age_severity = age_severity.sort_values('AGE_DRVR_YNGST')

fig_age_comp = px.bar(
    age_severity,
    x='AGE_DRVR_YNGST',
    y='percentage',
    color='SEVERITY_GROUP',
    title='Fatal vs Serious Crashes by Age of Youngest Driver (% of each severity)',
    labels={'percentage': 'Percentage (%)', 'AGE_DRVR_YNGST': 'Age Group'},
    color_discrete_map={'Fatal': '#d62728', 'Serious': '#ff7f0e'},
    barmode='group'
)
fig_age_comp.update_layout(height=500, xaxis_tickangle=-45)
st.plotly_chart(fig_age_comp, use_container_width=True)

st.markdown("---")

# Footer
st.caption("Data Source: Massachusetts Crash Data (2003-2024)")
st.caption("Dashboard created for ALY6110 - Northeastern University")