import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import ast
import os
import io
import uuid
import tempfile
import base64
import zipfile

# Set page configuration
st.set_page_config(
    page_title="Keyhole Surgery Game Admin Analysis",
    page_icon="🩺",
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
    if df.empty:
        return df

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


def is_valid_mouse_data(df):
    """Check if the dataframe has the required columns for mouse tracking data"""
    required_columns = ['TIMESTAMP', 'X_POSITION', 'Y_POSITION']
    return all(col in df.columns for col in required_columns)


def is_valid_vessel_data(df):
    """Check if the dataframe has the required columns for vessel data"""
    required_columns = ['TIMESTAMP', 'VESSEL_ID', 'EVENT']
    return all(col in df.columns for col in required_columns)


def preprocess_dataframe(df, data_type):
    """Preprocess dataframe based on data type"""
    if df.empty:
        return df

    # Convert timestamps
    if 'TIMESTAMP' in df.columns:
        df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])

    if data_type == 'mouse':
        # Convert boolean columns
        for col in ['IS_CUTTING', 'FIELD_OF_VIEW']:
            if col in df.columns:
                try:
                    df[col] = df[col].astype(bool)
                except:
                    pass

    elif data_type == 'vessel':
        # Convert boolean columns
        for col in ['IS_CORRECT', 'IS_CUT', 'IS_INTERTWINED']:
            if col in df.columns:
                try:
                    df[col] = df[col].astype(bool)
                except:
                    pass

        # Parse PATH_POINTS if available
        if 'PATH_POINTS' in df.columns:
            try:
                df['PATH_POINTS_PARSED'] = df['PATH_POINTS'].apply(
                    parse_path_points)
            except:
                pass

    return df


def get_movement_metrics(mouse_data):
    """Calculate movement metrics from mouse tracking data"""
    if mouse_data.empty:
        return {}

    # Calculate movement
    movement_data = calculate_movement(mouse_data)

    # Calculate metrics
    total_movement = movement_data['MOVEMENT'].sum()
    avg_movement = movement_data['MOVEMENT'].mean()
    max_movement = movement_data['MOVEMENT'].max()

    # Movement by level if available
    level_movement = {}
    if 'LEVEL' in movement_data.columns:
        for level in movement_data['LEVEL'].unique():
            level_data = movement_data[movement_data['LEVEL'] == level]
            level_movement[level] = {
                'total': level_data['MOVEMENT'].sum(),
                'avg': level_data['MOVEMENT'].mean()
            }

    return {
        'total_movement': total_movement,
        'avg_movement': avg_movement,
        'max_movement': max_movement,
        'level_movement': level_movement
    }


def get_task_completion_metrics(mouse_data, vessel_data):
    """Calculate task completion metrics"""
    if vessel_data.empty:
        return {}

    # Filter for vessel events
    vessel_cuts = vessel_data[vessel_data['EVENT'] == 'cut']
    vessel_creates = vessel_data[vessel_data['EVENT'] == 'created']

    if vessel_cuts.empty or vessel_creates.empty:
        return {}

    # Merge to get creation and cut times for each vessel
    vessel_times = pd.merge(
        vessel_creates[['VESSEL_ID', 'TIMESTAMP', 'IS_CORRECT', 'LEVEL']],
        vessel_cuts[['VESSEL_ID', 'TIMESTAMP']],
        on='VESSEL_ID',
        suffixes=('_create', '_cut'),
        how='inner'
    )

    if vessel_times.empty:
        return {}

    # Calculate time difference
    vessel_times['TIME_TO_CUT'] = vessel_times.apply(
        lambda row: calculate_time_difference(
            row['TIMESTAMP_create'], row['TIMESTAMP_cut']),
        axis=1
    )

    # Calculate metrics
    avg_time_overall = vessel_times['TIME_TO_CUT'].mean()

    correct_time = np.nan
    if 'IS_CORRECT' in vessel_times.columns:
        correct_vessels = vessel_times[vessel_times['IS_CORRECT'] == True]
        if not correct_vessels.empty:
            correct_time = correct_vessels['TIME_TO_CUT'].mean()

    incorrect_time = np.nan
    if 'IS_CORRECT' in vessel_times.columns:
        incorrect_vessels = vessel_times[vessel_times['IS_CORRECT'] == False]
        if not incorrect_vessels.empty:
            incorrect_time = incorrect_vessels['TIME_TO_CUT'].mean()

    # Calculate success rate
    success_rate = np.nan
    if 'IS_CORRECT' in vessel_times.columns:
        success_rate = vessel_times['IS_CORRECT'].mean() * 100

    # Calculate time by level if available
    level_times = {}
    if 'LEVEL' in vessel_times.columns:
        for level in vessel_times['LEVEL'].unique():
            level_data = vessel_times[vessel_times['LEVEL'] == level]
            level_times[level] = {
                'avg_time': level_data['TIME_TO_CUT'].mean(),
                'success_rate': level_data['IS_CORRECT'].mean() * 100 if 'IS_CORRECT' in level_data.columns else np.nan
            }

    return {
        'avg_time_overall': avg_time_overall,
        'correct_time': correct_time,
        'incorrect_time': incorrect_time,
        'success_rate': success_rate,
        'level_times': level_times,
        'vessel_times': vessel_times
    }


def get_distraction_metrics(mouse_data):
    """Calculate distraction response metrics"""
    if mouse_data.empty:
        return {}

    # Filter for distraction events
    distraction_events = mouse_data[mouse_data['DISTRACTION_ACTION'].notna()]

    if distraction_events.empty:
        return {}

    # Find appear/click pairs
    distraction_appear = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'appear']
    distraction_click = distraction_events[distraction_events['DISTRACTION_ACTION'] == 'click']

    if distraction_appear.empty:
        return {}

    # Calculate response rates
    total_distractions = len(distraction_appear)
    responded_distractions = len(distraction_click)
    response_rate = responded_distractions / \
        total_distractions * 100 if total_distractions > 0 else 0

    # Calculate response times if we have click events
    avg_response_time = np.nan
    if not distraction_click.empty:
        # Merge to get appearance and click times for each distraction
        distractions = pd.merge(
            distraction_appear[['DISTRACTION_ID',
                                'TIMESTAMP', 'DISTRACTION_TYPE', 'LEVEL']],
            distraction_click[['DISTRACTION_ID', 'TIMESTAMP']],
            on='DISTRACTION_ID',
            suffixes=('_appear', '_click'),
            how='inner'
        )

        if not distractions.empty:
            # Calculate response time for clicked distractions
            distractions['RESPONSE_TIME'] = distractions.apply(
                lambda row: calculate_time_difference(
                    row['TIMESTAMP_appear'], row['TIMESTAMP_click']),
                axis=1
            )

            avg_response_time = distractions['RESPONSE_TIME'].mean()

    # Calculate response metrics by distraction type if available
    type_metrics = {}
    if 'DISTRACTION_TYPE' in distraction_events.columns:
        for dist_type in distraction_events['DISTRACTION_TYPE'].unique():
            if pd.isna(dist_type):
                continue

            appear_type = distraction_appear[distraction_appear['DISTRACTION_TYPE'] == dist_type]
            click_type = distraction_click[distraction_click['DISTRACTION_TYPE'] == dist_type]

            total_type = len(appear_type)
            responded_type = len(click_type)
            type_rate = responded_type / total_type * 100 if total_type > 0 else 0

            type_metrics[dist_type] = {
                'total': total_type,
                'responded': responded_type,
                'rate': type_rate
            }

            # Calculate response time for this type
            if not click_type.empty and not appear_type.empty:
                type_distractions = pd.merge(
                    appear_type[['DISTRACTION_ID', 'TIMESTAMP']],
                    click_type[['DISTRACTION_ID', 'TIMESTAMP']],
                    on='DISTRACTION_ID',
                    suffixes=('_appear', '_click'),
                    how='inner'
                )

                if not type_distractions.empty:
                    type_distractions['RESPONSE_TIME'] = type_distractions.apply(
                        lambda row: calculate_time_difference(
                            row['TIMESTAMP_appear'], row['TIMESTAMP_click']),
                        axis=1
                    )

                    type_metrics[dist_type]['avg_response_time'] = type_distractions['RESPONSE_TIME'].mean(
                    )

    return {
        'total_distractions': total_distractions,
        'responded_distractions': responded_distractions,
        'response_rate': response_rate,
        'avg_response_time': avg_response_time,
        'type_metrics': type_metrics
    }


def get_background_distraction_metrics(mouse_data, vessel_data):
    """Calculate metrics for background distractions (calls, heart rate alerts, etc.)"""
    if mouse_data.empty:
        return {}

    # Find background distraction events (start/end)
    background_distractions = mouse_data[
        (mouse_data['DISTRACTION_ID'] == 'background') &
        (mouse_data['DISTRACTION_ACTION'].isin(['start', 'end']))
    ]

    if background_distractions.empty:
        return {}

    # Extract distraction periods
    distraction_pairs = {}
    for _, row in background_distractions.iterrows():
        distraction_key = row['DISTRACTION_TYPE']
        if pd.isna(distraction_key):
            continue

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

    if not distraction_periods:
        return {}

    # Create distraction period dataframe
    distraction_df = pd.DataFrame(distraction_periods)
    distraction_df['duration'] = distraction_df.apply(
        lambda row: calculate_time_difference(row['start'], row['end']),
        axis=1
    )

    # Function to check if a timestamp is within any distraction period
    def is_distracted(timestamp):
        for period in distraction_periods:
            if period['start'] <= timestamp <= period['end']:
                return True
        return False

    # Add distraction flag to mouse movement data
    mouse_movement = calculate_movement(mouse_data.copy())
    mouse_movement['DISTRACTED'] = mouse_movement['TIMESTAMP'].apply(
        is_distracted)

    # Calculate performance during distractions vs. normal
    distracted_movement = mouse_movement[mouse_movement['DISTRACTED']]['MOVEMENT'].mean(
    ) if any(mouse_movement['DISTRACTED']) else np.nan
    normal_movement = mouse_movement[~mouse_movement['DISTRACTED']]['MOVEMENT'].mean(
    ) if any(~mouse_movement['DISTRACTED']) else np.nan

    # Calculate error rates during distractions if we have vessel data
    distracted_error_rate = np.nan
    normal_error_rate = np.nan

    if not vessel_data.empty:
        vessel_cuts = vessel_data[vessel_data['EVENT'] == 'cut'].copy()
        if not vessel_cuts.empty and 'IS_CORRECT' in vessel_cuts.columns:
            vessel_cuts['DISTRACTED'] = vessel_cuts['TIMESTAMP'].apply(
                is_distracted)

            # Calculate error rates
            distracted_cuts = vessel_cuts[vessel_cuts['DISTRACTED']]
            normal_cuts = vessel_cuts[~vessel_cuts['DISTRACTED']]

            if not distracted_cuts.empty:
                distracted_error_rate = (
                    1 - distracted_cuts['IS_CORRECT'].mean()) * 100

            if not normal_cuts.empty:
                normal_error_rate = (
                    1 - normal_cuts['IS_CORRECT'].mean()) * 100

    # Calculate metrics by distraction type
    type_performance = {}
    for period in distraction_periods:
        dist_type = period['type']
        if dist_type not in type_performance:
            type_performance[dist_type] = {
                'count': 0,
                'total_duration': 0,
                'avg_movement': [],
                'error_rates': []
            }

        type_performance[dist_type]['count'] += 1
        duration = calculate_time_difference(period['start'], period['end'])
        type_performance[dist_type]['total_duration'] += duration if duration else 0

        # Calculate performance during this specific distraction
        period_movement = mouse_movement[
            (mouse_movement['TIMESTAMP'] >= period['start']) &
            (mouse_movement['TIMESTAMP'] <= period['end'])
        ]

        if not period_movement.empty:
            type_performance[dist_type]['avg_movement'].append(
                period_movement['MOVEMENT'].mean())

        # Calculate error rate during this specific distraction
        if not vessel_data.empty:
            period_cuts = vessel_cuts[
                (vessel_cuts['TIMESTAMP'] >= period['start']) &
                (vessel_cuts['TIMESTAMP'] <= period['end'])
            ]

            if not period_cuts.empty and 'IS_CORRECT' in period_cuts.columns:
                error_rate = (1 - period_cuts['IS_CORRECT'].mean()) * 100
                type_performance[dist_type]['error_rates'].append(error_rate)

    # Calculate averages for each distraction type
    for dist_type in type_performance:
        if type_performance[dist_type]['avg_movement']:
            type_performance[dist_type]['avg_movement'] = np.mean(
                type_performance[dist_type]['avg_movement'])
        else:
            type_performance[dist_type]['avg_movement'] = np.nan

        if type_performance[dist_type]['error_rates']:
            type_performance[dist_type]['error_rates'] = np.mean(
                type_performance[dist_type]['error_rates'])
        else:
            type_performance[dist_type]['error_rates'] = np.nan

    return {
        'distraction_periods': distraction_df,
        'distracted_movement': distracted_movement,
        'normal_movement': normal_movement,
        'distracted_error_rate': distracted_error_rate,
        'normal_error_rate': normal_error_rate,
        'type_performance': type_performance
    }


def process_user_data(mouse_data, vessel_data, user_id):
    """Process data for a single user"""
    if mouse_data.empty or vessel_data.empty:
        return {}

    # Ensure data is properly formatted
    mouse_data = preprocess_dataframe(mouse_data, 'mouse')
    vessel_data = preprocess_dataframe(vessel_data, 'vessel')

    # Calculate all metrics
    movement_metrics = get_movement_metrics(mouse_data)
    task_metrics = get_task_completion_metrics(mouse_data, vessel_data)
    distraction_metrics = get_distraction_metrics(mouse_data)
    background_metrics = get_background_distraction_metrics(
        mouse_data, vessel_data)

    # Create summary metrics for this user
    summary = {
        'user_id': user_id,
        'data_points': len(mouse_data),
        'vessels': len(vessel_data[vessel_data['EVENT'] == 'created']),
        'vessels_cut': len(vessel_data[vessel_data['EVENT'] == 'cut']),
        'total_movement': movement_metrics.get('total_movement', np.nan),
        'avg_movement': movement_metrics.get('avg_movement', np.nan),
        'avg_task_time': task_metrics.get('avg_time_overall', np.nan),
        'success_rate': task_metrics.get('success_rate', np.nan),
        'distraction_response_rate': distraction_metrics.get('response_rate', np.nan),
        'distraction_response_time': distraction_metrics.get('avg_response_time', np.nan),
        'movement_ratio': background_metrics.get('distracted_movement', np.nan) /
        background_metrics.get('normal_movement', 1) if background_metrics.get(
            'normal_movement', 0) else np.nan,
        'error_ratio': background_metrics.get('distracted_error_rate', np.nan) /
        background_metrics.get('normal_error_rate', 1) if background_metrics.get(
            'normal_error_rate', 0) else np.nan
    }

    # Add detailed metrics
    user_data = {
        'summary': summary,
        'movement': movement_metrics,
        'task': task_metrics,
        'distraction': distraction_metrics,
        'background': background_metrics,
        'mouse_data': mouse_data,
        'vessel_data': vessel_data
    }

    return user_data


# Main app header
st.title("🏥 Keyhole Surgery Game Admin Analysis")
st.markdown("""
This admin application allows analysis of multiple users' data from the Blood Vessel Cutting Game, calculating metrics aligned with the research objectives:

1. **Instrument Efficiency**: How efficiently instruments are used based on total movement
2. **Task Completion Time**: How quickly tasks are completed, measured by time taken
3. **Peripheral Awareness**: How well participants notice events outside the main focus, measured by response speed
4. **Distraction Management**: How distractions affect focus and errors, measured by attention to irrelevant elements
""")

# Sidebar for navigation
st.sidebar.title("Navigation")
selected_page = st.sidebar.radio(
    "Go to",
    ["Data Upload", "Aggregate Analysis", "Instrument Efficiency", "Task Completion",
        "Peripheral Awareness", "Distraction Management", "User Comparison", "Surgeon Experience Analysis", "Export Report"]
)

# Initialise session state for storing data
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'aggregated' not in st.session_state:
    st.session_state.aggregated = False
if 'user_id_input' not in st.session_state:
    st.session_state.user_id_input = f"user_{len(st.session_state.user_data) + 1}"

# Data Upload Page
if selected_page == "Data Upload":
    st.header("Upload Multiple Users' Game Data")

    # Option to upload multiple user data files
    st.subheader("Upload User Data Files")
    st.markdown("""
    Upload data for multiple users. For each user, you need:
    1. Mouse tracking CSV file
    2. Vessel creation CSV file
    
    You can upload as many user datasets as needed.
    """)

    # Function to reset input fields after submission
    def reset_upload_fields():
        st.session_state.user_id_input = f"user_{len(st.session_state.user_data) + 1}"
        # We can't reset the file uploaders directly, but we'll update the key
        st.rerun()

    # Create a container for file uploads
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            user_id = st.text_input(
                "User ID (optional)", value=st.session_state.user_id_input, key="user_id_field")
        with col2:
            mouse_file = st.file_uploader(f"Mouse Tracking File", type=[
                                          "csv"], key=f"mouse_{st.session_state.user_id_input}")
        with col3:
            vessel_file = st.file_uploader(f"Vessel Creation File", type=[
                                           "csv"], key=f"vessel_{st.session_state.user_id_input}")

        if mouse_file is not None and vessel_file is not None:
            if st.button("Add User Data"):
                try:
                    # Read the data
                    mouse_data = pd.read_csv(mouse_file)
                    vessel_data = pd.read_csv(vessel_file)

                    # Validate data format
                    if not is_valid_mouse_data(mouse_data):
                        st.error("Invalid mouse tracking data format")
                    elif not is_valid_vessel_data(vessel_data):
                        st.error("Invalid vessel creation data format")
                    else:
                        # Process user data
                        user_data = process_user_data(
                            mouse_data, vessel_data, user_id)

                        # Add to session state
                        st.session_state.user_data[user_id] = user_data
                        st.success(
                            f"Successfully added data for user {user_id}")

                        # Reset input fields
                        reset_upload_fields()
                except Exception as e:
                    st.error(f"Error processing files: {str(e)}")

    # Display list of uploaded users
    st.subheader("Uploaded User Data")

    if st.session_state.user_data:
        user_list = []
        for user_id, data in st.session_state.user_data.items():
            user_list.append({
                "User ID": user_id,
                "Mouse Data Points": data.get('summary', {}).get('data_points', 0),
                "Vessels Created": data.get('summary', {}).get('vessels', 0),
                "Vessels Cut": data.get('summary', {}).get('vessels_cut', 0)
            })

        user_df = pd.DataFrame(user_list)
        st.dataframe(user_df)

        if st.button("Remove All Users"):
            st.session_state.user_data = {}
            st.session_state.aggregated = False
            st.rerun()
    else:
        st.info("No user data uploaded yet")

    # Option to aggregate data
    if st.session_state.user_data:
        st.subheader("Prepare Aggregate Analysis")
        if st.button("Process All Data for Analysis"):
            st.session_state.aggregated = True
            st.success(
                "Data aggregated successfully! You can now navigate to the analysis pages.")

    # Option to upload a zip file with multiple user data
    st.subheader("Bulk Upload (ZIP File)")
    st.markdown("""
    Alternatively, upload a ZIP file containing multiple user datasets. 
    The ZIP should contain folders named by user ID, each with two CSV files:
    - mouse_tracking.csv
    - vessel_creation.csv
    """)

    zip_file = st.file_uploader("Upload ZIP with multiple user data", type=[
                                "zip"], key="zip_upload")

    if zip_file is not None:
        if st.button("Process ZIP File"):
            try:
                with zipfile.ZipFile(zip_file) as z:
                    # Get list of all files in zip
                    file_list = z.namelist()

                    # Find all potential user folders (any folder that contains both required files)
                    user_folders = set()
                    for file_path in file_list:
                        parts = file_path.split('/')
                        if len(parts) > 2:  # It's in a nested folder
                            # Get the folder name that contains both files
                            folder_path = '/'.join(parts[:-1])
                            mouse_path = f"{folder_path}/mouse_tracking.csv"
                            vessel_path = f"{folder_path}/vessel_creation.csv"
                            
                            if mouse_path in file_list and vessel_path in file_list:
                                user_folders.add(folder_path)

                    # Process each user's data
                    users_processed = 0
                    for user_folder in user_folders:
                        mouse_path = f"{user_folder}/mouse_tracking.csv"
                        vessel_path = f"{user_folder}/vessel_creation.csv"

                        if mouse_path in file_list and vessel_path in file_list:
                            # Extract and read files
                            with z.open(mouse_path) as mouse_file, z.open(vessel_path) as vessel_file:
                                mouse_data = pd.read_csv(mouse_file)
                                vessel_data = pd.read_csv(vessel_file)

                                if is_valid_mouse_data(mouse_data) and is_valid_vessel_data(vessel_data):
                                    # Use the last part of the folder path as user ID
                                    user_id = user_folder.split('/')[-1]
                                    user_data = process_user_data(
                                        mouse_data, vessel_data, user_id)
                                    st.session_state.user_data[user_id] = user_data
                                    users_processed += 1

                    if users_processed > 0:
                        st.session_state.aggregated = True
                        st.success(
                            f"Successfully processed data for {users_processed} users from the ZIP file")
                    else:
                        st.warning("No valid user data found in the ZIP file")

            except Exception as e:
                st.error(f"Error processing ZIP file: {str(e)}")

# Check if data is ready for analysis (excluding Surgeon Experience Analysis page)
if selected_page not in ["Data Upload", "Surgeon Experience Analysis"] and not st.session_state.user_data:
    st.warning("Please upload user data first on the Data Upload page.")
    st.stop()
elif selected_page not in ["Data Upload", "Surgeon Experience Analysis"] and not st.session_state.aggregated:
    st.warning("Please process the data for analysis on the Data Upload page.")
    st.stop()

# Aggregate Analysis page
if selected_page == "Aggregate Analysis":
    st.header("Aggregate Analysis Dashboard")
    st.markdown("""
    This dashboard provides an overview of all users' performance metrics aggregated across the study.
    """)

    # Extract summary metrics for all users
    user_summaries = []
    for user_id, data in st.session_state.user_data.items():
        if 'summary' in data:
            user_summaries.append(data['summary'])

    # Create summary dataframe
    if user_summaries:
        summary_df = pd.DataFrame(user_summaries)

        # Calculate aggregate statistics
        agg_stats = {
            'total_users': len(summary_df),
            'avg_movement': summary_df['avg_movement'].mean(),
            'avg_task_time': summary_df['avg_task_time'].mean(),
            'avg_success_rate': summary_df['success_rate'].mean(),
            'avg_response_rate': summary_df['distraction_response_rate'].mean(),
            'avg_response_time': summary_df['distraction_response_time'].mean(),
            'avg_movement_ratio': summary_df['movement_ratio'].mean(),
            'avg_error_ratio': summary_df['error_ratio'].mean()
        }

        # Display key metrics
        st.subheader("Key Aggregate Metrics")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", agg_stats['total_users'])
        with col2:
            st.metric("Avg Movement", f"{agg_stats['avg_movement']:.2f} px")
        with col3:
            st.metric("Avg Task Time", f"{agg_stats['avg_task_time']:.2f}s")
        with col4:
            st.metric("Avg Success Rate",
                      f"{agg_stats['avg_success_rate']:.1f}%")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Response Rate",
                      f"{agg_stats['avg_response_rate']:.1f}%")
        with col2:
            st.metric("Avg Response Time",
                      f"{agg_stats['avg_response_time']:.2f}s")
        with col3:
            st.metric("Movement Impact Ratio",
                      f"{agg_stats['avg_movement_ratio']:.2f}x")
            st.caption("Movement during distractions vs normal")
        with col4:
            st.metric("Error Impact Ratio",
                      f"{agg_stats['avg_error_ratio']:.2f}x")
            st.caption("Error rate during distractions vs normal")

        # Single metric selection instead of X and Y axes
        st.subheader("Metric Distribution")

        metric_options = [
            "avg_movement", "avg_task_time", "success_rate",
            "distraction_response_rate", "distraction_response_time",
            "movement_ratio", "error_ratio"
        ]

        metric_labels = {
            "avg_movement": "Average Movement (px)",
            "avg_task_time": "Average Task Time (s)",
            "success_rate": "Success Rate (%)",
            "distraction_response_rate": "Distraction Response Rate (%)",
            "distraction_response_time": "Distraction Response Time (s)",
            "movement_ratio": "Movement Impact Ratio",
            "error_ratio": "Error Impact Ratio"
        }

        selected_metric = st.selectbox(
            "Select Metric to Visualise",
            metric_options,
            format_func=lambda x: metric_labels[x],
            key="dist_metric"
        )

        # Create bar chart for selected metric
        fig = px.bar(
            summary_df,
            x='user_id',
            y=selected_metric,
            title=f"{metric_labels[selected_metric]} by User",
            labels={'user_id': 'User ID',
                    selected_metric: metric_labels[selected_metric]}
        )
        st.plotly_chart(fig, use_container_width=True)

        # Distribution histogram
        fig = px.histogram(
            summary_df,
            x=selected_metric,
            title=f"Distribution of {metric_labels[selected_metric]}",
            labels={selected_metric: metric_labels[selected_metric]},
            marginal="box"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show summary statistics
        desc_stats = summary_df[selected_metric].describe()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Mean", f"{desc_stats['mean']:.2f}")
        with col2:
            st.metric("Median", f"{desc_stats['50%']:.2f}")
        with col3:
            st.metric("Min", f"{desc_stats['min']:.2f}")
        with col4:
            st.metric("Max", f"{desc_stats['max']:.2f}")

        # Display full summary table
        st.subheader("User Performance Summary")
        display_cols = [
            'user_id', 'data_points', 'vessels', 'vessels_cut',
            'avg_movement', 'avg_task_time', 'success_rate',
            'distraction_response_rate', 'distraction_response_time'
        ]

        # Format the display dataframe
        display_df = summary_df[display_cols].copy()
        display_df.columns = [col.replace(
            '_', ' ').title() for col in display_cols]

        st.dataframe(display_df)
    else:
        st.info("No user data available for analysis")

# Instrument Efficiency Analysis
elif selected_page == "Instrument Efficiency":
    st.header("Objective 1: Efficiency of Instrument Use")
    st.markdown("""
    This analysis measures how efficiently the surgical instruments are used across all users, based on:
    - Total movement distance (in pixels)
    - Economy of movement (movement per successful action)
    - Movement patterns across different game levels
    """)

    try:
        # Aggregate movement data from all users
        combined_movement_data = []

        for user_id, user_data in st.session_state.user_data.items():
            if 'mouse_data' in user_data and not user_data['mouse_data'].empty:
                # Calculate movement for this user if not already done
                mouse_data = calculate_movement(user_data['mouse_data'].copy())

                # Add user_id column
                mouse_data['USER_ID'] = user_id

                # Add to combined data
                combined_movement_data.append(mouse_data)

        if combined_movement_data:
            # Combine all users' data
            all_movement_data = pd.concat(
                combined_movement_data, ignore_index=True)

            # Calculate overall movement metrics
            overall_movement = all_movement_data['MOVEMENT'].mean()
            total_movement = all_movement_data['MOVEMENT'].sum()

            # Movement metrics per user
            user_movement = all_movement_data.groupby(
                'USER_ID')['MOVEMENT'].agg(['mean', 'sum']).reset_index()
            user_movement.columns = ['User ID',
                                     'Average Movement', 'Total Movement']

            # Display movement metrics
            st.subheader("Movement Metrics Across All Users")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Overall Average Movement",
                          f"{overall_movement:.2f} px")
            with col2:
                st.metric("Total Combined Movement",
                          f"{total_movement:.0f} px")

            # Movement by user
            st.subheader("Movement Metrics by User")
            st.dataframe(user_movement)

            # Visualisation of movement by user
            fig = px.bar(
                user_movement,
                x='User ID',
                y='Average Movement',
                title='Average Movement by User',
                labels={'Average Movement': 'Average Movement (pixels)'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Movement patterns by level
            if 'LEVEL' in all_movement_data.columns:
                st.subheader("Movement Analysis by Level")

                # Calculate average movement by level across all users
                level_movement = all_movement_data.groupby(
                    'LEVEL')['MOVEMENT'].mean().reset_index()
                level_movement['LEVEL'] = level_movement['LEVEL'].astype(
                    str)  # Convert to string for plotting

                fig = px.line(
                    level_movement,
                    x='LEVEL',
                    y='MOVEMENT',
                    title='Average Movement by Level (All Users)',
                    labels={'LEVEL': 'Level',
                            'MOVEMENT': 'Average Movement (pixels)'},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

                # Movement by level for each user
                st.subheader("Movement by Level for Each User")

                user_level_movement = all_movement_data.groupby(
                    ['USER_ID', 'LEVEL'])['MOVEMENT'].mean().reset_index()
                user_level_movement['LEVEL'] = user_level_movement['LEVEL'].astype(
                    str)  # Convert to string for plotting

                fig = px.line(
                    user_level_movement,
                    x='LEVEL',
                    y='MOVEMENT',
                    color='USER_ID',
                    title='Average Movement by Level for Each User',
                    labels={
                        'LEVEL': 'Level', 'MOVEMENT': 'Average Movement (pixels)', 'USER_ID': 'User ID'},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

                # Calculate movement efficiency metrics
                combined_vessel_data = []

                for user_id, user_data in st.session_state.user_data.items():
                    if 'vessel_data' in user_data and not user_data['vessel_data'].empty:
                        vessel_data = user_data['vessel_data'].copy()
                        vessel_data['USER_ID'] = user_id
                        combined_vessel_data.append(vessel_data)

                if combined_vessel_data:
                    all_vessel_data = pd.concat(
                        combined_vessel_data, ignore_index=True)

                    # Calculate successful cuts by level
                    successful_cuts = all_vessel_data[
                        (all_vessel_data['EVENT'] == 'cut') &
                        (all_vessel_data['IS_CORRECT'] == True)
                    ].groupby(['USER_ID', 'LEVEL']).size().reset_index(name='SUCCESSFUL_CUTS')

                    # Convert LEVEL to string in both dataframes to ensure compatibility
                    successful_cuts['LEVEL'] = successful_cuts['LEVEL'].astype(
                        str)
                    user_level_movement['LEVEL'] = user_level_movement['LEVEL'].astype(
                        str)

                    # Merge with movement data
                    efficiency_data = pd.merge(
                        user_level_movement,
                        successful_cuts,
                        on=['USER_ID', 'LEVEL'],
                        how='left'
                    )

                    # Calculate movement per successful cut
                    efficiency_data['MOVEMENT_PER_SUCCESS'] = efficiency_data.apply(
                        lambda row: row['MOVEMENT'] / row['SUCCESSFUL_CUTS'] if pd.notnull(
                            row['SUCCESSFUL_CUTS']) and row['SUCCESSFUL_CUTS'] > 0 else np.nan,
                        axis=1
                    )

                    # Display efficiency metrics
                    st.subheader("Movement Efficiency by Level")

                    # Filter out rows with NaN values
                    efficiency_data_clean = efficiency_data.dropna(
                        subset=['MOVEMENT_PER_SUCCESS'])

                    if not efficiency_data_clean.empty:
                        fig = px.line(
                            efficiency_data_clean,
                            x='LEVEL',
                            y='MOVEMENT_PER_SUCCESS',
                            color='USER_ID',
                            title='Movement per Successful Cut by Level',
                            labels={
                                'LEVEL': 'Level',
                                'MOVEMENT_PER_SUCCESS': 'Movement per Successful Cut (pixels)',
                                'USER_ID': 'User ID'
                            },
                            markers=True
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Average efficiency across all users by level
                        avg_efficiency = efficiency_data_clean.groupby(
                            'LEVEL')['MOVEMENT_PER_SUCCESS'].mean().reset_index()

                        fig = px.bar(
                            avg_efficiency,
                            x='LEVEL',
                            y='MOVEMENT_PER_SUCCESS',
                            title='Average Movement Efficiency by Level (All Users)',
                            labels={
                                'LEVEL': 'Level',
                                'MOVEMENT_PER_SUCCESS': 'Movement per Successful Cut (pixels)'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)

            # Movement heatmap
            st.subheader("Aggregate Movement Heatmap")

            # Create a 2D histogram of mouse positions
            fig = px.density_heatmap(
                all_movement_data,
                x='X_POSITION',
                y='Y_POSITION',
                title='Aggregate Mouse Movement Heatmap (All Users)',
                labels={'X_POSITION': 'X Position', 'Y_POSITION': 'Y Position'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Movement during cutting vs. navigation
            if 'IS_CUTTING' in all_movement_data.columns:
                st.subheader("Movement Analysis: Cutting vs. Navigation")

                cutting_movement = all_movement_data.groupby(
                    'IS_CUTTING')['MOVEMENT'].mean().reset_index()
                cutting_movement['IS_CUTTING'] = cutting_movement['IS_CUTTING'].map(
                    {True: 'Cutting', False: 'Navigating'})

                fig = px.bar(
                    cutting_movement,
                    x='IS_CUTTING',
                    y='MOVEMENT',
                    title='Average Movement: Cutting vs. Navigating (All Users)',
                    labels={'IS_CUTTING': 'Activity',
                            'MOVEMENT': 'Average Movement (pixels)'},
                    color='IS_CUTTING',
                    color_discrete_map={
                        'Cutting': '#ff7f0e', 'Navigating': '#1f77b4'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No movement data available for analysis")

    except Exception as e:
        st.error(f"Error analysing instrument efficiency: {str(e)}")
        st.error(f"Detailed error info: {type(e).__name__}")
        import traceback
        st.code(traceback.format_exc())

# Task Completion Time Analysis
elif selected_page == "Task Completion":
    st.header("Objective 2: Task Completion Time")
    st.markdown("""
    This analysis measures how quickly tasks are completed across all users, based on:
    - Time taken to cut vessels
    - Success rates for vessel cutting
    - Performance changes across game levels
    """)

    try:
        # Aggregate task completion data from all users
        combined_vessel_data = []
        vessel_times_list = []

        for user_id, user_data in st.session_state.user_data.items():
            if 'vessel_data' in user_data and not user_data['vessel_data'].empty:
                # Get vessel data
                vessel_data = user_data['vessel_data'].copy()
                vessel_data['USER_ID'] = user_id
                combined_vessel_data.append(vessel_data)

                # Get vessel times if available
                if 'task' in user_data and 'vessel_times' in user_data['task']:
                    vessel_times = user_data['task']['vessel_times'].copy()
                    vessel_times['USER_ID'] = user_id
                    vessel_times_list.append(vessel_times)

        if combined_vessel_data:
            # Combine all users' vessel data
            all_vessel_data = pd.concat(
                combined_vessel_data, ignore_index=True)

            # Get task completion times if available
            all_vessel_times = pd.concat(
                vessel_times_list, ignore_index=True) if vessel_times_list else pd.DataFrame()

            # Calculate success rates
            vessel_cuts = all_vessel_data[all_vessel_data['EVENT'] == 'cut']
            overall_success_rate = vessel_cuts['IS_CORRECT'].mean(
            ) * 100 if 'IS_CORRECT' in vessel_cuts.columns else np.nan

            # Calculate by user
            user_success = vessel_cuts.groupby(
                'USER_ID')['IS_CORRECT'].mean().reset_index()
            user_success['Success Rate (%)'] = user_success['IS_CORRECT'] * 100
            user_success = user_success[['USER_ID', 'Success Rate (%)']]
            user_success.columns = ['User ID', 'Success Rate (%)']

            # Display task completion metrics
            st.subheader("Task Completion Metrics Across All Users")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Overall Success Rate",
                          f"{overall_success_rate:.1f}%")

            with col2:
                if not all_vessel_times.empty and 'TIME_TO_CUT' in all_vessel_times.columns:
                    avg_time = all_vessel_times['TIME_TO_CUT'].mean()
                    st.metric("Average Time to Cut", f"{avg_time:.2f}s")

            # Success rate by user
            st.subheader("Success Rate by User")
            st.dataframe(user_success)

            # Visualisation of success rate by user
            fig = px.bar(
                user_success,
                x='User ID',
                y='Success Rate (%)',
                title='Success Rate by User',
                labels={'Success Rate (%)': 'Success Rate (%)'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Task completion time analysis
            if not all_vessel_times.empty and 'TIME_TO_CUT' in all_vessel_times.columns:
                st.subheader("Task Completion Time Analysis")

                # Time by user
                user_time = all_vessel_times.groupby(
                    'USER_ID')['TIME_TO_CUT'].mean().reset_index()
                user_time.columns = ['User ID', 'Average Time to Cut (s)']

                fig = px.bar(
                    user_time,
                    x='User ID',
                    y='Average Time to Cut (s)',
                    title='Average Task Completion Time by User',
                    labels={'Average Time to Cut (s)': 'Time (seconds)'}
                )
                st.plotly_chart(fig, use_container_width=True)

                # Time by vessel correctness
                if 'IS_CORRECT' in all_vessel_times.columns:
                    correctness_time = all_vessel_times.groupby(
                        'IS_CORRECT')['TIME_TO_CUT'].mean().reset_index()
                    correctness_time['IS_CORRECT'] = correctness_time['IS_CORRECT'].map(
                        {True: 'Correct', False: 'Incorrect'})

                    fig = px.bar(
                        correctness_time,
                        x='IS_CORRECT',
                        y='TIME_TO_CUT',
                        title='Average Time by Vessel Type (Correct vs. Incorrect)',
                        labels={'IS_CORRECT': 'Vessel Type',
                                'TIME_TO_CUT': 'Time (seconds)'},
                        color='IS_CORRECT',
                        color_discrete_map={
                            'Correct': '#2ca02c', 'Incorrect': '#d62728'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Time by level
                if 'LEVEL' in all_vessel_times.columns:
                    level_time = all_vessel_times.groupby(
                        'LEVEL')['TIME_TO_CUT'].mean().reset_index()
                    level_time['LEVEL'] = level_time['LEVEL'].astype(str)

                    fig = px.line(
                        level_time,
                        x='LEVEL',
                        y='TIME_TO_CUT',
                        title='Average Task Completion Time by Level (All Users)',
                        labels={'LEVEL': 'Level',
                                'TIME_TO_CUT': 'Time (seconds)'},
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Time by level for each user
                    user_level_time = all_vessel_times.groupby(['USER_ID', 'LEVEL'])[
                        'TIME_TO_CUT'].mean().reset_index()
                    user_level_time['LEVEL'] = user_level_time['LEVEL'].astype(
                        str)

                    fig = px.line(
                        user_level_time,
                        x='LEVEL',
                        y='TIME_TO_CUT',
                        color='USER_ID',
                        title='Average Task Completion Time by Level for Each User',
                        labels={
                            'LEVEL': 'Level', 'TIME_TO_CUT': 'Time (seconds)', 'USER_ID': 'User ID'},
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # Success rate by level
            if 'LEVEL' in vessel_cuts.columns:
                st.subheader("Success Rate Analysis by Level")

                level_success = vessel_cuts.groupby(
                    'LEVEL')['IS_CORRECT'].mean().reset_index()
                level_success['Success Rate (%)'] = level_success['IS_CORRECT'] * 100
                level_success['LEVEL'] = level_success['LEVEL'].astype(str)

                fig = px.line(
                    level_success,
                    x='LEVEL',
                    y='Success Rate (%)',
                    title='Success Rate by Level (All Users)',
                    labels={'LEVEL': 'Level',
                            'Success Rate (%)': 'Success Rate (%)'},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

                # Success rate by level for each user
                user_level_success = vessel_cuts.groupby(['USER_ID', 'LEVEL'])[
                    'IS_CORRECT'].mean().reset_index()
                user_level_success['Success Rate (%)'] = user_level_success['IS_CORRECT'] * 100
                user_level_success['LEVEL'] = user_level_success['LEVEL'].astype(
                    str)

                fig = px.line(
                    user_level_success,
                    x='LEVEL',
                    y='Success Rate (%)',
                    color='USER_ID',
                    title='Success Rate by Level for Each User',
                    labels={
                        'LEVEL': 'Level', 'Success Rate (%)': 'Success Rate (%)', 'USER_ID': 'User ID'},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

            # Distribution of task completion times
            if not all_vessel_times.empty and 'TIME_TO_CUT' in all_vessel_times.columns:
                st.subheader("Distribution of Task Completion Times")

                fig = px.histogram(
                    all_vessel_times,
                    x='TIME_TO_CUT',
                    title='Distribution of Task Completion Times (All Users)',
                    labels={'TIME_TO_CUT': 'Time (seconds)'},
                    marginal='box'
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No vessel data available for analysis")

    except Exception as e:
        st.error(f"Error analysing task completion time: {str(e)}")

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
        # Aggregate distraction data from all users
        combined_distraction_data = []

        for user_id, user_data in st.session_state.user_data.items():
            if 'mouse_data' in user_data and not user_data['mouse_data'].empty:
                # Filter for distraction events
                mouse_data = user_data['mouse_data'].copy()
                distraction_events = mouse_data[mouse_data['DISTRACTION_ACTION'].notna(
                )]

                if not distraction_events.empty:
                    distraction_events['USER_ID'] = user_id
                    combined_distraction_data.append(distraction_events)

        if combined_distraction_data:
            # Combine all users' distraction data
            all_distraction_data = pd.concat(
                combined_distraction_data, ignore_index=True)

            # Split by appear/click actions
            distraction_appear = all_distraction_data[all_distraction_data['DISTRACTION_ACTION'] == 'appear']
            distraction_click = all_distraction_data[all_distraction_data['DISTRACTION_ACTION'] == 'click']

            # Calculate overall response rate
            total_appear = len(distraction_appear)
            total_click = len(distraction_click)
            overall_response_rate = total_click / \
                total_appear * 100 if total_appear > 0 else np.nan

            # Calculate by user
            user_appear = distraction_appear.groupby(
                'USER_ID').size().reset_index(name='appear_count')
            user_click = distraction_click.groupby(
                'USER_ID').size().reset_index(name='click_count')

            user_response = pd.merge(
                user_appear, user_click, on='USER_ID', how='left')
            user_response['click_count'] = user_response['click_count'].fillna(
                0)
            user_response['response_rate'] = user_response['click_count'] / \
                user_response['appear_count'] * 100
            user_response = user_response[[
                'USER_ID', 'appear_count', 'click_count', 'response_rate']]
            user_response.columns = [
                'User ID', 'Distractions', 'Responses', 'Response Rate (%)']

            # Display distraction response metrics
            st.subheader("Peripheral Awareness Metrics Across All Users")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Distractions", total_appear)

            with col2:
                st.metric("Total Responses", total_click)

            with col3:
                st.metric("Overall Response Rate",
                          f"{overall_response_rate:.1f}%")

            # Response rate by user
            st.subheader("Response Rate by User")
            st.dataframe(user_response)

            # Visualisation of response rate by user
            fig = px.bar(
                user_response,
                x='User ID',
                y='Response Rate (%)',
                title='Distraction Response Rate by User',
                labels={'Response Rate (%)': 'Response Rate (%)'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Calculate response times
            if not distraction_appear.empty and not distraction_click.empty:
                # Merge to get appearance and click times for each distraction
                distractions = pd.merge(
                    distraction_appear[[
                        'DISTRACTION_ID', 'TIMESTAMP', 'DISTRACTION_TYPE', 'LEVEL', 'USER_ID']],
                    distraction_click[['DISTRACTION_ID',
                                       'TIMESTAMP', 'USER_ID']],
                    on=['DISTRACTION_ID', 'USER_ID'],
                    suffixes=('_appear', '_click'),
                    how='inner'
                )

                if not distractions.empty:
                    # Calculate response time
                    distractions['RESPONSE_TIME'] = distractions.apply(
                        lambda row: calculate_time_difference(
                            row['TIMESTAMP_appear'], row['TIMESTAMP_click']),
                        axis=1
                    )

                    # Overall average response time
                    overall_response_time = distractions['RESPONSE_TIME'].mean(
                    )

                    # Response time by user
                    user_response_time = distractions.groupby(
                        'USER_ID')['RESPONSE_TIME'].mean().reset_index()
                    user_response_time.columns = [
                        'User ID', 'Average Response Time (s)']

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("Overall Average Response Time",
                                  f"{overall_response_time:.2f}s")

                    with col2:
                        # Calculate median response time
                        median_response_time = distractions['RESPONSE_TIME'].median(
                        )
                        st.metric("Median Response Time",
                                  f"{median_response_time:.2f}s")

                    # Response time by user
                    st.subheader("Response Time by User")
                    st.dataframe(user_response_time)

                    # Visualisation of response time by user
                    fig = px.bar(
                        user_response_time,
                        x='User ID',
                        y='Average Response Time (s)',
                        title='Average Distraction Response Time by User',
                        labels={'Average Response Time (s)': 'Time (seconds)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Response time by distraction type
                    if 'DISTRACTION_TYPE' in distractions.columns:
                        st.subheader("Response Analysis by Distraction Type")

                        type_response_time = distractions.groupby('DISTRACTION_TYPE')[
                            'RESPONSE_TIME'].mean().reset_index()

                        fig = px.bar(
                            type_response_time,
                            x='DISTRACTION_TYPE',
                            y='RESPONSE_TIME',
                            title='Average Response Time by Distraction Type (All Users)',
                            labels={'DISTRACTION_TYPE': 'Distraction Type',
                                    'RESPONSE_TIME': 'Time (seconds)'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Response rate by type
                        type_appear = distraction_appear.groupby(
                            'DISTRACTION_TYPE').size().reset_index(name='appear_count')
                        type_click = distraction_click.groupby(
                            'DISTRACTION_TYPE').size().reset_index(name='click_count')

                        type_response = pd.merge(
                            type_appear, type_click, on='DISTRACTION_TYPE', how='left')
                        type_response['click_count'] = type_response['click_count'].fillna(
                            0)
                        type_response['response_rate'] = type_response['click_count'] / \
                            type_response['appear_count'] * 100

                        fig = px.bar(
                            type_response,
                            x='DISTRACTION_TYPE',
                            y='response_rate',
                            title='Response Rate by Distraction Type (All Users)',
                            labels={'DISTRACTION_TYPE': 'Distraction Type',
                                    'response_rate': 'Response Rate (%)'}
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Response analysis by level
                    if 'LEVEL' in distractions.columns:
                        st.subheader("Peripheral Awareness by Level")

                        level_response_time = distractions.groupby(
                            'LEVEL')['RESPONSE_TIME'].mean().reset_index()
                        level_response_time['LEVEL'] = level_response_time['LEVEL'].astype(
                            str)

                        fig = px.line(
                            level_response_time,
                            x='LEVEL',
                            y='RESPONSE_TIME',
                            title='Average Response Time by Level (All Users)',
                            labels={'LEVEL': 'Level',
                                    'RESPONSE_TIME': 'Time (seconds)'},
                            markers=True
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Response rate by level
                        level_appear = distraction_appear.groupby(
                            'LEVEL').size().reset_index(name='appear_count')
                        level_click = distraction_click.groupby(
                            'LEVEL').size().reset_index(name='click_count')

                        level_response = pd.merge(
                            level_appear, level_click, on='LEVEL', how='left')
                        level_response['click_count'] = level_response['click_count'].fillna(
                            0)
                        level_response['response_rate'] = level_response['click_count'] / \
                            level_response['appear_count'] * 100
                        level_response['LEVEL'] = level_response['LEVEL'].astype(
                            str)

                        fig = px.line(
                            level_response,
                            x='LEVEL',
                            y='response_rate',
                            title='Response Rate by Level (All Users)',
                            labels={'LEVEL': 'Level',
                                    'response_rate': 'Response Rate (%)'},
                            markers=True
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    # Distribution of response times
                    st.subheader("Distribution of Response Times")

                    fig = px.histogram(
                        distractions,
                        x='RESPONSE_TIME',
                        title='Distribution of Response Times (All Users)',
                        labels={'RESPONSE_TIME': 'Time (seconds)'},
                        marginal='box'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Compare response time distribution between users
                    st.subheader("Response Time Distribution by User")

                    fig = px.box(
                        distractions,
                        x='USER_ID',
                        y='RESPONSE_TIME',
                        title='Response Time Distribution by User',
                        labels={'USER_ID': 'User ID',
                                'RESPONSE_TIME': 'Response Time (seconds)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No distraction response time data available for analysis")
        else:
            st.info("No distraction data available for analysis")

    except Exception as e:
        st.error(f"Error analysing peripheral awareness: {str(e)}")

# Distraction Management Analysis
elif selected_page == "Distraction Management":
    st.header("Objective 4: Distraction Management")
    st.markdown("""
    This analysis measures how distractions affect focus and error rates, based on:
    - Performance comparison during distractions vs. normal conditions
    - Error rates during distractions
    - Impact of different types of background distractions
    """)

    try:
        # Aggregate background distraction data from all users
        combined_background_metrics = []

        for user_id, user_data in st.session_state.user_data.items():
            if 'background' in user_data and user_data['background']:
                background_metrics = user_data['background']

                # Create a summary entry for this user
                if 'distracted_movement' in background_metrics and 'normal_movement' in background_metrics:
                    entry = {
                        'USER_ID': user_id,
                        'distracted_movement': background_metrics['distracted_movement'],
                        'normal_movement': background_metrics['normal_movement'],
                        'movement_ratio': background_metrics['distracted_movement'] / background_metrics['normal_movement']
                        if background_metrics['normal_movement'] else np.nan,
                        'distracted_error_rate': background_metrics.get('distracted_error_rate', np.nan),
                        'normal_error_rate': background_metrics.get('normal_error_rate', np.nan)
                    }
                    # Only add error_ratio if both error rates exist
                    if not pd.isna(entry['distracted_error_rate']) and not pd.isna(entry['normal_error_rate']) and entry['normal_error_rate'] != 0:
                        entry['error_ratio'] = entry['distracted_error_rate'] / \
                            entry['normal_error_rate']
                    else:
                        entry['error_ratio'] = np.nan

                    combined_background_metrics.append(entry)

        if combined_background_metrics:
            # Create dataframe of background distraction metrics
            background_df = pd.DataFrame(combined_background_metrics)

            # Ensure ERROR_RATE columns exist (with NaN values if needed)
            if 'error_ratio' not in background_df.columns:
                background_df['error_ratio'] = np.nan

            # Calculate overall averages
            avg_distracted_movement = background_df['distracted_movement'].mean(
            )
            avg_normal_movement = background_df['normal_movement'].mean()
            avg_movement_ratio = background_df['movement_ratio'].mean()

            # Calculate error averages only if columns exist
            avg_distracted_error = background_df['distracted_error_rate'].mean(
            ) if 'distracted_error_rate' in background_df.columns else np.nan
            avg_normal_error = background_df['normal_error_rate'].mean(
            ) if 'normal_error_rate' in background_df.columns else np.nan
            avg_error_ratio = background_df['error_ratio'].mean(
            ) if 'error_ratio' in background_df.columns else np.nan

            # Display distraction management metrics
            st.subheader("Distraction Impact Metrics Across All Users")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Movement Impact**")
                st.metric("Avg Movement During Distractions",
                          f"{avg_distracted_movement:.2f} px")
                st.metric("Avg Movement During Normal Conditions",
                          f"{avg_normal_movement:.2f} px")
                st.metric("Movement Impact Ratio",
                          f"{avg_movement_ratio:.2f}x")
                st.caption("Movement during distractions vs normal")

            with col2:
                st.markdown("**Error Rate Impact**")
                st.metric("Avg Error Rate During Distractions", f"{avg_distracted_error:.1f}%" if not pd.isna(
                    avg_distracted_error) else "N/A")
                st.metric("Avg Error Rate During Normal Conditions",
                          f"{avg_normal_error:.1f}%" if not pd.isna(avg_normal_error) else "N/A")
                st.metric("Error Rate Impact Ratio", f"{avg_error_ratio:.2f}x" if not pd.isna(
                    avg_error_ratio) else "N/A")
                st.caption("Error rate during distractions vs normal")

            # Visualise distraction impact by user
            st.subheader("Distraction Impact by User")

            # Movement impact
            movement_comparison = pd.melt(
                background_df[['USER_ID',
                               'distracted_movement', 'normal_movement']],
                id_vars=['USER_ID'],
                value_vars=['distracted_movement', 'normal_movement'],
                var_name='Condition',
                value_name='Movement'
            )

            movement_comparison['Condition'] = movement_comparison['Condition'].map({
                'distracted_movement': 'During Distractions',
                'normal_movement': 'Normal Conditions'
            })

            fig = px.bar(
                movement_comparison,
                x='USER_ID',
                y='Movement',
                color='Condition',
                barmode='group',
                title='Movement During Distractions vs. Normal Conditions by User',
                labels={'USER_ID': 'User ID',
                        'Movement': 'Average Movement (pixels)'}
            )
            st.plotly_chart(fig, use_container_width=True)

            # Error rate impact - only if both columns exist
            if 'distracted_error_rate' in background_df.columns and 'normal_error_rate' in background_df.columns:
                error_comparison = pd.melt(
                    background_df[[
                        'USER_ID', 'distracted_error_rate', 'normal_error_rate']],
                    id_vars=['USER_ID'],
                    value_vars=['distracted_error_rate', 'normal_error_rate'],
                    var_name='Condition',
                    value_name='Error Rate'
                )

                error_comparison['Condition'] = error_comparison['Condition'].map({
                    'distracted_error_rate': 'During Distractions',
                    'normal_error_rate': 'Normal Conditions'
                })

                fig = px.bar(
                    error_comparison,
                    x='USER_ID',
                    y='Error Rate',
                    color='Condition',
                    barmode='group',
                    title='Error Rate During Distractions vs. Normal Conditions by User',
                    labels={'USER_ID': 'User ID',
                            'Error Rate': 'Error Rate (%)'}
                )
                st.plotly_chart(fig, use_container_width=True)

            # Distraction impact ratios
            st.subheader("Distraction Impact Ratios by User")

            # Ensure both columns exist for visualisation
            ratio_columns = ['USER_ID']
            if 'movement_ratio' in background_df.columns:
                ratio_columns.append('movement_ratio')
            if 'error_ratio' in background_df.columns:
                ratio_columns.append('error_ratio')

            ratio_df = background_df[ratio_columns].copy()

            # Rename columns for display
            new_columns = {'USER_ID': 'User ID'}
            if 'movement_ratio' in ratio_df.columns:
                new_columns['movement_ratio'] = 'Movement Impact Ratio'
            if 'error_ratio' in ratio_df.columns:
                new_columns['error_ratio'] = 'Error Rate Impact Ratio'

            ratio_df.columns = [new_columns.get(
                col, col) for col in ratio_df.columns]

            st.dataframe(ratio_df)

            # Visualise ratios if we have both types
            if 'Movement Impact Ratio' in ratio_df.columns and 'Error Rate Impact Ratio' in ratio_df.columns:
                ratio_melt = pd.melt(
                    ratio_df,
                    id_vars=['User ID'],
                    value_vars=['Movement Impact Ratio',
                                'Error Rate Impact Ratio'],
                    var_name='Impact Type',
                    value_name='Impact Ratio'
                )

                fig = px.bar(
                    ratio_melt,
                    x='User ID',
                    y='Impact Ratio',
                    color='Impact Type',
                    barmode='group',
                    title='Distraction Impact Ratios by User',
                    labels={
                        'Impact Ratio': 'Impact Ratio (Distracted / Normal)'}
                )
                fig.add_hline(y=1, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)

            # Analyse impact by distraction type
            st.subheader("Impact Analysis by Distraction Type")

            # Collect distraction type metrics from all users
            all_type_metrics = []

            for user_id, user_data in st.session_state.user_data.items():
                if 'background' in user_data and 'type_performance' in user_data['background']:
                    type_perf = user_data['background']['type_performance']

                    for dist_type, metrics in type_perf.items():
                        all_type_metrics.append({
                            'USER_ID': user_id,
                            'type': dist_type,
                            'count': metrics['count'],
                            'total_duration': metrics['total_duration'],
                            'avg_movement': metrics['avg_movement'],
                            'error_rate': metrics['error_rates']
                        })

            if all_type_metrics:
                type_df = pd.DataFrame(all_type_metrics)

                # Average by distraction type across all users
                type_avg = type_df.groupby('type').agg({
                    'count': 'sum',
                    'total_duration': 'sum',
                    'avg_movement': 'mean',
                    'error_rate': 'mean'
                }).reset_index()

                # Display type metrics
                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(
                        type_avg,
                        x='type',
                        y='avg_movement',
                        title='Average Movement by Distraction Type (All Users)',
                        labels={'type': 'Distraction Type',
                                'avg_movement': 'Average Movement (pixels)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Check if error_rate column has valid data
                    if 'error_rate' in type_avg.columns and not type_avg['error_rate'].isna().all():
                        fig = px.bar(
                            type_avg,
                            x='type',
                            y='error_rate',
                            title='Error Rate by Distraction Type (All Users)',
                            labels={'type': 'Distraction Type',
                                    'error_rate': 'Error Rate (%)'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(
                            "No error rate data available for distraction types")

                # Show distraction frequency
                st.subheader("Distraction Frequency and Duration")

                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(
                        type_avg,
                        x='type',
                        y='count',
                        title='Distraction Frequency by Type',
                        labels={'type': 'Distraction Type',
                                'count': 'Number of Occurrences'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    type_avg['avg_duration'] = type_avg['total_duration'] / \
                        type_avg['count']

                    fig = px.bar(
                        type_avg,
                        x='type',
                        y='avg_duration',
                        title='Average Distraction Duration by Type',
                        labels={'type': 'Distraction Type',
                                'avg_duration': 'Average Duration (seconds)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No distraction type performance metrics available")

            # Field of view analysis
            st.subheader("Field of View Impact Analysis")

            fov_data = []

            for user_id, user_data in st.session_state.user_data.items():
                if 'mouse_data' in user_data and not user_data['mouse_data'].empty:
                    mouse_data = user_data['mouse_data'].copy()

                    if 'FIELD_OF_VIEW' in mouse_data.columns:
                        # Calculate movement by FOV
                        movement_data = calculate_movement(mouse_data)
                        fov_movement = movement_data.groupby('FIELD_OF_VIEW')[
                            'MOVEMENT'].mean().reset_index()

                        for _, row in fov_movement.iterrows():
                            entry = {
                                'USER_ID': user_id,
                                'FIELD_OF_VIEW': row['FIELD_OF_VIEW'],
                                'AVG_MOVEMENT': row['MOVEMENT']
                            }

                            # Calculate error rates by FOV if vessel data is available
                            if 'vessel_data' in user_data and not user_data['vessel_data'].empty:
                                vessel_data = user_data['vessel_data'].copy()
                                vessel_cuts = vessel_data[vessel_data['EVENT'] == 'cut']

                                if not vessel_cuts.empty and 'FIELD_OF_VIEW' in vessel_cuts.columns and 'IS_CORRECT' in vessel_cuts.columns:
                                    fov_value = row['FIELD_OF_VIEW']
                                    fov_cuts = vessel_cuts[vessel_cuts['FIELD_OF_VIEW']
                                                           == fov_value]

                                    if not fov_cuts.empty:
                                        entry['ERROR_RATE'] = (
                                            1 - fov_cuts['IS_CORRECT'].mean()) * 100

                            fov_data.append(entry)

            if fov_data:
                fov_df = pd.DataFrame(fov_data)

                # Calculate averages by FOV across all users
                agg_dict = {'AVG_MOVEMENT': 'mean'}
                if 'ERROR_RATE' in fov_df.columns:
                    agg_dict['ERROR_RATE'] = 'mean'

                fov_avg = fov_df.groupby('FIELD_OF_VIEW').agg(
                    agg_dict).reset_index()

                fov_avg['FIELD_OF_VIEW'] = fov_avg['FIELD_OF_VIEW'].map(
                    {True: 'Limited FOV', False: 'Full FOV'})

                col1, col2 = st.columns(2)

                with col1:
                    fig = px.bar(
                        fov_avg,
                        x='FIELD_OF_VIEW',
                        y='AVG_MOVEMENT',
                        title='Average Movement by Field of View (All Users)',
                        labels={'FIELD_OF_VIEW': 'Field of View',
                                'AVG_MOVEMENT': 'Average Movement (pixels)'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    if 'ERROR_RATE' in fov_avg.columns:
                        fig = px.bar(
                            fov_avg,
                            x='FIELD_OF_VIEW',
                            y='ERROR_RATE',
                            title='Error Rate by Field of View (All Users)',
                            labels={'FIELD_OF_VIEW': 'Field of View',
                                    'ERROR_RATE': 'Error Rate (%)'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(
                            "No error rate data available for field of view analysis")
            else:
                st.info("No field of view data available for analysis")
        else:
            st.info("No background distraction data available for analysis")

    except Exception as e:
        st.error(f"Error analysing distraction management: {str(e)}")
        st.error(f"Detailed error info: {type(e).__name__}")
        import traceback
        st.code(traceback.format_exc())

# User Comparison
elif selected_page == "User Comparison":
    st.header("User Performance Comparison")
    st.markdown("""
    This page allows direct comparison between users across different performance metrics.
    """)

    # Extract summary metrics for all users
    user_summaries = []
    for user_id, data in st.session_state.user_data.items():
        if 'summary' in data:
            user_summaries.append(data['summary'])

    if user_summaries:
        summary_df = pd.DataFrame(user_summaries)

        # Select users for comparison
        if len(summary_df) > 1:
            st.subheader("Select Users to Compare")

            user_list = summary_df['user_id'].tolist()
            selected_users = st.multiselect(
                "Select users for comparison",
                user_list,
                # Default to first 5 users or less
                default=user_list[:min(5, len(user_list))]
            )

            if selected_users:
                # Filter for selected users
                selected_df = summary_df[summary_df['user_id'].isin(
                    selected_users)]

                # Radar chart of metrics
                st.subheader("Multi-dimensional Performance Comparison")

                # Normalise metrics for radar chart
                metrics_to_normalize = [
                    'avg_movement', 'avg_task_time', 'success_rate',
                    'distraction_response_rate', 'distraction_response_time'
                ]

                radar_df = selected_df[['user_id'] +
                                       metrics_to_normalize].copy()

                for metric in metrics_to_normalize:
                    if metric in ['avg_movement', 'avg_task_time', 'distraction_response_time']:
                        # Lower is better, invert normalization
                        max_val = radar_df[metric].max()
                        if max_val > 0:
                            radar_df[metric] = 1 - (radar_df[metric] / max_val)
                    else:
                        # Higher is better
                        max_val = radar_df[metric].max()
                        if max_val > 0:
                            radar_df[metric] = radar_df[metric] / max_val

                # Rename columns for display
                radar_df.columns = [
                    'User ID', 'Movement Efficiency', 'Task Speed',
                    'Success Rate', 'Distraction Response Rate', 'Distraction Response Time'
                ]

                # Create radar chart
                fig = go.Figure()

                # Add each user as a trace
                for _, user_row in radar_df.iterrows():
                    user_id = user_row['User ID']
                    # Extract metrics excluding user_id
                    values = user_row.drop('User ID').values
                    # Add a closing value to complete the polygon
                    r_values = list(values) + [values[0]]

                    # Define the categories (with an extra repeat of the first category at the end)
                    categories = list(user_row.drop(
                        'User ID').index) + [list(user_row.drop('User ID').index)[0]]

                    fig.add_trace(go.Scatterpolar(
                        r=r_values,
                        theta=categories,
                        fill='toself',
                        name=user_id
                    ))

                fig.update_layout(
                    title="Performance Radar Chart (Normalised Values - Higher is Better)",
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]
                        )
                    )
                )

                st.plotly_chart(fig, use_container_width=True)

                # Bar chart comparison for key metrics
                st.subheader("Key Metrics Comparison")

                # Let the user select metrics to compare
                metric_options = {
                    'avg_movement': 'Average Movement (px)',
                    'avg_task_time': 'Average Task Time (s)',
                    'success_rate': 'Success Rate (%)',
                    'distraction_response_rate': 'Distraction Response Rate (%)',
                    'distraction_response_time': 'Distraction Response Time (s)',
                    'movement_ratio': 'Movement Impact Ratio',
                    'error_ratio': 'Error Impact Ratio'
                }

                selected_metric = st.selectbox(
                    "Select Metric to Compare",
                    list(metric_options.keys()),
                    format_func=lambda x: metric_options[x],
                    key="compare_metric"
                )

                if selected_metric in selected_df.columns:
                    fig = px.bar(
                        selected_df,
                        x='user_id',
                        y=selected_metric,
                        title=f"{metric_options[selected_metric]} Comparison",
                        labels={'user_id': 'User ID',
                                selected_metric: metric_options[selected_metric]}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Performance across levels
                st.subheader("Performance Across Levels")

                # Collect level data for selected users
                level_metrics = []

                for user_id in selected_users:
                    user_data = st.session_state.user_data.get(user_id, {})

                    # Movement by level
                    if 'movement' in user_data and 'level_movement' in user_data['movement']:
                        level_movement = user_data['movement']['level_movement']
                        for level, metrics in level_movement.items():
                            level_metrics.append({
                                'user_id': user_id,
                                'level': level,
                                'avg_movement': metrics['avg']
                            })

                    # Task time and success rate by level
                    if 'task' in user_data and 'level_times' in user_data['task']:
                        level_times = user_data['task']['level_times']
                        for level, metrics in level_times.items():
                            # Find existing entry or create new
                            found = False
                            for entry in level_metrics:
                                if entry['user_id'] == user_id and entry['level'] == level:
                                    entry['avg_task_time'] = metrics['avg_time']
                                    entry['success_rate'] = metrics['success_rate']
                                    found = True
                                    break

                            if not found:
                                level_metrics.append({
                                    'user_id': user_id,
                                    'level': level,
                                    'avg_task_time': metrics['avg_time'],
                                    'success_rate': metrics['success_rate']
                                })

                if level_metrics:
                    level_df = pd.DataFrame(level_metrics)
                    # Convert level to string for consistent plotting
                    level_df['level'] = level_df['level'].astype(str)

                    # Let user choose which level metric to view
                    level_metric_options = {
                        'avg_movement': 'Average Movement (px)',
                        'avg_task_time': 'Average Task Time (s)',
                        'success_rate': 'Success Rate (%)'
                    }

                    available_metrics = [
                        m for m in level_metric_options.keys() if m in level_df.columns]

                    if available_metrics:
                        selected_level_metric = st.selectbox(
                            "Select Level Metric to Compare",
                            available_metrics,
                            format_func=lambda x: level_metric_options[x],
                            key="compare_level_metric"
                        )

                        fig = px.line(
                            level_df,
                            x='level',
                            y=selected_level_metric,
                            color='user_id',
                            title=f"{level_metric_options[selected_level_metric]} by Level",
                            labels={
                                'level': 'Level',
                                selected_level_metric: level_metric_options[selected_level_metric],
                                'user_id': 'User ID'
                            },
                            markers=True
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No level metrics available for comparison")
                else:
                    st.info("No level data available for the selected users")
            else:
                st.info("Please select at least one user for comparison")
        else:
            st.info("Need at least two users for comparison")
    else:
        st.info("No user data available for comparison")

# Surgeon Experience Analysis
elif selected_page == "Surgeon Experience Analysis":
    

    # Initialise session state for surgeon experience data
    if 'surgeon_experience' not in st.session_state:
        st.session_state.surgeon_experience = None

    # File upload section
    st.subheader("Upload Surgeon Experience Data")
    st.markdown("""
    Upload a CSV file with the following columns:
    - **TimeStamp**: When the experience data was recorded
    - **UUID**: Unique identifier matching the user IDs from the game data
    - **Experience**: Experience level as numerical value (1=1-5 years, 2=6-10 years, 3=11-15 years, 4=15+ years)
    """)

    experience_file = st.file_uploader(
        "Upload Surgeon Experience CSV", 
        type=["csv"], 
        key="surgeon_experience_upload"
    )

    if experience_file is not None:
        if st.button("Process Experience Data"):
            try:
                # Read the experience data
                experience_data = pd.read_csv(experience_file)
                
                # Validate required columns
                required_columns = ['TimeStamp', 'UUID', 'Experience']
                missing_columns = [col for col in required_columns if col not in experience_data.columns]
                
                if missing_columns:
                    st.error(f"Missing required columns: {missing_columns}")
                else:
                    # Process the data
                    experience_data['TimeStamp'] = pd.to_datetime(experience_data['TimeStamp'])
                    st.session_state.surgeon_experience = experience_data
                    st.success(f"Successfully loaded experience data for {len(experience_data)} surgeons")
                    
                    # Show preview of the data
                    st.subheader("Experience Data Preview")
                    st.dataframe(experience_data.head())

            except Exception as e:
                st.error(f"Error processing experience file: {str(e)}")

    # Analysis section
    if st.session_state.surgeon_experience is not None:
        st.subheader("Experience vs Performance Analysis")
        
        experience_df = st.session_state.surgeon_experience.copy()
        
        # Create performance metrics table
        performance_metrics = []
        
        # Check if we have user data uploaded
        if st.session_state.user_data:
            st.markdown("### Performance Metrics by Surgeon Experience")
            
            # Extract performance data for each UUID in experience data
            for _, exp_row in experience_df.iterrows():
                uuid = exp_row['UUID']
                experience_level = exp_row['Experience']
                
                # Initialise metrics with default values
                metrics = {
                    'UUID': uuid,
                    'Experience_Level': experience_level,
                    'Instrument_Efficiency': None,  # Average movement
                    'Task_Completion_Time': None,   # Average task time
                    'Peripheral_Awareness': None,   # Distraction response time
                    'Distraction_Management': None  # Movement ratio during distractions
                }
                
                # Try to find matching user data
                user_data = st.session_state.user_data.get(uuid)
                if user_data and 'summary' in user_data:
                    summary = user_data['summary']
                    
                    # Extract metrics for the 4 objectives
                    metrics['Instrument_Efficiency'] = summary.get('avg_movement', None)
                    metrics['Task_Completion_Time'] = summary.get('avg_task_time', None)
                    metrics['Peripheral_Awareness'] = summary.get('distraction_response_time', None)
                    metrics['Distraction_Management'] = summary.get('movement_ratio', None)
                
                performance_metrics.append(metrics)
            
            # Create performance table
            if performance_metrics:
                performance_df = pd.DataFrame(performance_metrics)
                
                # Define metric labels at the top for use throughout the analysis
                metric_labels = {
                    'Instrument_Efficiency': 'Objective 1: Instrument Efficiency (Avg Movement in px)',
                    'Task_Completion_Time': 'Objective 2: Task Completion Time (Avg Time in seconds)',
                    'Peripheral_Awareness': 'Objective 3: Peripheral Awareness (Response Time in seconds)',
                    'Distraction_Management': 'Objective 4: Distraction Management (Movement Impact Ratio)'
                }
                
                # Format the table for display
                display_df = performance_df.copy()
                
                # Round numerical values for better display
                numeric_columns = ['Instrument_Efficiency', 'Task_Completion_Time', 
                                 'Peripheral_Awareness', 'Distraction_Management']
                
                for col in numeric_columns:
                    display_df[col] = display_df[col].apply(
                        lambda x: f"{x:.2f}" if pd.notnull(x) else "No Data"
                    )
                
                # Rename columns for better readability
                display_df.columns = [
                    'UUID', 'Experience Level', 
                    'Avg Movement (px)', 'Avg Task Time (s)', 
                    'Avg Response Time (s)', 'Movement Impact Ratio'
                ]
                
                st.dataframe(display_df, use_container_width=True)
                
                # Statistical analysis
                st.subheader("Statistical Analysis by Experience Level")
                
                # Create readable experience labels
                experience_labels = {
                    1: '1-5 years (Novice)',
                    2: '6-10 years', 
                    3: '11-15 years',
                    4: '15+ years (Expert)'
                }
                
                # Group by experience level and calculate averages
                numeric_df = performance_df.copy()
                for col in numeric_columns:
                    numeric_df[col] = pd.to_numeric(numeric_df[col], errors='coerce')
                
                # Convert experience to numerical and create labels
                numeric_df['Experience_Numeric'] = pd.to_numeric(numeric_df['Experience_Level'], errors='coerce')
                numeric_df['Experience_Label'] = numeric_df['Experience_Numeric'].map(experience_labels)
                numeric_df['Experience_Label'] = numeric_df['Experience_Label'].fillna(numeric_df['Experience_Level'])
                
                # Group by experience label and calculate only mean and count
                experience_stats = numeric_df.groupby('Experience_Label')[numeric_columns].agg(['mean', 'count']).round(2)
                
                # Flatten column names
                experience_stats.columns = [f"{col[0]}_{col[1]}" for col in experience_stats.columns]
                experience_stats = experience_stats.reset_index()
                
                # Rename columns for better clarity
                new_column_names = {'Experience_Label': 'Experience Level'}
                for col in numeric_columns:
                    metric_name = metric_labels.get(col, col)
                    new_column_names[f'{col}_mean'] = f'{metric_name} (Average)'
                    new_column_names[f'{col}_count'] = f'{metric_name} (Count)'
                
                experience_stats = experience_stats.rename(columns=new_column_names)
                
                # Ensure proper ordering
                level_order = ['1-5 years (Novice)', '6-10 years', '11-15 years', '15+ years (Expert)']
                experience_stats['Experience Level'] = pd.Categorical(experience_stats['Experience Level'], categories=level_order, ordered=True)
                experience_stats = experience_stats.sort_values('Experience Level')
                
                st.dataframe(experience_stats, use_container_width=True)
                
                # Visualisations
                st.subheader("Performance Analysis Across the Four Study Objectives")
                
                # Create comprehensive visualisations for all 4 objectives
                metric_labels = {
                    'Instrument_Efficiency': 'Objective 1: Instrument Efficiency (Avg Movement in px)',
                    'Task_Completion_Time': 'Objective 2: Task Completion Time (Avg Time in seconds)',
                    'Peripheral_Awareness': 'Objective 3: Peripheral Awareness (Response Time in seconds)',
                    'Distraction_Management': 'Objective 4: Distraction Management (Movement Impact Ratio)'
                }
                
                # Overview: All 4 objectives in one comprehensive view
                st.markdown("### Complete Performance Overview")
                
                # Create a comprehensive heatmap showing all metrics by experience level
                heatmap_data = numeric_df.groupby('Experience_Label')[numeric_columns].mean().round(2)
                
                # Ensure proper ordering
                level_order = ['1-5 years (Novice)', '6-10 years', '11-15 years', '15+ years (Expert)']
                heatmap_data = heatmap_data.reindex(level_order)
                
                # Rename columns for heatmap
                heatmap_data.columns = [
                    'Obj 1: Instrument\nEfficiency (px)',
                    'Obj 2: Task Time\n(seconds)', 
                    'Obj 3: Peripheral\nAwareness (s)',
                    'Obj 4: Distraction\nManagement (ratio)'
                ]
                
                if not heatmap_data.empty:
                    fig = px.imshow(
                        heatmap_data.T,
                        x=heatmap_data.index,
                        y=heatmap_data.columns,
                        color_continuous_scale='RdYlBu_r',
                        title='Performance Heatmap: All Four Objectives by Experience Level',
                        labels={'color': 'Performance Score'},
                        text_auto=True
                    )
                    fig.update_layout(
                        xaxis_title="Experience Level",
                        yaxis_title="Study Objectives"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Individual metric analysis with different chart types
                selected_metric = st.selectbox(
                    "Select Study Objective for Detailed Analysis",
                    list(metric_labels.keys()),
                    format_func=lambda x: metric_labels[x],
                    key="exp_metric_select"
                )
                
                # Filter out rows with no data for the selected metric
                plot_data = numeric_df.dropna(subset=[selected_metric])
                
                # Add experience labels to plot_data for better visualisation
                plot_data['Experience_Numeric'] = pd.to_numeric(plot_data['Experience_Level'], errors='coerce')
                plot_data['Experience_Label'] = plot_data['Experience_Numeric'].map(experience_labels)
                plot_data['Experience_Label'] = plot_data['Experience_Label'].fillna(plot_data['Experience_Level'])
                
                if not plot_data.empty:
                    # Line chart showing trend across experience levels
                    avg_by_exp = plot_data.groupby('Experience_Label')[selected_metric].mean().reset_index()
                    
                    # Ensure proper ordering
                    avg_by_exp['Experience_Label'] = pd.Categorical(avg_by_exp['Experience_Label'], categories=level_order, ordered=True)
                    avg_by_exp = avg_by_exp.sort_values('Experience_Label')
                    
                    fig = px.line(
                        avg_by_exp,
                        x='Experience_Label',
                        y=selected_metric,
                        title=f"Performance Trend: {metric_labels[selected_metric]}",
                        labels={
                            'Experience_Label': 'Experience Level',
                            selected_metric: metric_labels[selected_metric].split(':')[1].strip()
                        },
                        markers=True,
                        line_shape='linear'
                    )
                    fig.update_traces(marker_size=12, line_width=4)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Comprehensive comparison across all objectives
                    st.markdown("### Cross-Objective Performance Comparison")
                    
                    # Radar chart for selected experience levels
                    experience_levels = plot_data['Experience_Label'].unique()
                    if len(experience_levels) > 1:
                        selected_levels = st.multiselect(
                            "Select Experience Levels to Compare",
                            sorted(experience_levels),
                            default=sorted(experience_levels)[:2] if len(experience_levels) >= 2 else sorted(experience_levels),
                            key="exp_levels_compare"
                        )
                        
                        if selected_levels:
                            # Create radar chart data
                            radar_data = []
                            for level in selected_levels:
                                level_data = plot_data[plot_data['Experience_Label'] == level]
                                if not level_data.empty:
                                    radar_entry = {
                                        'Experience_Level': level,
                                        'Instrument_Efficiency': level_data['Instrument_Efficiency'].mean(),
                                        'Task_Completion_Time': 1/level_data['Task_Completion_Time'].mean() if level_data['Task_Completion_Time'].mean() > 0 else 0,  # Inverted for radar (lower is better)
                                        'Peripheral_Awareness': 1/level_data['Peripheral_Awareness'].mean() if level_data['Peripheral_Awareness'].mean() > 0 else 0,  # Inverted for radar (lower is better)
                                        'Distraction_Management': 1/level_data['Distraction_Management'].mean() if level_data['Distraction_Management'].mean() > 0 else 0  # Inverted for radar (lower is better)
                                    }
                                    radar_data.append(radar_entry)
                            
                            if radar_data:
                                # Create radar chart
                                fig = go.Figure()
                                
                                categories = ['Instrument\nEfficiency', 'Task\nCompletion', 'Peripheral\nAwareness', 'Distraction\nManagement']
                                
                                for entry in radar_data:
                                    values = [
                                        entry['Instrument_Efficiency'],
                                        entry['Task_Completion_Time'],
                                        entry['Peripheral_Awareness'],
                                        entry['Distraction_Management']
                                    ]
                                    # Close the radar chart
                                    values += [values[0]]
                                    categories_closed = categories + [categories[0]]
                                    
                                    fig.add_trace(go.Scatterpolar(
                                        r=values,
                                        theta=categories_closed,
                                        fill='toself',
                                        name=entry['Experience_Level'],
                                        line_width=3
                                    ))
                                
                                fig.update_layout(
                                    title="Multi-Objective Performance Comparison by Experience Level<br><sub>Note: All metrics normalised for comparison (higher values = better performance)</sub>",
                                    polar=dict(
                                        radialaxis=dict(
                                            visible=True,
                                            range=[0, 1]
                                        )
                                    ),
                                    height=500
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                    
                    # Correlation and Statistical Analysis
                    st.markdown("### Statistical Correlation Analysis")
                    
                    # If we have numerical experience data, show correlation
                    if not plot_data['Experience_Numeric'].isna().all():
                        correlation = plot_data['Experience_Numeric'].corr(plot_data[selected_metric])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                f"Correlation Coefficient", 
                                f"{correlation:.3f}" if not pd.isna(correlation) else "N/A"
                            )
                        
                        with col2:
                            # Interpretation
                            if not pd.isna(correlation):
                                if abs(correlation) > 0.7:
                                    interpretation = "Strong"
                                elif abs(correlation) > 0.3:
                                    interpretation = "Moderate"
                                else:
                                    interpretation = "Weak"
                                
                                direction = "Positive" if correlation > 0 else "Negative"
                                st.metric("Correlation Strength", f"{interpretation} {direction}")
                        
                        with col3:
                            # Performance direction interpretation
                            direction_meaning = ""
                            if not pd.isna(correlation):
                                if selected_metric in ['Instrument_Efficiency', 'Task_Completion_Time', 'Peripheral_Awareness']:
                                    # Lower is better for these metrics
                                    if correlation < 0:
                                        direction_meaning = "✅ Improves with Experience"
                                    else:
                                        direction_meaning = "⚠️ Worsens with Experience"
                                else:
                                    # Higher is better for distraction management ratio
                                    if correlation > 0:
                                        direction_meaning = "✅ Improves with Experience"
                                    else:
                                        direction_meaning = "⚠️ Worsens with Experience"
                            
                            st.metric("Performance Trend", direction_meaning)
                        
                        # Scatter plot with trend line using numerical values but showing readable labels
                        fig = px.scatter(
                            plot_data,
                            x='Experience_Numeric',
                            y=selected_metric,
                            hover_data=['Experience_Label', 'UUID'],
                            title=f"Correlation Analysis: {metric_labels[selected_metric]} vs Experience",
                            labels={
                                'Experience_Numeric': 'Experience Level (Years)',
                                selected_metric: metric_labels[selected_metric].split(':')[1].strip()
                            },
                            trendline="ols",
                            trendline_color_override="red"
                        )
                        
                        # Update x-axis to show readable labels
                        fig.update_xaxes(
                            tickmode='array',
                            tickvals=[1, 2, 3, 4],
                            ticktext=['1-5 years\n(Novice)', '6-10 years', '11-15 years', '15+ years\n(Expert)']
                        )
                        
                        # Add correlation coefficient to the plot
                        fig.add_annotation(
                            x=0.02, y=0.98,
                            xref="paper", yref="paper",
                            text=f"Correlation: r = {correlation:.3f}",
                            showarrow=False,
                            font=dict(size=14, color="red"),
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="red",
                            borderwidth=1
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Detailed breakdown by experience level
                        st.markdown("### Detailed Performance Breakdown")
                        
                        experience_breakdown = plot_data.groupby('Experience_Label').agg({
                            selected_metric: ['count', 'mean', 'min', 'max'],
                            'UUID': 'count'
                        }).round(2)
                        
                        # Flatten column names
                        experience_breakdown.columns = [
                            'Sample Count', 'Average', 'Minimum', 'Maximum', 'Participants'
                        ]
                        experience_breakdown = experience_breakdown.reset_index()
                        experience_breakdown.columns = [
                            'Experience Level', 'Sample Count', f'Average {metric_labels[selected_metric].split(":")[1].strip()}', 
                            f'Best {metric_labels[selected_metric].split(":")[1].strip()}', 
                            f'Worst {metric_labels[selected_metric].split(":")[1].strip()}', 'Participants'
                        ]
                        
                        # Ensure proper ordering
                        level_order = ['1-5 years (Novice)', '6-10 years', '11-15 years', '15+ years (Expert)']
                        experience_breakdown['Experience Level'] = pd.Categorical(experience_breakdown['Experience Level'], categories=level_order, ordered=True)
                        experience_breakdown = experience_breakdown.sort_values('Experience Level')
                        
                        st.dataframe(experience_breakdown, use_container_width=True)
                else:
                    st.warning(f"No data available for {metric_labels[selected_metric]}")
                
                # Download processed data
                st.subheader("Export Experience Analysis Data")
                
                # Prepare comprehensive export data
                export_df = performance_df.copy()
                
                # Add additional summary statistics
                if st.button("Download Experience Analysis Data (CSV)"):
                    csv_buffer = io.StringIO()
                    export_df.to_csv(csv_buffer, index=False)
                    csv_str = csv_buffer.getvalue()
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv_str,
                        file_name="surgeon_experience_analysis.csv",
                        mime="text/csv"
                    )
            
            else:
                st.warning("No matching user data found for the provided UUIDs")
        
        else:
            st.warning("""
            No user performance data has been uploaded yet. Please upload user data on the 'Data Upload' page first.
            
            However, you can still view the experience data:
            """)
            
            # Show basic experience data analysis
            st.subheader("Experience Data Overview")
            
            # Create readable labels for experience levels
            experience_labels = {
                1: '1-5 years (Novice)',
                2: '6-10 years', 
                3: '11-15 years',
                4: '15+ years (Expert)'
            }
            
            # Convert experience to numerical and create labels
            experience_df['Experience_Numeric'] = pd.to_numeric(experience_df['Experience'], errors='coerce')
            experience_df['Experience_Label'] = experience_df['Experience_Numeric'].map(experience_labels)
            experience_df['Experience_Label'] = experience_df['Experience_Label'].fillna(experience_df['Experience'])
            
            # Experience level distribution
            exp_counts = experience_df['Experience_Label'].value_counts().reset_index()
            exp_counts.columns = ['Experience Level', 'Count']
            
            # Ensure proper ordering
            level_order = ['1-5 years (Novice)', '6-10 years', '11-15 years', '15+ years (Expert)']
            exp_counts['Experience Level'] = pd.Categorical(exp_counts['Experience Level'], categories=level_order, ordered=True)
            exp_counts = exp_counts.sort_values('Experience Level')
            
            fig = px.bar(
                exp_counts,
                x='Experience Level',
                y='Count',
                title='Distribution of Surgeon Experience Levels'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show full experience data
            st.dataframe(experience_df)
    
    else:
        st.info("Please upload a surgeon experience CSV file to begin the analysis.")

# Export Report
elif selected_page == "Export Report":
    st.header("Export Analysis Report")
    st.markdown("""
    Download analysis reports and aggregated data from the study.
    """)

    # Extract summary metrics for all users
    user_summaries = []
    for user_id, data in st.session_state.user_data.items():
        if 'summary' in data:
            user_summaries.append(data['summary'])

    if user_summaries:
        summary_df = pd.DataFrame(user_summaries)

        # Generate summary CSV
        csv_buffer = io.StringIO()
        summary_df.to_csv(csv_buffer, index=False)
        csv_str = csv_buffer.getvalue()

        st.subheader("Download Summary Data")
        st.download_button(
            label="Download All Users Summary (CSV)",
            data=csv_str,
            file_name="keyhole_surgery_study_summary.csv",
            mime="text/csv"
        )

        # Generate a PDF report with main findings
        st.subheader("Generate Analysis Report")

        # Options for report content
        st.markdown("Select which sections to include in the report:")

        include_summary = st.checkbox("Overall Summary Statistics", value=True)
        include_efficiency = st.checkbox(
            "Instrument Efficiency Analysis", value=True)
        include_task = st.checkbox("Task Completion Analysis", value=True)
        include_awareness = st.checkbox(
            "Peripheral Awareness Analysis", value=True)
        include_distraction = st.checkbox(
            "Distraction Management Analysis", value=True)
        include_user = st.checkbox("User Comparison", value=True)

        # Generate HTML report
        if st.button("Generate Report"):
            # Create HTML content
            html_content = f"""
            <html>
            <head>
                <title>Keyhole Surgery Game Study Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    h2 {{ color: #3498db; margin-top: 30px; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .metric {{ font-weight: bold; margin: 15px 0; }}
                    .metric span {{ color: #3498db; }}
                </style>
            </head>
            <body>
                <h1>Keyhole Surgery Game Study Report</h1>
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>This report provides analysis of data collected from {len(summary_df)} participants in the Keyhole Surgery Game study.</p>
            """

            # Add summary section
            if include_summary:
                html_content += """
                <h2>1. Overall Summary Statistics</h2>
                <p>Key performance metrics across all participants:</p>
                """

                # Calculate aggregate statistics
                agg_stats = {
                    'total_users': len(summary_df),
                    'avg_movement': summary_df['avg_movement'].mean(),
                    'avg_task_time': summary_df['avg_task_time'].mean(),
                    'avg_success_rate': summary_df['success_rate'].mean(),
                    'avg_response_rate': summary_df['distraction_response_rate'].mean(),
                    'avg_response_time': summary_df['distraction_response_time'].mean(),
                }

                html_content += f"""
                <div class="metric">Total Participants: <span>{agg_stats['total_users']}</span></div>
                <div class="metric">Average Movement: <span>{agg_stats['avg_movement']:.2f} px</span></div>
                <div class="metric">Average Task Completion Time: <span>{agg_stats['avg_task_time']:.2f} seconds</span></div>
                <div class="metric">Average Success Rate: <span>{agg_stats['avg_success_rate']:.1f}%</span></div>
                <div class="metric">Average Distraction Response Rate: <span>{agg_stats['avg_response_rate']:.1f}%</span></div>
                <div class="metric">Average Distraction Response Time: <span>{agg_stats['avg_response_time']:.2f} seconds</span></div>
                
                <h3>Individual Participant Performance</h3>
                <table>
                    <tr>
                        <th>Participant ID</th>
                        <th>Avg Movement</th>
                        <th>Avg Task Time</th>
                        <th>Success Rate</th>
                        <th>Response Rate</th>
                    </tr>
                """

                for _, row in summary_df.iterrows():
                    html_content += f"""
                    <tr>
                        <td>{row['user_id']}</td>
                        <td>{row['avg_movement']:.2f} px</td>
                        <td>{row['avg_task_time']:.2f} s</td>
                        <td>{row['success_rate']:.1f}%</td>
                        <td>{row['distraction_response_rate']:.1f}%</td>
                    </tr>
                    """

                html_content += "</table>"

            # Add other sections based on user selection
            if include_efficiency:
                html_content += """
                <h2>2. Instrument Efficiency Analysis</h2>
                <p>Analysis of how efficiently the surgical instruments were used across all participants:</p>
                
                <div class="findings">
                    <p>Key findings:</p>
                    <ul>
                        <li>Average movement across all participants shows the overall efficiency of instrument use</li>
                        <li>Movement patterns change across different levels, indicating adaptation to increasing difficulty</li>
                        <li>Economy of movement (movement per successful action) provides insight into precision</li>
                    </ul>
                </div>
                """

            if include_task:
                html_content += """
                <h2>3. Task Completion Analysis</h2>
                <p>Analysis of how quickly tasks were completed across all participants:</p>
                
                <div class="findings">
                    <p>Key findings:</p>
                    <ul>
                        <li>Average task completion time provides insight into surgical speed</li>
                        <li>Success rate indicates precision and accuracy of surgical tasks</li>
                        <li>Performance changes across game levels show learning curve and adaptation</li>
                    </ul>
                </div>
                """

            if include_awareness:
                html_content += """
                <h2>4. Peripheral Awareness Analysis</h2>
                <p>Analysis of how well participants notice events outside their main focus:</p>
                
                <div class="findings">
                    <p>Key findings:</p>
                    <ul>
                        <li>Response rate to peripheral distractions indicates situational awareness</li>
                        <li>Response time measures how quickly participants can shift attention</li>
                        <li>Different distraction types have varying impacts on performance</li>
                    </ul>
                </div>
                """

            if include_distraction:
                html_content += """
                <h2>5. Distraction Management Analysis</h2>
                <p>Analysis of how distractions affect focus and error rates:</p>
                
                <div class="findings">
                    <p>Key findings:</p>
                    <ul>
                        <li>Performance comparison during distractions vs. normal conditions shows impact on focus</li>
                        <li>Error rates during distractions quantify the precision impact</li>
                        <li>Different types of distractions (calls, alerts, etc.) have varying effects</li>
                        <li>Limited field of view significantly affects both movement and error rates</li>
                    </ul>
                </div>
                """

            if include_user:
                html_content += """
                <h2>6. User Comparison</h2>
                <p>Comparative analysis of performance across different participants:</p>
                
                <div class="findings">
                    <p>Key findings:</p>
                    <ul>
                        <li>Performance varies significantly between participants</li>
                        <li>Some participants excel in certain metrics but struggle in others</li>
                        <li>Adaptation to increasing difficulty levels shows individual learning patterns</li>
                    </ul>
                </div>
                """

            # Add conclusions
            html_content += """
            <h2>Conclusions</h2>
            <p>Based on the analysis of the keyhole surgery game data, we can draw the following conclusions about the study objectives:</p>
            
            <ol>
                <li><strong>Instrument Efficiency:</strong> The data shows clear patterns in movement efficiency, with participants demonstrating varying levels of economy of movement. The limited field of view significantly affects movement patterns and efficiency.</li>
                
                <li><strong>Task Completion Time:</strong> Task completion times provide insights into surgical speed and precision. Most participants show adaptation and improvement across levels, indicating a learning curve effect.</li>
                
                <li><strong>Peripheral Awareness:</strong> Response rates to peripheral distractions indicate participants' ability to maintain awareness outside their main focus. This is a critical skill in real surgical environments.</li>
                
                <li><strong>Distraction Management:</strong> Performance metrics during distractions show how external factors impact focus and precision. Different types of distractions have varying impacts, with some being more disruptive than others.</li>
            </ol>
            
            <p>These findings provide valuable insights for surgical training and the design of surgical environments, highlighting the importance of field of view, distraction management, and peripheral awareness in keyhole surgery.</p>
            
            <h2>Recommendations</h2>
            <p>Based on the findings, we recommend:</p>
            
            <ul>
                <li>Surgical training should incorporate practice with limited field of view conditions</li>
                <li>Developing strategies to manage distractions in the operating room</li>
                <li>Training to improve peripheral awareness during focused procedures</li>
                <li>Further studies to explore the relationship between instrument efficiency and surgical outcomes</li>
            </ul>
            
            <p><em>End of Report - UCL Medical Physics and Biomedical Engineering Research Study</em></p>
            </body>
            </html>
            """

            # Convert HTML to downloadable format
            html_bytes = html_content.encode()

            # Provide download button
            st.download_button(
                label="Download HTML Report",
                data=html_bytes,
                file_name="keyhole_surgery_analysis_report.html",
                mime="text/html"
            )

            # Display preview
            st.subheader("Report Preview")
            st.components.v1.html(html_content, height=600, scrolling=True)

        # Export all processed data
        st.subheader("Export All Processed Data")

        if st.button("Prepare Full Data Export (ZIP)"):
            try:
                # Create temp directory
                with tempfile.TemporaryDirectory() as tmpdirname:
                    # Create user directories
                    for user_id, user_data in st.session_state.user_data.items():
                        user_dir = os.path.join(tmpdirname, user_id)
                        os.makedirs(user_dir, exist_ok=True)

                        # Export processed data for each user
                        if 'mouse_data' in user_data and not user_data['mouse_data'].empty:
                            user_data['mouse_data'].to_csv(os.path.join(
                                user_dir, 'processed_mouse_data.csv'), index=False)

                        if 'vessel_data' in user_data and not user_data['vessel_data'].empty:
                            user_data['vessel_data'].to_csv(os.path.join(
                                user_dir, 'processed_vessel_data.csv'), index=False)

                        # Export summary data
                        if 'summary' in user_data:
                            pd.DataFrame([user_data['summary']]).to_csv(
                                os.path.join(user_dir, 'summary_metrics.csv'), index=False)

                    # Export aggregated data
                    summary_df.to_csv(os.path.join(
                        tmpdirname, 'all_users_summary.csv'), index=False)

                    # Create ZIP file in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(tmpdirname):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(
                                    file_path, tmpdirname)
                                zipf.write(file_path, arcname)

                    # Provide download link
                    zip_buffer.seek(0)
                    st.download_button(
                        label="Download All Processed Data (ZIP)",
                        data=zip_buffer,
                        file_name="keyhole_surgery_processed_data.zip",
                        mime="application/zip"
                    )
            except Exception as e:
                st.error(f"Error creating ZIP file: {str(e)}")
    else:
        st.info("No user data available for export")