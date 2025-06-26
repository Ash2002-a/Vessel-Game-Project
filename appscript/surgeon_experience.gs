function doPost(e) {
  try {
    const formType = e.parameter.formType;
    const data = JSON.parse(e.parameter.data);

    if (formType === 'surgeonInfo') {
      const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SurgeonInfo') || SpreadsheetApp.getActiveSpreadsheet().insertSheet('SurgeonInfo');

      // Add headers if sheet is empty
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(["TimeStamp", "UUID", "Experience"]);
      }

      const uuid = data.uuid;
      const experience = data.experience;

      // Get all UUIDs from column 2 (UUID column)
      const uuids = sheet.getRange(2, 2, sheet.getLastRow() - 1).getValues().flat();

      // If UUID already exists, skip appending but still return success
      if (!uuids.includes(uuid)) {
        sheet.appendRow([new Date(), uuid, experience]);
      }

      // Always return success, even if duplicate
      return ContentService.createTextOutput(JSON.stringify({ success: true })).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({ success: false, message: "Unknown Form Type" })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ success: false, message: error.message })).setMimeType(ContentService.MimeType.JSON);
  }
}
