/**
 * Greenhouse Google Sheets Ingestion Script
 * - Receives RAW samples and DAILY SUMMARY rows from Jetson
 * - Does NO computation
 * - NULL-safe
 * - Append-only
 */

/* =========================
   Utility
   ========================= */

function sheetValue(v) {
  return (v === null || v === undefined) ? "" : v;
}

/* =========================
   Daily Sheet Setup
   ========================= */

function ensureDailySheets(ss, dateString) {
  var props = PropertiesService.getScriptProperties();
  var lastSetup = props.getProperty("last_setup_date");
  if (lastSetup === dateString) return;

  var lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    Logger.log("WARN: Could not acquire lock for daily sheet setup");
    return;
  }

  try {
    lastSetup = props.getProperty("last_setup_date");
    if (lastSetup === dateString) return;

    var rawName = dateString + " RAW";
    var summaryName = dateString + " SUMMARY";

    var templateRaw = ss.getSheetByName("YYYY-MM-DD RAW");
    var templateSummary = ss.getSheetByName("YYYY-MM-DD SUMMARY");

    if (!templateRaw || !templateSummary) {
      throw new Error("Missing RAW or SUMMARY template sheets");
    }

    if (!ss.getSheetByName(rawName)) {
      templateRaw.copyTo(ss).setName(rawName);
    }

    if (!ss.getSheetByName(summaryName)) {
      templateSummary.copyTo(ss).setName(summaryName);
    }

    props.setProperty("last_setup_date", dateString);
  } finally {
    lock.releaseLock();
  }
}

/* =========================
   POST Endpoint
   ========================= */

function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput("ERROR: No data")
      .setMimeType(ContentService.MimeType.TEXT);
  }

  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var tz = ss.getSpreadsheetTimeZone();

    // -------------------------
    // DAILY SUMMARY PAYLOAD
    // -------------------------
    if (data.type === "summary") {
      var dateString = data.date;
      ensureDailySheets(ss, dateString);

      var summarySheet = ss.getSheetByName(dateString + " SUMMARY");
      if (!summarySheet) throw new Error("SUMMARY sheet missing");

      // Prevent duplicates
      if (summarySheet.getLastRow() > 1) {
        Logger.log("INFO: Summary already exists for " + dateString);
        return ContentService.createTextOutput("OK")
          .setMimeType(ContentService.MimeType.TEXT);
      }

      var summaryRow = [
        dateString,
        sheetValue(data.season_state),
        sheetValue(data.avg_temp_f),
        sheetValue(data.min_temp_f),
        sheetValue(data.max_temp_f),
        sheetValue(data.avg_humidity_rh),
        sheetValue(data.total_light_minutes),
        sheetValue(data.total_exhaust_minutes),
        sheetValue(data.total_circulation_minutes),
        sheetValue(data.notes)
      ];

      summarySheet.appendRow(summaryRow);

      return ContentService.createTextOutput("OK")
        .setMimeType(ContentService.MimeType.TEXT);
    }

    // -------------------------
    // RAW SAMPLE PAYLOAD
    // -------------------------
    var now = new Date();
    var dateString = Utilities.formatDate(now, tz, "yyyy-MM-dd");

    ensureDailySheets(ss, dateString);

    var rawSheet = ss.getSheetByName(dateString + " RAW");
    if (!rawSheet) throw new Error("RAW sheet missing");

    var timestamp = data.local_time
      ? new Date(data.local_time)
      : new Date();

    var rowData = [
      timestamp,
      sheetValue(data.inside_temp_f),
      sheetValue(data.inside_humidity_rh),
      sheetValue(data.inside_brightness_lux),
      sheetValue(data.outside_brightness_raw),
      sheetValue(data.cloud_coverage_pct),
      sheetValue(data.circulation_fan_pwm),
      sheetValue(data.exhaust_fan_pwm),
      sheetValue(data.grow_light_pwm),
      sheetValue(data.intent_window),
      sheetValue(data.control_mode),
      sheetValue(data.control_reason)
    ];

    rawSheet.appendRow(rowData);

    return ContentService.createTextOutput("OK")
      .setMimeType(ContentService.MimeType.TEXT);

  } catch (err) {
    Logger.log("ERROR: " + err);
    Logger.log(err.stack);
    return ContentService.createTextOutput("ERROR: " + err.toString())
      .setMimeType(ContentService.MimeType.TEXT);
  }
}
