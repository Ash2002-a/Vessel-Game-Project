import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import ast

# Set page configuration
st.set_page_config(
    page_title="Vessel Cutting Game Analysis",
    page_icon="🔬",
    layout="wide"
)

# Helper functions


def parse_path_points(points_str):
    """Parse the PATH_POINTS JSON string to a list of points"""
    try:
        # Try to parse as a JSON string
        return json.loads(points_str)
    except (json.JSONDecodeError, TypeError):
        try:
            # Try to parse as a Python literal
            return ast.literal_eval(points_str)
        except (SyntaxError, ValueError, TypeError):
            # Return empty list if parsing fails
            return []


def calculate_movement(df):
    """Calculate movement between consecutive points"""
    df = df.sort_values('TIMESTAMP')
    df['X_DIFF'] = df['X_POSITION'].diff()
    df['Y_DIFF'] = df['Y_POSITION'].diff()
    df['MOVEMENT'] = np.sqrt(df['X_DIFF']**2 + df['Y_DIFF']**2)
    return df


def calculate_time_difference(start_time, end_time):
    """Calculate time difference in seconds"""
    try:
        # Try to convert to datetime if they're strings
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        if isinstance(end_time, str):
            end_time = pd.to_datetime(end_time)

        # Calculate difference in seconds
        return (end_time - start_time).total_seconds()
    except:
        return None


# Main app header
st.title("🩺 Keyhole Surgery Game Analysis")
st.markdown("""
This application analyses data from the Blood Vessel Cutting Game to measure surgical performance based on the UCL research study objectives:

1. **Instrument Efficiency**: How efficiently instruments are used based on total movement
2. **Task Completion Time**: How quickly tasks are completed, measured by time taken
3. **Peripheral Awareness**: How well participants notice events outside the main focus, measured by response speed
4. **Distraction Management**: How external distractions affect focus and error rates
""")

# Sidebar for navigation
st.sidebar.title("Navigation")
selected_page = st.sidebar.radio(
    "Go to",
    ["Data Upload", "Instrument Efficiency", "Task Completion",
        "Peripheral Awareness", "Distraction Management", "Dashboard"]
)

# Initialize session state for storing data
if 'mouse_data' not in st.session_state:
    st.session_state.mouse_data = None
if 'vessel_data' not in st.session_state:
    st.session_state.vessel_data = None
if 'processed' not in st.session_state:
    st.session_state.processed = False

# Data Upload Page
if selected_page == "Data Upload":
    st.header("Upload Game Data")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Mouse Tracking Data")
        mouse_file = st.file_uploader("Upload Mouse Tracking CSV", type=[
                                      "csv"], key="mouse_upload")
        if mouse_file is not None:
            try:
                st.session_state.mouse_data = pd.read_csv(mouse_file)
                st.success(
                    f"Successfully loaded mouse tracking data with {len(st.session_state.mouse_data)} records")
                st.dataframe(st.session_state.mouse_data.head())
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    with col2:
        st.subheader("Vessel Creation Data")
        vessel_file = st.file_uploader("Upload Vessel Creation CSV", type=[
                                       "csv"], key="vessel_upload")
        if vessel_file is not None:
            try:
                st.session_state.vessel_data = pd.read_csv(vessel_file)
                st.success(
                    f"Successfully loaded vessel data with {len(st.session_state.vessel_data)} records")
                st.dataframe(st.session_state.vessel_data.head())
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")

    # Process data when both files are uploaded
    if st.session_state.mouse_data is not None and st.session_state.vessel_data is not None:
        st.subheader("Process Data")
        if st.button("Process Data for Analysis"):
            with st.spinner("Processing data..."):
                try:
                    # Convert timestamps
                    st.session_state.mouse_data['TIMESTAMP'] = pd.to_datetime(
                        st.session_state.mouse_data['TIMESTAMP'])
                    st.session_state.vessel_data['TIMESTAMP'] = pd.to_datetime(
                        st.session_state.vessel_data['TIMESTAMP'])

                    # Convert boolean columns
                    for col in ['IS_CUTTING', 'FIELD_OF_VIEW']:
                        if col in st.session_state.mouse_data.columns:
                            try:
                                st.session_state.mouse_data[col] = st.session_state.mouse_data[col].astype(
                                    bool)
                            except:
                                st.warning(
                                    f"Could not convert {col} to boolean. Treating as string.")

                    for col in ['IS_CORRECT', 'IS_CUT', 'IS_INTERTWINED']:
                        if col in st.session_state.vessel_data.columns:
                            try:
                                st.session_state.vessel_data[col] = st.session_state.vessel_data[col].astype(
                                    bool)
                            except:
                                st.warning(
                                    f"Could not convert {col} to boolean. Treating as string.")

                    # Parse PATH_POINTS if available
                    if 'PATH_POINTS' in st.session_state.vessel_data.columns:
                        try:
                            st.session_state.vessel_data['PATH_POINTS_PARSED'] = st.session_state.vessel_data['PATH_POINTS'].apply(
                                parse_path_points)
                        except:
                            st.warning(
                                "Could not parse PATH_POINTS column. Some analyses might be limited.")

                    st.session_state.processed = True
                    st.success(
                        "Data processed successfully! You can now navigate to the analysis pages.")
                except Exception as e:
                    st.error(f"Error processing data: {str(e)}")

    # Display a data not ready message if not all data is available
    if not st.session_state.processed:
        st.info("Please upload both datasets and process them to enable analysis.")

# Check if data is ready for analysis
if selected_page != "Data Upload":
    if not st.session_state.processed:
        st.warning(
            "Please upload and process the data first on the Data Upload page.")
        st.stop()

# Instrument Efficiency Analysis
if selected_page == "Instrument Efficiency":
    st.header("Objective 1: Efficiency of Instrument Use")
    st.markdown("""
    This analysis measures how efficiently the surgical instruments are used, based on:
    - Total movement distance (in pixels)
    - Economy of movement (movement per successful action)
    - Movement patterns across different game levels
    """)

    try:
        # Calculate total mouse movement
        mouse_movement = calculate_movement(st.session_state.mouse_data.copy())
        total_movement = mouse_movement['MOVEMENT'].sum()
        avg_movement_per_point = mouse_movement['MOVEMENT'].mean()

        # Movement metrics
        st.subheader("Key Movement Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Movement", f"{total_movement:.0f} px")
        with col2:
            st.metric("Avg. Movement Per Point",
                      f"{avg_movement_per_point:.2f} px")
        with col3:
            # Calculate efficiency as ratio of distance to successful cuts
            successful_cuts = st.session_state.vessel_data[(st.session_state.vessel_data['EVENT'] == 'cut') & (
                st.session_state.vessel_data['IS_CORRECT'] == True)].shape[0]
            if successful_cuts > 0:
                movement_per_success = total_movement / successful_cuts
                st.metric("Movement Per Successful Cut",
                          f"{movement_per_success:.0f} px")
            else:
                st.metric("Movement Per Successful Cut", "N/A")

        # Movement per level
        if 'LEVEL' in mouse_movement.columns:
            st.subheader("Movement Analysis by Level")

            level_movement = mouse_movement.groupby(
                'LEVEL')['MOVEMENT'].sum().reset_index()
            level_avg_movement = mouse_movement.groupby(
                'LEVEL')['MOVEMENT'].mean().reset_index()
            level_movement['LEVEL'] = level_movement['LEVEL'].astype(str)
            level_avg_movement['LEVEL'] = level_avg_movement['LEVEL'].astype(
                str)

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(level_movement, x='LEVEL', y='MOVEMENT',
                             title='Total Movement by Level',
                             labels={'LEVEL': 'Level', 'MOVEMENT': 'Movement (pixels)'})
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(level_avg_movement, x='LEVEL', y='MOVEMENT',
                             title='Average Movement per Action by Level',
                             labels={'LEVEL': 'Level', 'MOVEMENT': 'Avg Movement (pixels)'})
                st.plotly_chart(fig, use_container_width=True)

        # Movement patterns
        st.subheader("Movement Patterns Over Time")

        # Group data by time intervals
        mouse_movement['TIME_BUCKET'] = mouse_movement['TIMESTAMP'].dt.floor(
            '1S')
        time_series = mouse_movement.groupby(
            'TIME_BUCKET')['MOVEMENT'].sum().reset_index()

        fig = px.line(time_series, x='TIME_BUCKET', y='MOVEMENT',
                      title='Movement Over Time',
                      labels={'TIME_BUCKET': 'Time', 'MOVEMENT': 'Movement (pixels)'})
        st.plotly_chart(fig, use_container_width=True)

        # Movement heatmap
        st.subheader("Movement Density Heatmap")

        # Create a 2D histogram heatmap of mouse positions
        fig = px.density_heatmap(
            mouse_movement,
            x='X_POSITION',
            y='Y_POSITION',
            title='Mouse Movement Heatmap',
            labels={'X_POSITION': 'X Position', 'Y_POSITION': 'Y Position'}
        )
        fig.update_layout(coloraxis_colorbar=dict(title='Frequency'))
        st.plotly_chart(fig, use_container_width=True)

        # Cutting vs. non-cutting movement
        if 'IS_CUTTING' in mouse_movement.columns:
            st.subheader("Cutting vs. Non-Cutting Movement Analysis")

            cutting_movement = mouse_movement.groupby(
                'IS_CUTTING')['MOVEMENT'].sum().reset_index()
            cutting_movement['IS_CUTTING'] = cutting_movement['IS_CUTTING'].map(
                {True: 'Cutting', False: 'Navigating'})

            fig = px.pie(
                cutting_movement,
                values='MOVEMENT',
                names='IS_CUTTING',
                title='Movement Distribution: Cutting vs. Navigating',
                color_discrete_sequence=px.colors.sequential.Blues
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error analyzing instrument efficiency: {str(e)}")

# Task Completion Time Analysis
elif selected_page == "Task Completion":
    st.header("Objective 2: Task Completion Time")
    st.markdown("""
    This analysis measures how quickly tasks are completed, based on:
    - Time taken to cut vessels
    - Speed comparison between correct and incorrect vessels
    - Performance changes across game levels
    """)

    try:
        # Identify vessel events
        vessel_cuts = st.session_state.vessel_data[st.session_state.vessel_data['EVENT'] == 'cut']
        vessel_creates = st.session_state.vessel_data[st.session_state.vessel_data['EVENT'] == 'created']

        # Calculate time between vessel creation and cutting
        if not vessel_cuts.empty and not vessel_creates.empty:
            # Merge to get creation and cut times for each vessel
            vessel_times = pd.merge(
                vessel_creates[['VESSEL_ID',
                                'TIMESTAMP', 'IS_CORRECT', 'LEVEL']],
                vessel_cuts[['VESSEL_ID', 'TIMESTAMP']],
                on='VESSEL_ID',
                suffixes=('_create', '_cut')
            )

            # Calculate time difference
            vessel_times['TIME_TO_CUT'] = vessel_times.apply(
                lambda row: calculate_time_difference(
                    row['TIMESTAMP_create'], row['TIMESTAMP_cut']),
                axis=1
            )

            # Basic time metrics
            st.subheader("Task Completion Metrics")
            col1, col2, col3 = st.columns(3)

            with col1:
                avg_time_overall = vessel_times['TIME_TO_CUT'].mean()
                st.metric("Avg. Time to Cut (Overall)",
                          f"{avg_time_overall:.2f}s")

            with col2:
                correct_time = vessel_times[vessel_times['IS_CORRECT']]['TIME_TO_CUT'].mean(
                )
                st.metric("Avg. Time for Correct Vessels",
                          f"{correct_time:.2f}s")

            with col3:
                incorrect_time = vessel_times[~vessel_times['IS_CORRECT']]['TIME_TO_CUT'].mean(
                )
                st.metric("Avg. Time for Incorrect Vessels",
                          f"{incorrect_time:.2f}s")

            # Efficiency metrics
            st.subheader("Task Efficiency Metrics")

            col1, col2 = st.columns(2)

            with col1:
                # Calculate cutting speed (vessels per minute)
                total_time = (vessel_times['TIMESTAMP_cut'].max(
                ) - vessel_times['TIMESTAMP_cut'].min()).total_seconds() / 60
                if total_time > 0:
                    cutting_speed = len(vessel_times) / total_time
                    st.metric("Vessels Cut Per Minute", f"{cutting_speed:.2f}")
                else:
                    st.metric("Vessels Cut Per Minute", "N/A")

            with col2:
                # Calculate correct vessel ratio
                correct_ratio = vessel_times['IS_CORRECT'].mean() * 100
                st.metric("Correct Vessel Selection Rate",
                          f"{correct_ratio:.1f}%")

            # Time by vessel type (correct vs incorrect)
            st.subheader("Time Analysis by Vessel Type")

            avg_time_by_type = vessel_times.groupby(
                'IS_CORRECT')['TIME_TO_CUT'].mean().reset_index()
            avg_time_by_type['IS_CORRECT'] = avg_time_by_type['IS_CORRECT'].map(
                {True: 'Correct', False: 'Incorrect'})

            fig = px.bar(avg_time_by_type, x='IS_CORRECT', y='TIME_TO_CUT',
                         title='Average Time to Cut by Vessel Type',
                         labels={'IS_CORRECT': 'Vessel Type', 'TIME_TO_CUT': 'Time (seconds)'})
            st.plotly_chart(fig, use_container_width=True)

            # Time by level
            if 'LEVEL' in vessel_times.columns:
                st.subheader("Performance Analysis by Level")

                avg_time_by_level = vessel_times.groupby(
                    'LEVEL')['TIME_TO_CUT'].mean().reset_index()
                avg_time_by_level['LEVEL'] = avg_time_by_level['LEVEL'].astype(
                    str)

                fig = px.line(avg_time_by_level, x='LEVEL', y='TIME_TO_CUT',
                              title='Average Time to Cut by Level',
                              labels={'LEVEL': 'Level', 'TIME_TO_CUT': 'Time (seconds)'})
                st.plotly_chart(fig, use_container_width=True)

                # Success rate by level
                success_by_level = vessel_times.groupby(
                    'LEVEL')['IS_CORRECT'].mean().reset_index()
                success_by_level['Success Rate (%)'] = success_by_level['IS_CORRECT'] * 100
                success_by_level['LEVEL'] = success_by_level['LEVEL'].astype(
                    str)

                fig = px.bar(success_by_level, x='LEVEL', y='Success Rate (%)',
                             title='Success Rate by Level',
                             labels={'LEVEL': 'Level', 'Success Rate (%)': 'Success Rate (%)'})
                st.plotly_chart(fig, use_container_width=True)

            # Distribution of completion times
            st.subheader("Task Completion Time Distribution")

            fig = px.histogram(vessel_times, x='TIME_TO_CUT',
                               title='Distribution of Task Completion Times',
                               labels={'TIME_TO_CUT': 'Time (seconds)'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No vessel cut events found in the data.")

    except Exception as e:
        st.error(f"Error analyzing task completion time: {str(e)}")

# Peripheral Awareness Analysis
elif selected_page == "Peripheral Awareness":
    st.header("Objective 3: Peripheral Awareness")
    st.markdown("""
    This analysis measures how well participants notice events outside their main focus, based on:
    - Response rate to peripheral distractions
    - Response time to peripheral distractions
    - Detection effectiveness across different types of distractions
    """)

    try:
        # Filter for distraction events
        distraction_events = st.session_state.mouse_data[st.session_state.mouse_data['DISTRACTION_ACTION'].notna(
        )]

        if not distraction_events.empty:
            st.subheader("Distraction Events Overview")

            # Count by type and action
            distraction_counts = distraction_events.groupby(
                ['DISTRACTION_TYPE', 'DISTRACTION_ACTION']).size().reset_index(name='COUNT')

            # Display in a table
            st.write("Distraction Events by Type and Action:")
            st.dataframe(distraction_counts)

            # Find appear/click pairs
            distraction_appear = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'appear']
            distraction_click = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'click']

            if not distraction_appear.empty and not distraction_click.empty:
                # Merge to get appearance and click times for each distraction
                distractions = pd.merge(
                    distraction_appear[['DISTRACTION_ID',
                                        'TIMESTAMP', 'DISTRACTION_TYPE', 'LEVEL']],
                    distraction_click[['DISTRACTION_ID', 'TIMESTAMP']],
                    on='DISTRACTION_ID',
                    suffixes=('_appear', '_click'),
                    how='left'  # Include distractions that appeared but weren't clicked
                )

                # Calculate response time for clicked distractions
                distractions['RESPONSE_TIME'] = distractions.apply(
                    lambda row: calculate_time_difference(
                        row['TIMESTAMP_appear'], row['TIMESTAMP_click'])
                    if pd.notna(row['TIMESTAMP_click']) else None,
                    axis=1
                )

                # Response metrics
                st.subheader("Peripheral Awareness Metrics")

                col1, col2, col3 = st.columns(3)

                total_distractions = len(distractions)
                responded_distractions = distractions['RESPONSE_TIME'].count()
                missed_distractions = total_distractions - responded_distractions

                with col1:
                    st.metric("Total Distractions", total_distractions)

                with col2:
                    st.metric("Responded Distractions", responded_distractions)

                with col3:
                    response_rate = responded_distractions / \
                        total_distractions * 100 if total_distractions > 0 else 0
                    st.metric("Response Rate", f"{response_rate:.1f}%")

                # Additional metrics
                col1, col2 = st.columns(2)

                with col1:
                    if responded_distractions > 0:
                        avg_response_time = distractions['RESPONSE_TIME'].mean(
                        )
                        st.metric("Average Response Time",
                                  f"{avg_response_time:.2f}s")
                    else:
                        st.metric("Average Response Time", "N/A")

                with col2:
                    st.metric("Missed Distractions", missed_distractions)

                # Response time by distraction type
                if responded_distractions > 0:
                    st.subheader("Response Analysis by Distraction Type")

                    # Calculate response rate by type
                    response_by_type = distractions.groupby('DISTRACTION_TYPE').agg(
                        Total=('DISTRACTION_ID', 'count'),
                        Responded=('RESPONSE_TIME', 'count')
                    ).reset_index()

                    response_by_type['Response Rate (%)'] = response_by_type['Responded'] / \
                        response_by_type['Total'] * 100

                    fig = px.bar(response_by_type, x='DISTRACTION_TYPE', y='Response Rate (%)',
                                 title='Response Rate by Distraction Type',
                                 labels={'DISTRACTION_TYPE': 'Distraction Type', 'Response Rate (%)': 'Response Rate (%)'})
                    st.plotly_chart(fig, use_container_width=True)

                    # Average response time by distraction type
                    avg_response_by_type = distractions.dropna(subset=['RESPONSE_TIME']).groupby(
                        'DISTRACTION_TYPE')['RESPONSE_TIME'].mean().reset_index()

                    fig = px.bar(avg_response_by_type, x='DISTRACTION_TYPE', y='RESPONSE_TIME',
                                 title='Average Response Time by Distraction Type',
                                 labels={'DISTRACTION_TYPE': 'Distraction Type', 'RESPONSE_TIME': 'Response Time (seconds)'})
                    st.plotly_chart(fig, use_container_width=True)

                    # Response analysis by level
                    if 'LEVEL' in distractions.columns:
                        st.subheader("Peripheral Awareness by Level")

                        # Calculate response rate by level
                        response_by_level = distractions.groupby('LEVEL').agg(
                            Total=('DISTRACTION_ID', 'count'),
                            Responded=('RESPONSE_TIME', 'count')
                        ).reset_index()

                        response_by_level['Response Rate (%)'] = response_by_level['Responded'] / \
                            response_by_level['Total'] * 100
                        response_by_level['LEVEL'] = response_by_level['LEVEL'].astype(
                            str)

                        col1, col2 = st.columns(2)

                        with col1:
                            fig = px.bar(response_by_level, x='LEVEL', y='Response Rate (%)',
                                         title='Response Rate by Level',
                                         labels={'LEVEL': 'Level', 'Response Rate (%)': 'Response Rate (%)'})
                            st.plotly_chart(fig, use_container_width=True)

                        with col2:
                            # Average response time by level
                            avg_response_by_level = distractions.dropna(subset=['RESPONSE_TIME']).groupby(
                                'LEVEL')['RESPONSE_TIME'].mean().reset_index()
                            avg_response_by_level['LEVEL'] = avg_response_by_level['LEVEL'].astype(
                                str)

                            fig = px.line(avg_response_by_level, x='LEVEL', y='RESPONSE_TIME',
                                          title='Average Response Time by Level',
                                          labels={'LEVEL': 'Level', 'RESPONSE_TIME': 'Response Time (seconds)'})
                            st.plotly_chart(fig, use_container_width=True)

                    # Distribution of response times
                    st.subheader("Response Time Distribution")

                    fig = px.histogram(distractions.dropna(subset=['RESPONSE_TIME']), x='RESPONSE_TIME',
                                       title='Distribution of Response Times',
                                       labels={'RESPONSE_TIME': 'Response Time (seconds)'})
                    fig.update_layout(bargap=0.1)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No distraction appear/click pairs found in the data.")
        else:
            st.info("No distraction events found in the data.")

    except Exception as e:
        st.error(f"Error analyzing peripheral awareness: {str(e)}")

# Distraction Management Analysis
elif selected_page == "Distraction Management":
    st.header("Objective 4: Distraction Management")
    st.markdown("""
    This analysis measures how distractions affect focus and error rates, based on:
    - Performance comparison during distractions vs. normal conditions
    - Error rates during distractions
    - Movement patterns during distractions
    """)

    try:
        # Find background distraction events (start/end)
        background_distractions = st.session_state.mouse_data[
            (st.session_state.mouse_data['DISTRACTION_ID'] == 'background') &
            (st.session_state.mouse_data['DISTRACTION_ACTION'].isin(
                ['start', 'end']))
        ]

        if not background_distractions.empty:
            # Extract distraction periods
            st.subheader("Background Distraction Analysis")

            # Create pairs of start/end times
            distraction_pairs = {}

            for _, row in background_distractions.iterrows():
                distraction_key = row['DISTRACTION_TYPE']
                if distraction_key not in distraction_pairs:
                    distraction_pairs[distraction_key] = {}

                if row['DISTRACTION_ACTION'] == 'start':
                    distraction_pairs[distraction_key]['start'] = row['TIMESTAMP']
                elif row['DISTRACTION_ACTION'] == 'end':
                    if 'start' in distraction_pairs[distraction_key]:
                        distraction_pairs[distraction_key]['end'] = row['TIMESTAMP']

            # Create a list of distraction periods
            distraction_periods = []
            for distraction_type, times in distraction_pairs.items():
                if 'start' in times and 'end' in times:
                    distraction_periods.append({
                        'type': distraction_type,
                        'start': times['start'],
                        'end': times['end']
                    })

            if distraction_periods:
                # Display distraction periods
                st.write(
                    f"Found {len(distraction_periods)} background distraction periods")
                distraction_df = pd.DataFrame(distraction_periods)
                distraction_df['duration'] = distraction_df.apply(
                    lambda row: calculate_time_difference(
                        row['start'], row['end']),
                    axis=1
                )

                st.dataframe(
                    distraction_df[['type', 'start', 'end', 'duration']])

                # Function to check if a timestamp is within any distraction period
                def is_distracted(timestamp):
                    for period in distraction_periods:
                        if period['start'] <= timestamp <= period['end']:
                            return True
                    return False

                # Add distraction flag to mouse movement data
                mouse_movement = calculate_movement(
                    st.session_state.mouse_data.copy())
                mouse_movement['DISTRACTED'] = mouse_movement['TIMESTAMP'].apply(
                    is_distracted)

                # Performance comparison during distractions
                st.subheader(
                    "Performance During Distractions vs. Normal Conditions")

                # Movement comparison
                movement_by_condition = mouse_movement.groupby(
                    'DISTRACTED')['MOVEMENT'].mean().reset_index()
                movement_by_condition['DISTRACTED'] = movement_by_condition['DISTRACTED'].map(
                    {True: 'Distracted', False: 'Normal'})

                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(movement_by_condition, x='DISTRACTED', y='MOVEMENT',
                                 title='Average Movement During Distractions vs. Normal',
                                 labels={'DISTRACTED': 'Condition',
                                         'MOVEMENT': 'Avg Movement (pixels)'},
                                 color_discrete_sequence=['#2166ac', '#b2182b'])
                    st.plotly_chart(fig, use_container_width=True)

                # Find vessel cuts during distraction periods
                vessel_cuts = st.session_state.vessel_data[st.session_state.vessel_data['EVENT'] == 'cut'].copy(
                )
                vessel_cuts['DISTRACTED'] = vessel_cuts['TIMESTAMP'].apply(
                    is_distracted)

                if not vessel_cuts.empty:
                    # Error rate comparison
                    error_by_condition = vessel_cuts.groupby('DISTRACTED').agg(
                        Total=('VESSEL_ID', 'count'),
                        Correct=('IS_CORRECT', 'sum')
                    ).reset_index()

                    error_by_condition['Error Rate (%)'] = (
                        1 - error_by_condition['Correct'] / error_by_condition['Total']) * 100
                    error_by_condition['DISTRACTED'] = error_by_condition['DISTRACTED'].map(
                        {True: 'Distracted', False: 'Normal'})

                    with col2:
                        fig = px.bar(error_by_condition, x='DISTRACTED', y='Error Rate (%)',
                                     title='Error Rate During Distractions vs. Normal',
                                     labels={'DISTRACTED': 'Condition',
                                             'Error Rate (%)': 'Error Rate (%)'},
                                     color_discrete_sequence=['#2166ac', '#b2182b'])
                        st.plotly_chart(fig, use_container_width=True)

                # Movement patterns during distractions
                st.subheader("Movement Patterns During Distractions")

                # Movement speed over time with distraction periods highlighted
                time_series = mouse_movement.set_index(
                    'TIMESTAMP')['MOVEMENT'].resample('500ms').mean().reset_index()
                time_series['DISTRACTED'] = time_series['TIMESTAMP'].apply(
                    is_distracted)

                # Create line plot with distraction periods highlighted
                fig = go.Figure()

                # Add movement data
                fig.add_trace(go.Scatter(
                    x=time_series['TIMESTAMP'],
                    y=time_series['MOVEMENT'],
                    mode='lines',
                    name='Movement'
                ))

                # Highlight distraction periods
                for period in distraction_periods:
                    fig.add_vrect(
                        x0=period['start'],
                        x1=period['end'],
                        fillcolor="rgba(220, 20, 60, 0.2)",
                        opacity=0.5,
                        layer="below",
                        line_width=0,
                    )

                fig.update_layout(
                    title='Movement Speed Over Time (Distraction Periods Highlighted in Red)',
                    xaxis_title='Time',
                    yaxis_title='Movement (pixels)',
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

                # Heatmap comparison of movement patterns
                st.subheader(
                    "Movement Distribution During Different Conditions")

                col1, col2 = st.columns(2)

                with col1:
                    distracted_data = mouse_movement[mouse_movement['DISTRACTED']]
                    fig = px.density_heatmap(
                        distracted_data,
                        x='X_POSITION',
                        y='Y_POSITION',
                        title='Mouse Movement Heatmap (During Distractions)',
                        labels={'X_POSITION': 'X Position',
                                'Y_POSITION': 'Y Position'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    normal_data = mouse_movement[~mouse_movement['DISTRACTED']]
                    fig = px.density_heatmap(
                        normal_data,
                        x='X_POSITION',
                        y='Y_POSITION',
                        title='Mouse Movement Heatmap (Normal Conditions)',
                        labels={'X_POSITION': 'X Position',
                                'Y_POSITION': 'Y Position'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Impact of different distraction types
                st.subheader("Impact of Different Distraction Types")

                # Function to get the distraction type for a timestamp
                def get_distraction_type(timestamp):
                    for period in distraction_periods:
                        if period['start'] <= timestamp <= period['end']:
                            return period['type']
                    return None

                # Add distraction type to movement data
                mouse_movement['DISTRACTION_TYPE'] = mouse_movement['TIMESTAMP'].apply(
                    get_distraction_type)
                distraction_movement = mouse_movement[mouse_movement['DISTRACTION_TYPE'].notna(
                )]

                if not distraction_movement.empty:
                    # Average movement by distraction type
                    movement_by_type = distraction_movement.groupby(
                        'DISTRACTION_TYPE')['MOVEMENT'].mean().reset_index()

                    fig = px.bar(movement_by_type, x='DISTRACTION_TYPE', y='MOVEMENT',
                                 title='Average Movement by Distraction Type',
                                 labels={'DISTRACTION_TYPE': 'Distraction Type', 'MOVEMENT': 'Avg Movement (pixels)'})
                    st.plotly_chart(fig, use_container_width=True)

                    # If we have vessel cut data during distractions
                    if not vessel_cuts.empty and vessel_cuts['DISTRACTED'].any():
                        # Add distraction type to vessel cuts
                        vessel_cuts['DISTRACTION_TYPE'] = vessel_cuts['TIMESTAMP'].apply(
                            get_distraction_type)
                        distracted_cuts = vessel_cuts[vessel_cuts['DISTRACTION_TYPE'].notna(
                        )]

                        if not distracted_cuts.empty:
                            # Error rate by distraction type
                            error_by_type = distracted_cuts.groupby('DISTRACTION_TYPE').agg(
                                Total=('VESSEL_ID', 'count'),
                                Correct=('IS_CORRECT', 'sum')
                            ).reset_index()

                            error_by_type['Error Rate (%)'] = (
                                1 - error_by_type['Correct'] / error_by_type['Total']) * 100

                            fig = px.bar(error_by_type, x='DISTRACTION_TYPE', y='Error Rate (%)',
                                         title='Error Rate by Distraction Type',
                                         labels={'DISTRACTION_TYPE': 'Distraction Type', 'Error Rate (%)': 'Error Rate (%)'})
                            st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    "No complete distraction periods (start/end pairs) found in the data.")
        else:
            st.info("No background distraction events found in the data.")

        # Analyze the effect of field of view changes
        if 'FIELD_OF_VIEW' in st.session_state.mouse_data.columns:
            st.subheader("Field of View Impact Analysis")

            # Group by field of view setting
            mouse_movement = calculate_movement(
                st.session_state.mouse_data.copy())
            movement_by_fov = mouse_movement.groupby(
                'FIELD_OF_VIEW')['MOVEMENT'].mean().reset_index()
            movement_by_fov['FIELD_OF_VIEW'] = movement_by_fov['FIELD_OF_VIEW'].map(
                {True: 'Limited FOV', False: 'Full FOV'})

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(movement_by_fov, x='FIELD_OF_VIEW', y='MOVEMENT',
                             title='Average Movement by Field of View',
                             labels={'FIELD_OF_VIEW': 'Field of View', 'MOVEMENT': 'Avg Movement (pixels)'})
                st.plotly_chart(fig, use_container_width=True)

            # Analyze vessel cuts by field of view
            vessel_cuts = st.session_state.vessel_data[st.session_state.vessel_data['EVENT'] == 'cut'].copy(
            )

            if not vessel_cuts.empty and 'FIELD_OF_VIEW' in vessel_cuts.columns:
                error_by_fov = vessel_cuts.groupby('FIELD_OF_VIEW').agg(
                    Total=('VESSEL_ID', 'count'),
                    Correct=('IS_CORRECT', 'sum')
                ).reset_index()

                error_by_fov['Error Rate (%)'] = (
                    1 - error_by_fov['Correct'] / error_by_fov['Total']) * 100
                error_by_fov['FIELD_OF_VIEW'] = error_by_fov['FIELD_OF_VIEW'].map(
                    {True: 'Limited FOV', False: 'Full FOV'})

                with col2:
                    fig = px.bar(error_by_fov, x='FIELD_OF_VIEW', y='Error Rate (%)',
                                 title='Error Rate by Field of View',
                                 labels={'FIELD_OF_VIEW': 'Field of View', 'Error Rate (%)': 'Error Rate (%)'})
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error analyzing distraction management: {str(e)}")

# Dashboard Overview
elif selected_page == "Dashboard":
    st.header("Study Dashboard: Key Performance Metrics")
    st.markdown("""
    This dashboard provides an overview of key performance metrics across all four research objectives.
    """)

    try:
        # Prepare data
        mouse_movement = calculate_movement(st.session_state.mouse_data.copy())
        vessel_data = st.session_state.vessel_data.copy()

        # Summary metrics in cards
        st.subheader("Summary Performance Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Total movement
            total_movement = mouse_movement['MOVEMENT'].sum()
            st.metric("Total Movement", f"{total_movement:.0f} px")

        with col2:
            # Success rate
            vessel_cuts = vessel_data[vessel_data['EVENT'] == 'cut']
            if not vessel_cuts.empty:
                success_rate = vessel_cuts['IS_CORRECT'].mean() * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
            else:
                st.metric("Success Rate", "N/A")

        with col3:
            # Distraction response rate
            distraction_events = st.session_state.mouse_data[st.session_state.mouse_data['DISTRACTION_ACTION'].notna(
            )]
            if not distraction_events.empty:
                distraction_appear = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'appear']
                distraction_click = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'click']

                if not distraction_appear.empty:
                    appear_count = len(distraction_appear)
                    click_count = len(distraction_click)
                    response_rate = click_count / appear_count * 100 if appear_count > 0 else 0
                    st.metric("Distraction Response Rate",
                              f"{response_rate:.1f}%")
                else:
                    st.metric("Distraction Response Rate", "N/A")
            else:
                st.metric("Distraction Response Rate", "N/A")

        with col4:
            # Average time per task
            vessel_creates = vessel_data[vessel_data['EVENT'] == 'created']
            if not vessel_cuts.empty and not vessel_creates.empty:
                # Merge to get creation and cut times for each vessel
                vessel_times = pd.merge(
                    vessel_creates[['VESSEL_ID', 'TIMESTAMP']],
                    vessel_cuts[['VESSEL_ID', 'TIMESTAMP']],
                    on='VESSEL_ID',
                    suffixes=('_create', '_cut')
                )

                # Calculate time difference
                vessel_times['TIME_TO_CUT'] = vessel_times.apply(
                    lambda row: calculate_time_difference(
                        row['TIMESTAMP_create'], row['TIMESTAMP_cut']),
                    axis=1
                )

                avg_time = vessel_times['TIME_TO_CUT'].mean()
                st.metric("Avg Time per Task", f"{avg_time:.2f}s")
            else:
                st.metric("Avg Time per Task", "N/A")

        # Performance trends across levels
        st.subheader("Performance Trends by Level")

        if 'LEVEL' in mouse_movement.columns:
            # Calculate metrics by level
            level_metrics = []

            for level in sorted(mouse_movement['LEVEL'].unique()):
                level_data = mouse_movement[mouse_movement['LEVEL'] == level]
                level_cuts = vessel_cuts[vessel_cuts['LEVEL'] ==
                                         level] if not vessel_cuts.empty else pd.DataFrame()

                metrics = {
                    'LEVEL': str(level),
                    'Movement': level_data['MOVEMENT'].mean() if not level_data.empty else 0
                }

                if not level_cuts.empty:
                    metrics['Success Rate'] = level_cuts['IS_CORRECT'].mean() * \
                        100

                    # Calculate average time if we have the data
                    level_creates = vessel_creates[vessel_creates['LEVEL'] == level]
                    if not level_creates.empty:
                        level_times = pd.merge(
                            level_creates[['VESSEL_ID', 'TIMESTAMP']],
                            level_cuts[['VESSEL_ID', 'TIMESTAMP']],
                            on='VESSEL_ID',
                            suffixes=('_create', '_cut')
                        )

                        if not level_times.empty:
                            level_times['TIME_TO_CUT'] = level_times.apply(
                                lambda row: calculate_time_difference(
                                    row['TIMESTAMP_create'], row['TIMESTAMP_cut']),
                                axis=1
                            )
                            metrics['Task Time'] = level_times['TIME_TO_CUT'].mean()

                level_metrics.append(metrics)

            if level_metrics:
                level_df = pd.DataFrame(level_metrics)

                # Create line chart with multiple metrics
                fig = go.Figure()

                if 'Movement' in level_df.columns:
                    fig.add_trace(go.Scatter(
                        x=level_df['LEVEL'],
                        y=level_df['Movement'],
                        mode='lines+markers',
                        name='Avg Movement'
                    ))

                if 'Success Rate' in level_df.columns:
                    fig.add_trace(go.Scatter(
                        x=level_df['LEVEL'],
                        y=level_df['Success Rate'],
                        mode='lines+markers',
                        name='Success Rate (%)',
                        yaxis='y2'
                    ))

                if 'Task Time' in level_df.columns:
                    fig.add_trace(go.Scatter(
                        x=level_df['LEVEL'],
                        y=level_df['Task Time'],
                        mode='lines+markers',
                        name='Avg Task Time (s)',
                        yaxis='y3'
                    ))

                # Update layout with multiple y-axes
                fig.update_layout(
                    title='Key Performance Metrics by Level',
                    yaxis=dict(
                        title='Avg Movement (px)'
                    ),
                    yaxis2=dict(
                        title='Success Rate (%)',
                        overlaying='y',
                        side='right'
                    ),
                    yaxis3=dict(
                        title='Avg Task Time (s)',
                        overlaying='y',
                        side='right',
                        position=0.9
                    ),
                    xaxis=dict(title='Level'),
                    legend=dict(x=0.01, y=0.99),
                    hovermode='x'
                )

                st.plotly_chart(fig, use_container_width=True)

        # Task efficiency analysis
        st.subheader("Task Efficiency Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Movement patterns heatmap
            fig = px.density_heatmap(
                mouse_movement,
                x='X_POSITION',
                y='Y_POSITION',
                title='Movement Density Heatmap',
                labels={'X_POSITION': 'X Position', 'Y_POSITION': 'Y Position'}
            )
            fig.update_layout(coloraxis_colorbar=dict(title='Frequency'))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Task completion time distribution
            if 'vessel_times' in locals() and not vessel_times.empty and 'TIME_TO_CUT' in vessel_times.columns:
                fig = px.histogram(
                    vessel_times,
                    x='TIME_TO_CUT',
                    title='Task Completion Time Distribution',
                    labels={'TIME_TO_CUT': 'Time (seconds)'},
                    marginal='box'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No task completion time data available.")

        # Correlation analysis
        st.subheader("Correlation Between Movement and Performance")

        if 'vessel_times' in locals() and not vessel_times.empty and 'TIME_TO_CUT' in vessel_times.columns:
            # Try to correlate movement with task time
            if 'LEVEL' in mouse_movement.columns and 'LEVEL' in vessel_times.columns:
                # Calculate average movement and time by level
                avg_movement_by_level = mouse_movement.groupby(
                    'LEVEL')['MOVEMENT'].mean().reset_index()
                avg_time_by_level = vessel_times.groupby(
                    'LEVEL')['TIME_TO_CUT'].mean().reset_index()

                # Merge on level
                correlation_df = pd.merge(
                    avg_movement_by_level, avg_time_by_level, on='LEVEL')

                if not correlation_df.empty:
                    fig = px.scatter(
                        correlation_df,
                        x='MOVEMENT',
                        y='TIME_TO_CUT',
                        text='LEVEL',
                        title='Correlation Between Movement and Task Completion Time',
                        labels={
                            'MOVEMENT': 'Average Movement (pixels)',
                            'TIME_TO_CUT': 'Average Task Time (seconds)',
                            'LEVEL': 'Level'
                        },
                        trendline='ols'
                    )
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)

                    # Calculate correlation coefficient
                    corr = correlation_df['MOVEMENT'].corr(
                        correlation_df['TIME_TO_CUT'])
                    st.write(
                        f"Correlation coefficient between movement and task time: **{corr:.3f}**")

                    if corr > 0.5:
                        st.write("🔍 **Insight**: There appears to be a positive correlation between movement and task completion time, suggesting that more efficient movement may lead to faster task completion.")
                    elif corr < -0.5:
                        st.write("🔍 **Insight**: There appears to be a negative correlation between movement and task completion time, suggesting that more movement may actually help complete tasks faster.")
                    else:
                        st.write(
                            "🔍 **Insight**: There doesn't appear to be a strong correlation between movement and task completion time.")

        # Final insights
        st.subheader("Key Research Insights")

        st.markdown("""
        Based on the analysis of the game performance data, we can draw the following insights related to the research objectives:
        
        1. **Instrument Efficiency**:
           - The data shows how movement patterns change across different levels
           - Movement efficiency can be measured by the ratio of movement to successful outcomes
        
        2. **Task Completion Time**:
           - Task completion times provide insights into surgical speed and precision
           - The progression across levels reveals learning curves and adaptation
        
        3. **Peripheral Awareness**:
           - Response rates to peripheral distractions indicate situational awareness
           - Higher response rates correlate with better surgical awareness
        
        4. **Distraction Management**:
           - Performance differences during distracted vs. normal conditions highlight focus abilities
           - Changes in error rates during distractions quantify the impact on surgical precision
        """)

    except Exception as e:
        st.error(f"Error generating dashboard: {str(e)}")

# Add a footer to all pages
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    <p>Vessel Cutting Game Analysis Tool for UCL Medical Physics and Biomedical Engineering Research</p>
    <p>Ethics Committee Approval ID: 24249/005b</p>
</div>
""", unsafe_allow_html=True)
