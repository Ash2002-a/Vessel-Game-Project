#### Vessel Game
[Play the game here](https://vessel-game-project.vercel.app)

### Research Question
A Serious Game to Study the Effect of Limited Field of View in Keyhole Surgery.

## Project Overview
This project investigates the effects of limited field of view in keyhole surgery through a serious game approach. The game simulates surgical scenarios where players must navigate and perform tasks with varying levels of visual field constraints.

### 🎯 Research Objectives

1. **Instrument Efficiency**: Measure how efficiently instruments are used based on total movement
2. **Task Completion Time**: Analyse how quickly tasks are completed
3. **Peripheral Awareness**: Assess how well surgeons notice important events outside their main focus
4. **Distraction Impact**: Study how distractions affect focus and errors

## 📊 Data Collection Pipeline

### 1. Gameplay Data Collection
- Real-time data collection during gameplay
- Automated storage in Google Sheets
- [Access Data Spreadsheet](https://docs.google.com/spreadsheets/d/11iMJu3nDiwrV7bMak1cxVl-_bZSjJJn0kwjxF1cHwSM/edit?usp=sharing)

### 2. Data Processing Workflow
1. Execute AppScript to export data from Google Sheets
2. Download generated ZIP folder containing user data
3. Process and analyse data using provided tools

## 🛠️ Technical Setup

### Prerequisites
- Python 3.8+
- Visual Studio Code
- Modern web browser with JavaScript enabled
- Git

### 🚀 Installation Guide

#### 1. Development Environment Setup
1. Install Visual Studio Code
2. Install required VS Code extensions:
   - Live Server (by Ritwick Dey)
   - Python

#### 2. Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
cd streamlit
pip install -r requirements.txt
```

#### 3. Running the Game
1. Open project in VS Code
2. Right-click `index.html`
3. Select "Open with Live Server"
4. Access game at `http://localhost:5500`

## 📈 Analysis Tools

### Individual Analysis
- **Local**: `streamlit run streamlit/user.py`
- **Web**: [Vessel Game User Analysis](https://vessel-game-user.streamlit.app/)
- Features:
  - Performance metrics dashboard
  - Movement pattern visualisation
  - Distraction impact analysis
  - Level progression tracking

### Admin Analysis
- **Local**: `streamlit run streamlit/admin.py`
- **Web**: [Vessel Game Admin Dashboard](https://vessel-game-owner.streamlit.app/)
- Features:
  - Aggregate statistics
  - Comparative analysis
  - Research insights
  - Advanced data visualisation

## 📋 Data Structure

The game collects comprehensive data including:
- Mouse tracking and movement patterns
- Vessel creation and cutting events
- Distraction event timing and impact
- Performance metrics
- Level progression and completion rates




