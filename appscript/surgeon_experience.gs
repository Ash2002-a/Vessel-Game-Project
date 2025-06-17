function doPost(e) {
  try {
    const formType = e.parameter.formType;
    const data = JSON.parse(e.parameter.data);

    if (formType === 'surgeonInfo') {
      const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('SurgeonInfo') || SpreadsheetApp.getActiveSpreadsheet().insertSheet('SurgeonInfo');
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(["TimeStamp", "UUID", "Experience"]);
      }
      const uuid = data.uuid;
      const experience = data.experience;
      sheet.appendRow([new Date(), uuid, experience]);

      return ContentService.createTextOutput(JSON.stringify({ success: true })).setMimeType(ContentService.MimeType.JSON);

    }
    return ContentService.createTextOutput(JSON.stringify({ success: false, message: "Unknown Form Type" })).setMimeType(ContentService.MimeType.JSON);


  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({ success: false, message: error.message })).setMimeType(ContentService.MimeType.JSON);
  }

}


