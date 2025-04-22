### Research Question
A Serious Game to Study the Effect of Limited Field of View in Keyhole Surgery.
vessel-game-project.vercel.app

## Project Overview
This project investigates the effects of limited field of view in keyhole surgery through a serious game approach. The game simulates surgical scenarios where players must navigate and perform tasks with varying levels of visual field constraints.

### Research Objectives
1. **Instrument Efficiency**: Measure how efficiently instruments are used based on total movement
2. **Task Completion Time**: Analyse how quickly tasks are completed
3. **Peripheral Awareness**: Assess how well surgeons notice important events outside their main focus
4. **Distraction Impact**: Study how distractions affect focus and errors

## Data Collection and Analysis Pipeline

### 1. Gameplay Data Collection
- Users play the Vessel Game
- Game data is automatically collected and stored in Google Sheets
- Data Spreadsheet: [Vessel Game Data](https://docs.google.com/spreadsheets/d/11iMJu3nDiwrV7bMak1cxVl-_bZSjJJn0kwjxF1cHwSM/edit?usp=sharing)

### 2. Data Processing
1. Run AppScript to export all data from Google Sheets to Google Drive
2. Download the generated ZIP folder containing all user data

## Technical Requirements

### Prerequisites
- Python 3.8+
- Node.js (for local development)
- Visual Studio Code (recommended)
- Web browser with JavaScript enabled
- Git (for version control)

### Installation

#### 1. Game Setup
1. Install Visual Studio Code
2. Install the "Live Server" extension in VS Code:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X or Cmd+Shift+X)
   - Search for "Live Server"
   - Install the extension by Ritwick Dey

#### 2. Python Environment Setup
1. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. Install Python dependencies:
   ```bash
   cd streamlit
   pip install -r requirements.txt
   ```

#### 3. Running the Game
1. Open the project in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"
4. The game will open in your default web browser at `http://localhost:5500`

### 4. Data Analysis
Two analysis tools are provided:

#### Individual Analysis (user.py)
Locally:
- Run `streamlit run streamlit/user.py`
OR 
[https://vessel-game-user.streamlit.app/]
- Features:
  - Performance metrics
  - Movement patterns
  - Distraction analysis
  - Level progression

#### Admin Analysis (admin.py)
Locally:
- Run `streamlit run streamlit/admin.py`
OR
[https://vessel-game-owner.streamlit.app/]
- Upload the ZIP folder containing all user data
- Features:
  - Aggregate statistics
  - Comparative analysis
  - Research insights
  - Data visualisation

## Data Structure
The game collects the following data types:
- Mouse tracking data
- Vessel creation and cutting events
- Distraction events
- Performance metrics
- Level progression



