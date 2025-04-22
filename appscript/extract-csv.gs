/**
 * This function exports every sheet (worksheet) in the active Google Sheets 
 * file to a separate CSV file, and saves them to a specified Google Drive folder.
 */
function saveWorksheetsToCSV() {
  // Open the active spreadsheet
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ss.getSheets();
  
  // Replace with your own folder ID if you want to save the files in a specific folder.
  // You can find the folder ID in the URL when you open the folder in Google Drive.
  var folderId = '1CI2ViKdxBBOn2JHL5QMhzbPghMAqYq3c';  
  var folder = DriveApp.getFolderById(folderId);
  
  // Loop through each sheet in the spreadsheet
  sheets.forEach(function(sheet) {
    // Convert the sheet data to CSV format
    var csv = convertSheetToCsv(sheet);
    // Name the CSV file after the sheet
    var fileName = sheet.getName() + '.csv';
    // Create the file in the designated folder
    folder.createFile(fileName, csv, MimeType.PLAIN_TEXT);
  });
  
  Logger.log('CSV export complete.');
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
