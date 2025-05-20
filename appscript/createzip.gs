/**
 * This function exports data from the Google Sheets file to a folder structure
 * organised by user ID, with each user having mouse_tracking.csv and vessel_creation.csv files.
 * Added: Automatically checks for and adds missing column headers if needed.
 */
function exportDataForAnalyser() {
  // Open the active spreadsheet
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  
  // Replace with your own folder ID where you want to save the exported files
  var folderId = '1CI2ViKdxBBOn2JHL5QMhzbPghMAqYq3c';  
  var baseFolder = DriveApp.getFolderById(folderId);
  
  // Create a main export folder with timestamp
  var exportFolder = baseFolder.createFolder("KeyholeSurgeryData_" + new Date().toISOString().replace(/[:.]/g, '-'));
  
  // Dictionary to store user data by complete UUID
  var userSheets = {};
  var userPattern = /^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;
  
  // Define expected column headers for each sheet type
  var expectedHeaders = {
    'mouseTracking': ['TIMESTAMP', 'X_POSITION', 'Y_POSITION', 'IS_CUTTING', 'SCORE', 'TIME_LEFT', 'LEVEL', 'FIELD_OF_VIEW', 'DISTRACTION_ID', 'DISTRACTION_TYPE', 'DISTRACTION_ACTION'],
    'vesselCreation': ['TIMESTAMP', 'VESSEL_ID', 'IS_CORRECT', 'START_X', 'START_Y', 'END_X', 'END_Y', 'CONTROL_POINT1_X', 'CONTROL_POINT1_Y', 'CONTROL_POINT2_X', 'CONTROL_POINT2_Y', 'PATH_POINTS', 'EVENT', 'IS_CUT', 'LEVEL', 'IS_INTERTWINED']
  };
  
  // First pass: Identify all valid sheets and their types
  sheets.forEach(function(sheet) {
    var sheetName = sheet.getName();
    
    // Skip Master sheets
    if (sheetName.startsWith("Master-")) {
      return;
    }
    
    // Extract UUID using regex for standard UUID format (handles hyphens properly)
    var match = sheetName.match(userPattern);
    if (match) {
      var uuid = match[1]; // Complete UUID
      
      // Determine if this is mouse-tracking or vessel-creation
      if (sheetName.indexOf('mouse-tracking') !== -1) {
        if (!userSheets[uuid]) userSheets[uuid] = {};
        userSheets[uuid].mouseTracking = sheet;
        userSheets[uuid].mouseTrackingType = 'mouseTracking';
      } else if (sheetName.indexOf('vessel-creation') !== -1) {
        if (!userSheets[uuid]) userSheets[uuid] = {};
        userSheets[uuid].vesselCreation = sheet;
        userSheets[uuid].vesselCreationType = 'vesselCreation';
      }
    }
  });
  
  // Count of processed users and list of users missing data
  var processedUsers = 0;
  var incompleteUsers = [];
  var sheetsWithAddedHeaders = [];
  
  // Create the folder structure and export CSVs
  for (var uuid in userSheets) {
    // Create user folder
    var userFolder = exportFolder.createFolder(uuid);
    var isComplete = true;
    
    // Export mouse tracking data if available
    if (userSheets[uuid].mouseTracking) {
      var mouseTrackingCsv = convertSheetToCsv(userSheets[uuid].mouseTracking, expectedHeaders[userSheets[uuid].mouseTrackingType]);
      if (mouseTrackingCsv.headersAdded) {
        sheetsWithAddedHeaders.push(userSheets[uuid].mouseTracking.getName());
      }
      userFolder.createFile("mouse_tracking.csv", mouseTrackingCsv.csv, MimeType.PLAIN_TEXT);
      Logger.log('Created mouse_tracking.csv for user ' + uuid);
    } else {
      isComplete = false;
      Logger.log('Missing mouse tracking data for user ' + uuid);
    }
    
    // Export vessel creation data if available
    if (userSheets[uuid].vesselCreation) {
      var vesselCreationCsv = convertSheetToCsv(userSheets[uuid].vesselCreation, expectedHeaders[userSheets[uuid].vesselCreationType]);
      if (vesselCreationCsv.headersAdded) {
        sheetsWithAddedHeaders.push(userSheets[uuid].vesselCreation.getName());
      }
      userFolder.createFile("vessel_creation.csv", vesselCreationCsv.csv, MimeType.PLAIN_TEXT);
      Logger.log('Created vessel_creation.csv for user ' + uuid);
    } else {
      isComplete = false;
      Logger.log('Missing vessel creation data for user ' + uuid);
    }
    
    processedUsers++;
    
    if (!isComplete) {
      incompleteUsers.push(uuid);
    }
  }
  
  // Create a summary file
  var summary = "Keyhole Surgery Game Data Export\n";
  summary += "Exported on: " + new Date().toISOString() + "\n\n";
  summary += "Total users processed: " + processedUsers + "\n";
  summary += "Complete users (both files): " + (processedUsers - incompleteUsers.length) + "\n";
  summary += "Incomplete users: " + incompleteUsers.length + "\n\n";
  
  if (incompleteUsers.length > 0) {
    summary += "Users missing one or more data files:\n";
    incompleteUsers.forEach(function(uuid) {
      summary += "- " + uuid + " (Missing: ";
      if (!userSheets[uuid].mouseTracking) summary += "mouse_tracking.csv ";
      if (!userSheets[uuid].vesselCreation) summary += "vessel_creation.csv";
      summary += ")\n";
    });
  }
  
  // Add information about sheets that had headers added
  if (sheetsWithAddedHeaders.length > 0) {
    summary += "\nSheets where headers were automatically added:\n";
    sheetsWithAddedHeaders.forEach(function(sheetName) {
      summary += "- " + sheetName + "\n";
    });
  }
  
  exportFolder.createFile("export_summary.txt", summary, MimeType.PLAIN_TEXT);
  
  Logger.log('Export complete. Processed ' + processedUsers + ' users. Files saved to folder: ' + exportFolder.getName());
  Logger.log('Complete users: ' + (processedUsers - incompleteUsers.length));
  Logger.log('Incomplete users: ' + incompleteUsers.length);
  Logger.log('Sheets with added headers: ' + sheetsWithAddedHeaders.length);
  Logger.log('Export folder URL: ' + exportFolder.getUrl());
  
  // Return the URL to the export folder
  return exportFolder.getUrl();
}

/**
 * Converts the content of a sheet to a CSV string.
 * Checks for and adds missing column headers if needed.
 *
 * @param {Sheet} sheet - The sheet to convert.
 * @param {Array} expectedHeaders - The expected column headers for this sheet type.
 * @return {Object} Object containing CSV formatted string and whether headers were added.
 */
function convertSheetToCsv(sheet, expectedHeaders) {
  var data = sheet.getDataRange().getValues();
  var csv = '';
  var headersAdded = false;
  
  // Check if the sheet has headers by comparing with expected headers
  var hasHeaders = checkForHeaders(data[0], expectedHeaders);
  
  // If no headers, add them
  if (!hasHeaders && data.length > 0) {
    // Insert the expected headers at the beginning of our data array
    data.unshift(expectedHeaders);
    headersAdded = true;
    
    // Also add them to the actual sheet for future use
    sheet.insertRowBefore(1);
    sheet.getRange(1, 1, 1, expectedHeaders.length).setValues([expectedHeaders]);
    
    Logger.log('Added headers to sheet: ' + sheet.getName());
  }
  
  data.forEach(function(row) {
    // Map each field to a CSV-safe value: Escape quotes and wrap fields 
    // containing commas or quotes in double quotes.
    var csvRow = row.map(function(field) {
      // Convert to string in case the field is not
      field = String(field);
      // Escape any double quotes by replacing " with ""
      field = field.replace(/"/g, '""');
      // Wrap field in double quotes if it contains a comma or a double quote
      if (field.search(/("|,|\n)/g) >= 0) {
        field = '"' + field + '"';
      }
      return field;
    }).join(','); // Join the fields with commas
    
    csv += csvRow + "\n"; // Append the row with a newline
  });
  
  return {
    csv: csv,
    headersAdded: headersAdded
  };
}

/**
 * Checks if the first row contains proper headers.
 *
 * @param {Array} firstRow - The first row of the sheet.
 * @param {Array} expectedHeaders - The expected column headers.
 * @return {boolean} True if headers are present and valid.
 */
function checkForHeaders(firstRow, expectedHeaders) {
  // Quick check: If the first row is empty or has fewer columns than we expect, headers are missing
  if (!firstRow || firstRow.length < expectedHeaders.length) {
    return false;
  }
  
  // Check if first row matches our expected headers (case-insensitive)
  var headerMatches = 0;
  for (var i = 0; i < expectedHeaders.length && i < firstRow.length; i++) {
    if (firstRow[i] && String(firstRow[i]).toUpperCase() === expectedHeaders[i]) {
      headerMatches++;
    }
  }
  
  // If at least half of the expected headers match, consider it has headers
  // This allows for some flexibility in header naming or ordering
  return headerMatches >= (expectedHeaders.length / 2);
}

/**
 * Creates a UI menu to export data.
 */
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Keyhole Surgery Game')
    .addItem('Export Data for Analyser', 'exportDataForAnalyser')
    .addToUi();
}