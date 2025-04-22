/**
 * This function exports data from the Google Sheets file to a folder structure
 * organised by user ID, with each user having mouse_tracking.csv and vessel_creation.csv files.
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
      } else if (sheetName.indexOf('vessel-creation') !== -1) {
        if (!userSheets[uuid]) userSheets[uuid] = {};
        userSheets[uuid].vesselCreation = sheet;
      }
    }
  });
  
  // Count of processed users and list of users missing data
  var processedUsers = 0;
  var incompleteUsers = [];
  
  // Create the folder structure and export CSVs
  for (var uuid in userSheets) {
    // Create user folder
    var userFolder = exportFolder.createFolder(uuid);
    var isComplete = true;
    
    // Export mouse tracking data if available
    if (userSheets[uuid].mouseTracking) {
      var mouseTrackingCsv = convertSheetToCsv(userSheets[uuid].mouseTracking);
      userFolder.createFile("mouse_tracking.csv", mouseTrackingCsv, MimeType.PLAIN_TEXT);
      Logger.log('Created mouse_tracking.csv for user ' + uuid);
    } else {
      isComplete = false;
      Logger.log('Missing mouse tracking data for user ' + uuid);
    }
    
    // Export vessel creation data if available
    if (userSheets[uuid].vesselCreation) {
      var vesselCreationCsv = convertSheetToCsv(userSheets[uuid].vesselCreation);
      userFolder.createFile("vessel_creation.csv", vesselCreationCsv, MimeType.PLAIN_TEXT);
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
  
  exportFolder.createFile("export_summary.txt", summary, MimeType.PLAIN_TEXT);
  
  Logger.log('Export complete. Processed ' + processedUsers + ' users. Files saved to folder: ' + exportFolder.getName());
  Logger.log('Complete users: ' + (processedUsers - incompleteUsers.length));
  Logger.log('Incomplete users: ' + incompleteUsers.length);
  Logger.log('Export folder URL: ' + exportFolder.getUrl());
  
  // Return the URL to the export folder
  return exportFolder.getUrl();
}

/**
 * Converts the content of a sheet to a CSV string.
 *
 * @param {Sheet} sheet - The sheet to convert.
 * @return {string} CSV formatted string.
 */
function convertSheetToCsv(sheet) {
  var data = sheet.getDataRange().getValues();
  var csv = '';
  
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
  
  return csv;
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