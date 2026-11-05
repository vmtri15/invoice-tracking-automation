/**
 * Invoice Tracking Automation: Google Apps Script bound to the AR ledger Sheet.
 *
 * 1. onFormSubmit: checks each new Form row and writes "OK" or "ERROR: ..." in the Validation column.
 * 2. dailyOverdueAlert: once a day, posts unpaid invoices past their due date to Slack.
 *
 * Setup: set Script Property SLACK_WEBHOOK_URL (Project Settings > Script properties),
 * then run installTriggers() once from the editor. The webhook URL is never stored in this code.
 */

var SHEET_NAME = 'Form Responses 1';   // default tab name Google Forms creates
var REQUIRED = ['Customer', 'Invoice Number', 'Invoice Date', 'Due Date', 'Amount', 'Status'];
var VALIDATION_HEADER = 'Validation';

/** Run once by hand. Creates both triggers and removes old copies, so running it again is safe. */
function installTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (['onFormSubmit', 'dailyOverdueAlert'].indexOf(t.getHandlerFunction()) >= 0) ScriptApp.deleteTrigger(t);
  });
  var ss = SpreadsheetApp.getActive();
  ScriptApp.newTrigger('onFormSubmit').forSpreadsheet(ss).onFormSubmit().create();
  ScriptApp.newTrigger('dailyOverdueAlert').timeBased().everyDays(1).atHour(8).create();
}

/** Installable trigger: runs every time someone submits the Form. */
function onFormSubmit(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);  // two people submitting at once must not both pass the duplicate check
  try {
    var sheet = e.range.getSheet();
    var cols = headerIndex_(sheet);
    var data = sheet.getDataRange().getValues();
    var rowIdx = e.range.getRow() - 1;               // 0-based index into data
    var row = data[rowIdx];
    var others = data.filter(function (_, i) { return i > 0 && i !== rowIdx; })
                     .map(function (r) { return normalizeNumber_(r[cols['Invoice Number']]); });
    var errors = validateRow_(row, cols, others);
    sheet.getRange(rowIdx + 1, cols[VALIDATION_HEADER] + 1)
         .setValue(errors.length ? 'ERROR: ' + errors.join('; ') : 'OK');
  } finally {
    lock.releaseLock();
  }
}

/** Returns a list of error messages. An empty list means the row is fine. */
function validateRow_(row, cols, otherInvoiceNumbers) {
  var errors = [];
  REQUIRED.forEach(function (h) {
    if (String(row[cols[h]]).trim() === '') errors.push('Missing ' + h);
  });
  var num = normalizeNumber_(row[cols['Invoice Number']]);
  if (num && otherInvoiceNumbers.indexOf(num) >= 0) errors.push('Duplicate invoice number');
  var amount = parseAmount_(row[cols['Amount']]);
  if (String(row[cols['Amount']]).trim() !== '' && !(amount > 0)) errors.push('Amount must be greater than 0');
  return errors;
}

/** Time-driven trigger: daily summary of overdue, unpaid invoices posted to Slack. */
function dailyOverdueAlert() {
  var url = PropertiesService.getScriptProperties().getProperty('SLACK_WEBHOOK_URL');
  if (!url) throw new Error('Script Property SLACK_WEBHOOK_URL is not set');

  var sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  var cols = headerIndex_(sheet);
  var today = new Date();
  today.setHours(0, 0, 0, 0);                        // due today is not overdue yet

  var overdue = [], skipped = 0;
  sheet.getDataRange().getValues().slice(1).forEach(function (r) {
    if (String(r[cols[VALIDATION_HEADER]]).indexOf('ERROR') === 0) { skipped++; return; } // bad rows would double count
    if (String(r[cols['Status']]).trim().toLowerCase() === 'paid') return;
    var due = new Date(r[cols['Due Date']]);
    if (isNaN(due) || due >= today) return;
    overdue.push({
      customer: r[cols['Customer']], number: r[cols['Invoice Number']],
      amount: parseAmount_(r[cols['Amount']]), days: Math.floor((today - due) / 86400000)
    });
  });
  if (!overdue.length) { Logger.log('No overdue invoices today.'); return; }

  overdue.sort(function (a, b) { return b.days - a.days; });
  var total = overdue.reduce(function (s, o) { return s + o.amount; }, 0);
  var lines = overdue.slice(0, 15).map(function (o) {
    return '\u2022 ' + o.number + ' | ' + o.customer + ' | ' + money_(o.amount) + ' | ' + o.days + ' days overdue';
  });
  var text = ':rotating_light: *AR overdue summary*: ' + overdue.length + ' invoices, ' + money_(total) + ' past due\n' +
             lines.join('\n') +
             (overdue.length > 15 ? '\n...and ' + (overdue.length - 15) + ' more' : '') +
             (skipped ? '\n_' + skipped + ' rows with validation errors were skipped_' : '');

  UrlFetchApp.fetch(url, { method: 'post', contentType: 'application/json', payload: JSON.stringify({ text: text }) });
}

// ---------- helpers ----------

/** Maps header name to column index. Adds the Validation column if it is missing. */
function headerIndex_(sheet) {
  var headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  if (headers.indexOf(VALIDATION_HEADER) < 0) {
    sheet.getRange(1, headers.length + 1).setValue(VALIDATION_HEADER);
    headers.push(VALIDATION_HEADER);
  }
  var idx = {};
  headers.forEach(function (h, i) { idx[String(h).trim()] = i; });
  REQUIRED.forEach(function (h) { if (!(h in idx)) throw new Error('Sheet is missing column: ' + h); });
  return idx;
}

function normalizeNumber_(v) { return String(v).trim().toUpperCase(); }
function parseAmount_(v) { return typeof v === 'number' ? v : parseFloat(String(v).replace(/[$,\s]/g, '')); }
function money_(n) { return '$' + n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
