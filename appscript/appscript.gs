// The main spreadsheet ID where all data will be stored
const MASTER_SPREADSHEET_ID = "11iMJu3nDiwrV7bMak1cxVl-_bZSjJJn0kwjxF1cHwSM";

/**
 * Handles POST requests from the web application
 */
function doPost(e) {
  try {
    // Parse the incoming data
    const params = e.parameter || {};
    const formType = params.formType || "gameData"; // Default to gameData if not specified
    
    // Log the incoming request for debugging
    console.log("Request received: " + formType);
    console.log("Parameters: " + JSON.stringify(params));
    
    // Route to the appropriate handler based on formType
    if (formType === "feedback") {
      return handleFeedbackForm(params);
    } else {
      return handleGameData(params);
    }
      
  } catch (error) {
    console.error("Error in doPost: " + error.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "error", 
        message: "Server error: " + error.toString() 
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handles game data submissions (mouse tracking and vessel creation)
 */
function handleGameData(params) {
  try {
    const uuid = params.uuid || "";
    const dataType = params.dataType || "";
    
    // Validate required parameters
    if (!uuid) {
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "error", 
          message: "Missing UUID parameter" 
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    if (!dataType) {
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "error", 
          message: "Missing dataType parameter" 
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    if (!params.data) {
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "error", 
          message: "Missing data parameter" 
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Safely parse the data
    let data;
    try {
      data = JSON.parse(params.data);
    } catch (error) {
      console.error("Error parsing data: " + error.toString());
      console.error("Raw data received: " + params.data);
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "error", 
          message: "Invalid JSON data: " + error.toString() 
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Ensure sheets exist
    const sheet = ensureSheetExists(uuid, dataType);
    
    // Save the data
    const result = saveGameData(sheet, dataType, data);
    
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "success", 
        message: "Data saved successfully", 
        rowsAdded: result.rowsAdded
      }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    console.error("Error in handleGameData: " + error.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "error", 
        message: "Error processing game data: " + error.toString() 
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handles feedback form submissions
 */
function handleFeedbackForm(params) {
  try {
    const uuid = params.uuid || "";
    
    // Validate UUID
    if (!uuid) {
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "error", 
          message: "Missing UUID parameter" 
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Ensure the feedback sheet exists
    const userSheet = ensureFeedbackSheetExists(uuid);
    const masterSheet = ensureMasterFeedbackSheetExists();
    
    // Save the feedback data
    const result = saveFeedbackData(uuid, params, userSheet, masterSheet);
    
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "success", 
        message: "Feedback submitted successfully", 
        rowAdded: result.rowAdded
      }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    console.error("Error in handleFeedbackForm: " + error.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "error", 
        message: "Error processing feedback: " + error.toString() 
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Ensures that the sheet with the given UUID and data type exists
 */
function ensureSheetExists(uuid, dataType) {
  try {
    const ss = SpreadsheetApp.openById(MASTER_SPREADSHEET_ID);
    const sheetName = `${uuid}-${dataType}`;
    
    // Check if the sheet already exists
    let sheet = ss.getSheetByName(sheetName);
    
    // If not, create it with appropriate headers
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      
      // Set up headers based on data type
      if (dataType === "mouse-tracking") {
        sheet.appendRow([
          'TIMESTAMP', 'X_POSITION', 'Y_POSITION', 'IS_CUTTING',
          'SCORE', 'TIME_LEFT', 'LEVEL', 'FIELD_OF_VIEW',
          'DISTRACTION_ID', 'DISTRACTION_TYPE', 'DISTRACTION_ACTION'
        ]);
      } else if (dataType === "vessel-creation") {
        sheet.appendRow([
          'TIMESTAMP', 'VESSEL_ID', 'IS_CORRECT', 'START_X', 'START_Y',
          'END_X', 'END_Y', 'CONTROL_POINT1_X', 'CONTROL_POINT1_Y',
          'CONTROL_POINT2_X', 'CONTROL_POINT2_Y', 'PATH_POINTS', 'EVENT',
          'IS_CUT', 'LEVEL', 'IS_INTERTWINED'
        ]);
      }
      
      // Freeze the header row and format
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, sheet.getLastColumn()).setFontWeight("bold");
      
      console.log(`Created new sheet: ${sheetName}`);
    }
    
    return sheet;
  } catch (error) {
    console.error(`Error in ensureSheetExists: ${error.toString()}`);
    throw new Error(`Failed to create/access sheet: ${error.toString()}`);
  }
}

/**
 * Ensures that the feedback sheet for a user exists
 */
function ensureFeedbackSheetExists(uuid) {
  try {
    const ss = SpreadsheetApp.openById(MASTER_SPREADSHEET_ID);
    const sheetName = `${uuid}-feedback`;
    
    // Check if the sheet already exists
    let sheet = ss.getSheetByName(sheetName);
    
    // If not, create it with appropriate headers
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      
      // Set up headers for feedback form
      sheet.appendRow([
        'TIMESTAMP', 'PLAYS_GAMES', 'LAPAROSCOPIC_KNOWLEDGE', 
        'FIELD_OF_VIEW_UNDERSTANDING', 'ENHANCED_UNDERSTANDING', 'CLINICALLY_RELEVANT',
        'DIFFICULTY_REASONABLE', 'GAME_ENGAGING', 'VISUALLY_PLEASING', 'OTHER_COMMENTS',
        // SUS questions
        'SUS1', 'SUS2', 'SUS3', 'SUS4', 'SUS5', 'SUS6', 'SUS7', 'SUS8', 'SUS9', 'SUS10', 'SUS_SCORE',
        // TLX questions
        'TLX1', 'TLX2', 'TLX3', 'TLX4', 'TLX5', 'TLX6', 'TLX_SCORE'
      ]);
      
      // Freeze the header row and format
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, sheet.getLastColumn()).setFontWeight("bold");
      
      console.log(`Created new feedback sheet: ${sheetName}`);
    }
    
    return sheet;
  } catch (error) {
    console.error(`Error in ensureFeedbackSheetExists: ${error.toString()}`);
    throw new Error(`Failed to create/access feedback sheet: ${error.toString()}`);
  }
}

/**
 * Ensures that a master feedback sheet exists that compiles all feedback
 */
function ensureMasterFeedbackSheetExists() {
  try {
    const ss = SpreadsheetApp.openById(MASTER_SPREADSHEET_ID);
    const sheetName = "Master-Feedback";
    
    // Check if the sheet already exists
    let sheet = ss.getSheetByName(sheetName);
    
    // If not, create it with appropriate headers
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      
      // Set up headers for feedback form (same as individual sheets plus UUID)
      sheet.appendRow([
        'UUID', 'TIMESTAMP', 'PLAYS_GAMES', 'LAPAROSCOPIC_KNOWLEDGE', 
        'FIELD_OF_VIEW_UNDERSTANDING', 'ENHANCED_UNDERSTANDING', 'CLINICALLY_RELEVANT',
        'DIFFICULTY_REASONABLE', 'GAME_ENGAGING', 'VISUALLY_PLEASING', 'OTHER_COMMENTS',
        // SUS questions
        'SUS1', 'SUS2', 'SUS3', 'SUS4', 'SUS5', 'SUS6', 'SUS7', 'SUS8', 'SUS9', 'SUS10', 'SUS_SCORE',
        // TLX questions
        'TLX1', 'TLX2', 'TLX3', 'TLX4', 'TLX5', 'TLX6', 'TLX_SCORE'
      ]);
      
      // Freeze the header row and format
      sheet.setFrozenRows(1);
      sheet.getRange(1, 1, 1, sheet.getLastColumn()).setFontWeight("bold");
      
      console.log("Created master feedback sheet");
    }
    
    return sheet;
  } catch (error) {
    console.error(`Error in ensureMasterFeedbackSheetExists: ${error.toString()}`);
    throw new Error(`Failed to create/access master feedback sheet: ${error.toString()}`);
  }
}

/**
 * Safely converts any value to a string
 */
function safeToString(value) {
  if (value === undefined || value === null) {
    return "";
  }
  
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (e) {
      console.error("Error stringifying object: " + e.toString());
      return "[Object]";
    }
  }
  
  return String(value);
}

/**
 * Saves game data to the appropriate sheet
 */
function saveGameData(sheet, dataType, data) {
  try {
    if (!sheet) {
      throw new Error("Sheet is not defined");
    }
    
    // Convert data to rows based on the data type
    let rows = [];
    
    if (Array.isArray(data)) {
      console.log(`Processing array of ${data.length} entries for ${dataType}`);
      
      // If we're given an array of data entries
      if (dataType === "mouse-tracking") {
        rows = data.map(entry => [
          safeToString(entry.timestamp || new Date().toISOString()),
          safeToString(entry.x),
          safeToString(entry.y),
          safeToString(entry.isCutting),
          safeToString(entry.score),
          safeToString(entry.timeLeft),
          safeToString(entry.level),
          safeToString(entry.fieldOfView),
          safeToString(entry.distractionId),
          safeToString(entry.distractionType),
          safeToString(entry.distractionAction)
        ]);
      } else if (dataType === "vessel-creation") {
        rows = data.map(entry => {
          // Handle pathPoints specially
          let pathPointsString = entry.pathPoints;
          if (typeof pathPointsString !== 'string') {
            try {
              pathPointsString = JSON.stringify(pathPointsString);
            } catch (e) {
              console.error("Error serializing path points: " + e.toString());
              pathPointsString = "[Error serializing path points]";
            }
          }
          
          return [
            safeToString(entry.timestamp || new Date().toISOString()),
            safeToString(entry.vesselId),
            safeToString(entry.isCorrect),
            safeToString(entry.startX),
            safeToString(entry.startY),
            safeToString(entry.endX),
            safeToString(entry.endY),
            safeToString(entry.cp1x),
            safeToString(entry.cp1y),
            safeToString(entry.cp2x),
            safeToString(entry.cp2y),
            pathPointsString,
            safeToString(entry.event),
            safeToString(entry.isCut),
            safeToString(entry.level),
            safeToString(entry.intertwined)
          ];
        });
      }
    } else {
      console.log(`Processing single entry for ${dataType}`);
      
      // If we're given a single data entry
      if (dataType === "mouse-tracking") {
        rows = [[
          safeToString(data.timestamp || new Date().toISOString()),
          safeToString(data.x),
          safeToString(data.y),
          safeToString(data.isCutting),
          safeToString(data.score),
          safeToString(data.timeLeft),
          safeToString(data.level),
          safeToString(data.fieldOfView),
          safeToString(data.distractionId),
          safeToString(data.distractionType),
          safeToString(data.distractionAction)
        ]];
      } else if (dataType === "vessel-creation") {
        // Handle pathPoints specially
        let pathPointsString = data.pathPoints;
        if (typeof pathPointsString !== 'string') {
          try {
            pathPointsString = JSON.stringify(pathPointsString);
          } catch (e) {
            console.error("Error serializing path points: " + e.toString());
            pathPointsString = "[Error serializing path points]";
          }
        }
        
        rows = [[
          safeToString(data.timestamp || new Date().toISOString()),
          safeToString(data.vesselId),
          safeToString(data.isCorrect),
          safeToString(data.startX),
          safeToString(data.startY),
          safeToString(data.endX),
          safeToString(data.endY),
          safeToString(data.cp1x),
          safeToString(data.cp1y),
          safeToString(data.cp2x),
          safeToString(data.cp2y),
          pathPointsString,
          safeToString(data.event),
          safeToString(data.isCut),
          safeToString(data.level),
          safeToString(data.intertwined)
        ]];
      }
    }
    
    // Append the rows to the sheet if we have data
    if (rows.length > 0) {
      console.log(`Appending ${rows.length} rows of data`);
      const lastRow = sheet.getLastRow();
      sheet.getRange(lastRow + 1, 1, rows.length, rows[0].length).setValues(rows);
      return { rowsAdded: rows.length };
    } else {
      console.log("No rows to append");
      return { rowsAdded: 0 };
    }
  } catch (error) {
    console.error(`Error in saveGameData: ${error.toString()}`);
    console.error(`Data type: ${dataType}, Is array: ${Array.isArray(data)}`);
    if (Array.isArray(data) && data.length > 0) {
      console.error(`First entry sample: ${JSON.stringify(data[0]).substring(0, 100)}...`);
    } else if (!Array.isArray(data)) {
      console.error(`Data sample: ${JSON.stringify(data).substring(0, 100)}...`);
    }
    throw new Error(`Failed to save game data: ${error.toString()}`);
  }
}

/**
 * Safely parses an integer with default value
 */
function safeParseInt(value, defaultValue = 0) {
  try {
    const parsed = parseInt(value);
    return isNaN(parsed) ? defaultValue : parsed;
  } catch (e) {
    return defaultValue;
  }
}

/**
 * Saves feedback data to the appropriate sheets
 */
function saveFeedbackData(uuid, formData, userSheet, masterSheet) {
  try {
    const timestamp = new Date().toISOString();
    
    // Safely get all form values with defaults
    const playGames = safeToString(formData.playGames);
    const laparoscopicKnowledge = safeToString(formData.laparoscopicKnowledge);
    const fieldOfViewUnderstanding = safeToString(formData.fieldOfViewUnderstanding);
    const enhancedUnderstanding = safeToString(formData.enhancedUnderstanding);
    const clinicallyRelevant = safeToString(formData.clinicallyRelevant);
    const difficultyReasonable = safeToString(formData.difficultyReasonable);
    const gameEngaging = safeToString(formData.gameEngaging);
    const visuallyPleasing = safeToString(formData.visuallyPleasing);
    const otherComments = safeToString(formData.otherComments);
    
    // SUS values with defensive parsing
    const sus1 = safeParseInt(formData.sus1, 3);
    const sus2 = safeParseInt(formData.sus2, 3);
    const sus3 = safeParseInt(formData.sus3, 3);
    const sus4 = safeParseInt(formData.sus4, 3);
    const sus5 = safeParseInt(formData.sus5, 3);
    const sus6 = safeParseInt(formData.sus6, 3);
    const sus7 = safeParseInt(formData.sus7, 3);
    const sus8 = safeParseInt(formData.sus8, 3);
    const sus9 = safeParseInt(formData.sus9, 3);
    const sus10 = safeParseInt(formData.sus10, 3);
    
    // TLX values with defensive parsing
    const tlx1 = safeParseInt(formData.tlx1, 3);
    const tlx2 = safeParseInt(formData.tlx2, 3);
    const tlx3 = safeParseInt(formData.tlx3, 3);
    const tlx4 = safeParseInt(formData.tlx4, 3);
    const tlx5 = safeParseInt(formData.tlx5, 3);
    const tlx6 = safeParseInt(formData.tlx6, 3);
    
    // Calculate SUS score (ranges from 0-100)
    // For odd-numbered questions, score is the response minus 1
    // For even-numbered questions, score is 5 minus the response
    const sus1Score = sus1 - 1;
    const sus2Score = 5 - sus2;
    const sus3Score = sus3 - 1;
    const sus4Score = 5 - sus4;
    const sus5Score = sus5 - 1;
    const sus6Score = 5 - sus6;
    const sus7Score = sus7 - 1;
    const sus8Score = 5 - sus8;
    const sus9Score = sus9 - 1;
    const sus10Score = 5 - sus10;
    const susScore = (sus1Score + sus2Score + sus3Score + sus4Score + sus5Score + 
                      sus6Score + sus7Score + sus8Score + sus9Score + sus10Score) * 2.5;
    
    // Calculate TLX score (simple average of the 6 responses)
    const tlxScore = (tlx1 + tlx2 + tlx3 + tlx4 + tlx5 + tlx6) / 6;
    
    // Create the row data
    const rowData = [
      timestamp,
      playGames,
      laparoscopicKnowledge,
      fieldOfViewUnderstanding,
      enhancedUnderstanding,
      clinicallyRelevant,
      difficultyReasonable,
      gameEngaging,
      visuallyPleasing,
      otherComments,
      // SUS questions
      safeToString(sus1),
      safeToString(sus2),
      safeToString(sus3),
      safeToString(sus4),
      safeToString(sus5),
      safeToString(sus6),
      safeToString(sus7),
      safeToString(sus8),
      safeToString(sus9),
      safeToString(sus10),
      safeToString(susScore),
      // TLX questions
      safeToString(tlx1),
      safeToString(tlx2),
      safeToString(tlx3),
      safeToString(tlx4),
      safeToString(tlx5),
      safeToString(tlx6),
      safeToString(tlxScore)
    ];
    
    // Save to user-specific sheet
    userSheet.appendRow(rowData);
    
    // Save to master sheet (with UUID added at the beginning)
    masterSheet.appendRow([uuid].concat(rowData));
    
    console.log(`Feedback saved for user ${uuid}`);
    return { rowAdded: true };
  } catch (error) {
    console.error(`Error in saveFeedbackData: ${error.toString()}`);
    throw new Error(`Failed to save feedback data: ${error.toString()}`);
  }
}

/**
 * Simple GET endpoint for testing
 */
function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ 
      status: "success", 
      message: "Vessel Game Data Collection API is running",
      version: "1.1.0"
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Handles GET requests to retrieve user data
 */
function doGet(e) {
  try {
    // Parse the incoming parameters
    const params = e.parameter || {};
    const uuid = params.uuid || "";
    
    // If no UUID is provided, return the generic status message
    if (!uuid) {
      return ContentService
        .createTextOutput(JSON.stringify({ 
          status: "success", 
          message: "Vessel Game Data Collection API is running",
          version: "1.2.0"
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Get data from the sheets
    const result = getUserData(uuid);
    
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "success", 
        uuid: uuid,
        data: result
      }))
      .setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    console.error("Error in doGet: " + error.toString());
    return ContentService
      .createTextOutput(JSON.stringify({ 
        status: "error", 
        message: "Server error: " + error.toString() 
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Retrieves all data for a specific UUID
 */
function getUserData(uuid) {
  try {
    const ss = SpreadsheetApp.openById(MASTER_SPREADSHEET_ID);
    const result = {};
    
    // Check for mouse-tracking sheet
    const mouseTrackingSheetName = `${uuid}-mouse-tracking`;
    let mouseTrackingSheet = ss.getSheetByName(mouseTrackingSheetName);
    
    if (mouseTrackingSheet) {
      const mouseTrackingData = getSheetData(mouseTrackingSheet);
      result["mouse-tracking"] = mouseTrackingData;
    } else {
      result["mouse-tracking"] = [];
      console.log(`Sheet ${mouseTrackingSheetName} not found`);
    }
    
    // Check for vessel-creation sheet
    const vesselCreationSheetName = `${uuid}-vessel-creation`;
    let vesselCreationSheet = ss.getSheetByName(vesselCreationSheetName);
    
    if (vesselCreationSheet) {
      const vesselCreationData = getSheetData(vesselCreationSheet);
      result["vessel-creation"] = vesselCreationData;
    } else {
      result["vessel-creation"] = [];
      console.log(`Sheet ${vesselCreationSheetName} not found`);
    }
    
    return result;
  } catch (error) {
    console.error(`Error in getUserData: ${error.toString()}`);
    throw new Error(`Failed to retrieve user data: ${error.toString()}`);
  }
}

/**
 * Retrieves all data from a sheet as an array of objects
 */
function getSheetData(sheet) {
  try {
    const data = [];
    const values = sheet.getDataRange().getValues();
    
    if (values.length <= 1) {
      // Only header row exists, no data
      return data;
    }
    
    const headers = values[0];
    
    // Process each row, skipping the header
    for (let i = 1; i < values.length; i++) {
      const row = values[i];
      const rowData = {};
      
      // Map column values to headers
      for (let j = 0; j < headers.length; j++) {
        // Try to parse JSON for pathPoints or other stringified objects
        if (typeof row[j] === 'string' && 
            (headers[j] === 'PATH_POINTS' || row[j].startsWith('['))) {
          try {
            rowData[headers[j]] = JSON.parse(row[j]);
          } catch (e) {
            // If parsing fails, keep the original string
            rowData[headers[j]] = row[j];
          }
        } else {
          rowData[headers[j]] = row[j];
        }
      }
      
      data.push(rowData);
    }
    
    return data;
  } catch (error) {
    console.error(`Error in getSheetData: ${error.toString()}`);
    throw new Error(`Failed to retrieve sheet data: ${error.toString()}`);
  }
}