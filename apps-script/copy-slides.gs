/**
 * AANP 2026 — copy session slide PDFs into your Google Drive folder.
 * Skips AANP "no-handout" placeholders and anything already in the folder (dedup).
 *
 * SETUP (one time, ~3 min):
 *   1. Go to script.google.com  ->  New project
 *   2. Delete the sample, paste ALL of this, click Save
 *   3. Click Run -> choose "copySlides" -> Authorize (allow Drive access)
 *   It copies any newly-posted slide decks into the folder. Re-run anytime; it only adds new ones.
 *
 * OPTIONAL — make it a one-tap button:
 *   Deploy -> New deployment -> type "Web app" -> Execute as: Me, Who has access: Anyone with the link -> Deploy
 *   Copy the /exec URL and send it to me; I'll wire a "Copy slide PDFs to Drive" button into the app.
 */
var FOLDER_ID = '1bMjkD1PA54EXigKFE1SnQnHgexqGGXuv';
var PLACEHOLDER = 57794;            // AANP placeholder PDF size — treated as "no slides yet"
var SESSIONS = {"26.1.058":"Strategies to Engage in Serious Conversations","26.1.068":"NP Interview Playbook Prepare, Present, Prevail","26.2.006":"General Session Keynote","26.2.031":"From Burnout to Balance Building NP Resilience","26.2.046":"What's New in Sepsis Care 2026","26.2.070":"Leveraging Your NP Expertise to Shape Healthcare","26.2.112":"Cellulitis in the Acute Care Setting","26.2.127":"Parkinson’s 101 What Every Clinician Should Know","26.3.014":"Heads Up Concussion Assessment and Management","26.3.040":"Mastering Chest X-Ray Patterns","26.3.070":"Navigating New Guidelines in Atrial Fibrillation","26.3.097":"Pulmonary Hypertension in the ICU A Guide for NPs","26.3.120":"Complicated or Uncomplicated Simplifying UTI's","26.4.013":"General Session AANP Legislative Policy Update","26.4.028":"Cortisol ConundrumUnmasking Adrenal Insufficiency","26.4.045":"Pulmonary Precision Pharmacology","26.4.098":"Common Complaints,Uncommon Dx Cracking Mystery","26.4.119":"Transitioning From NP Practice to Academia","26.5.116":"General Session Unified, Energized, and Inspired NPs – Now W","26.1.078":"Welcome Reception","26.3.083":"Exhibit Hall Opens","26.5.115":"General Session Starting Soon","26.2.005":"General Session Starting Soon"};

function copySlides(codes) {
  // codes: optional array of session codes passed from the app (the checked ⭐ sessions).
  // If omitted (script run/opened directly), fall back to every session in SESSIONS.
  var list = (codes && codes.length) ? codes : Object.keys(SESSIONS);
  var folder = DriveApp.getFolderById(FOLDER_ID);
  var existing = {};
  var it = folder.getFiles();
  while (it.hasNext()) { existing[it.next().getName()] = true; }
  var added = [], dup = [], none = [];
  list.forEach(function (code) {
    code = String(code).trim();
    if (!code) return;
    var title = SESSIONS[code];                       // nice title if we know it...
    var name = title ? (code + ' ' + title + '.pdf') : (code + '.pdf');  // ...else just the code
    if (existing[name]) { dup.push(code); return; }
    try {
      var resp = UrlFetchApp.fetch('https://files.aanpdownload.org/2026/Natl/doc/' + code + '.pdf',
                                   { muteHttpExceptions: true, followRedirects: true });
      if (resp.getResponseCode() !== 200) { none.push(code); return; }
      var blob = resp.getBlob();
      if (blob.getBytes().length <= PLACEHOLDER + 50) { none.push(code); return; } // placeholder
      blob.setName(name);
      folder.createFile(blob);
      added.push(code);
    } catch (e) { none.push(code); }
  });
  var msg = 'Added ' + added.length + ' new deck(s): ' + added.join(', ') +
            '\nAlready in folder: ' + dup.length + (dup.length ? ' (' + dup.join(', ') + ')' : '') +
            '\nNo real slides yet: ' + none.length + (none.length ? ' (' + none.join(', ') + ')' : '');
  Logger.log(msg);
  return msg;
}

function doGet(e) {
  var codes = (e && e.parameter && e.parameter.codes)
    ? e.parameter.codes.split(',') : null;            // app passes ?codes=26.1.058,26.2.046,...
  var msg = copySlides(codes);
  return HtmlService.createHtmlOutput(
    '<div style="font-family:-apple-system,Arial;padding:18px;font-size:16px;max-width:560px">' +
    '<h2 style="color:#1565c0;margin:0 0 8px">AANP slides &#8594; your Drive</h2>' +
    '<pre style="white-space:pre-wrap;background:#f3f7fc;padding:12px;border-radius:8px">' +
    msg.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</pre>' +
    '<p>&#9989; Done — you can close this tab.</p></div>');
}
