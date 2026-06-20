#!/usr/bin/env python3
"""Reproducible builder for data.js.

Parses the saved AANP session page (source-aanp-sessions.html), extracts every
session, derives a primary clinical topic plus cross-cutting "featured" tags,
and writes window.SESSIONS to data.js. Each session carries a `tags` array so a
session can appear under several filters at once (multi-tag).

Re-fetch source with:
  curl -s -A "Mozilla/5.0" https://sessions.aanp.org/ -o source-aanp-sessions.html
"""
import re, html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "source-aanp-sessions.html")

DAYORDER = {"Tuesday":0,"Wednesday":1,"Thursday":2,"Friday":3,"Saturday":4}
REC_DEFAULT_TRUE = {"Concurrent Presentation","General Session","Seminar","Industry Supported Symposium"}

# ---- primary clinical topic (first match wins) ----
CLINICAL = [
 ("Cardiology / Vascular", r"cardi|\bheart\b|heart failure|hypertens|blood pressure|\bbp\b|\bhf\b|atrial|afib|arrhythm|lipid|cholesterol|statin|\becgs?\b|\bekgs?\b|12 lead|valv|anticoagul|\bdvt\b|embol|\bpe\b|arter|aort|ischemi|dissection|limb salvage|vascular|venous|\bmi\b|myocard|\bcad\b|angina|carotid|\bahas?\b|acc bp"),
 ("Neurology", r"neuro|stroke|seizure|epilep|parkinson|headache|migraine|dementia|alzheimer|multiple sclerosis|vestibul|concussion|\btbi\b|vertigo|dizz|myasthen|neuropath|spinal cord|\bbrain\b|restless leg|tremor|spasticit|subarachnoid|aneurysm"),
 ("Pulmonary / Critical Care", r"pulmon|copd|asthma|respirat|sepsis|ventilat|\bicu\b|critical care|ards|\blung|pneumonia|dyspnea|spiromet|bronch|sleep apnea|cystic fibros|pleural|chest x-?ray|trache|pertussis|pulse check|spinning|critical illness"),
 ("Endocrine / Diabetes", r"diabet|insulin|glucose|\bcgm\b|thyroid|endocrin|obesity|\bweight\b|metabolic|cortisol|adrenal|hypercortisol|glp-?1|osteoporos|osteopen|pituitary|\bmen2\b|testoster|hormone"),
 ("Women's Health / OB-GYN", r"gyneco|\bwomen|pregnan|menopaus|perimenopaus|perinatal|preconcept|contracep|\bpcos\b|polycystic ovar|breast|cervical|obstetr|prenatal|maternal|\bhpv\b|pelvic|vaginal|vaginitis|lactation|fertilit|menstr|low desire"),
 ("Men's Health", r"\bmale\b|\bmen's\b|prostat|\bbph\b|erectile|gynecomast|man boob"),
 ("Behavioral / Mental Health", r"depress|anxiety|psychiatr|mental health|suicide|substance|addiction|opioid|\bptsd\b|behavioral|bipolar|\badhd\b|eating disorder|anorexia|\bocd\b|\bsud\b|\bmoud\b|fentanyl|alcohol|marijuana|cannabis|\bmoody\b|mood disorder|withdrawal|self-harm|\bipv\b|intimate partner|abuse|trafficking|shame|trauma-informed|\baces\b"),
 ("Emergency / Trauma", r"trauma patient|trauma care|major trauma|trauma:|resuscitat|hemorrhagic|\bshock\b|overdose|toxic alcohol|envenom|\bburn\b|laceration|acute limb|wilderness|disaster|mass casualty|initial assessment"),
 ("Pediatrics / Neonatal", r"pediatr|\bchild|neonat|\bnicu\b|adolescen|infant|newborn|congenital|premature birth|gaming|youth"),
 ("Dermatology / Wound", r"derm|\bskin\b|biopsy|cryo|lesion|\bacne\b|wound|rash|psorias|eczema|melanoma|aesthetic|cosmet|cellulitis"),
 ("Geriatrics / Palliative", r"geriatr|older adult|aging|age-friendly|\belder|\bfalls\b|deprescrib|advanced care planning|end[- ]of[- ]life|palliat|hospice|long-?term care|decision making capacit|\bdnr\b|serious conversation|silent wishes"),
 ("Infectious Disease / Immunization", r"infect|\bhiv\b|hepatit|antibiotic|antimicrob|\btick|lyme|vaccin|immuniz|\bcovid|\bstis?\b|\bstds?\b|tubercul|\btb\b|h\.? pylori|mycoplasma|ureaplasma|travel medicine|travel health|correctional"),
 ("Oncology", r"cancer|oncolog|\btumor|chemo|malignan|leukemia|lymphoma|metasta|lynch syndrome|immunotherap|immune-related advers"),
 ("MSK / Orthopedics / Pain", r"orthoped|musculoskelet|\bjoint|injection|\bpain\b|arthrit|osteoarthr|fracture|back pain|sprain|tendon|\bmsk\b|lipedema|fibromyalg|disabilit"),
 ("Gastroenterology / Hepatology", r"gastro|\bgi\b|liver|hepat|\bibd\b|bowel|gerd|colon|crohn|colitis|pancrea|\bnafld\b|mafld|\bmash\b|microhematuria"),
 ("Renal / Urology", r"renal|kidney|urolog|bladder|\buti\b|nephro|incontinen|dialysis|\bgu exam|genitourinar|hematuria"),
 ("Pharmacology", r"pharmac|prescrib|deprescrib|\bmedication|polypharm|drug interaction|sedation|analges|new drug|biologic|small molecul|psychotropic|insomnia pharmac"),
 ("Procedures / POCUS / Imaging", r"ultrasound|pocus|point of care|suturing|\bheent\b|\bent\b|procedures|knobology|vascular access|aspiration|incision|preoperative|preop|perioperative|prehab|surgical|x-?ray|imaging|radiolog"),
 ("Research / Scholarship", r"poster|\bresearch\b|qualitative|implementation science|\bpublish|peer review|survey|scholarship|\bqi\b|quality improvement|dissertation|author|journalism|grant|evidence guiding|program evaluation|\bosce\b|methods"),
 ("Technology / AI", r"artificial intelligence|\bai\b|genomic|digital health|machine learning|prompt engineering|telehealth|virtual"),
 ("Lifestyle / Nutrition", r"lifestyle|nutrition|\bdiet\b|exercise|\bsleep\b|integrative|self-?care|coaching|heat and health|wellness"),
 ("Practice / Professional", r"malpractice|legal|billing|coding|leadership|business|practice management|practice authorit|resilience|burnout|curriculum|educat|policy|regulat|advocacy|advocat|reimburse|interview|preceptor|mentor|onboarding|negotiat|finance|retirement|contract|documentation|compliance|risk|entrepreneur|academia|value-based|innovat|career|profession|military|veteran|uniformed|\barmy\b|\bnavy\b|air force|usphs|chief|grassroots|big beautiful bill|barrier|disruption|workforce|diversity|now what|mindset|stethoscope|\bworth\b"),
 ("Primary / Urgent Care", r"primary care|urgent care|\bcough|\bfever|allerg|sinus|otitis|pharyngitis|preventive|screening|health maintenance|common complaint|mystery|spanish|capacity"),
]

# ---- cross-cutting featured tags (a session may match several) ----
ACUTE = r"acute care|critical care|\bicu\b|critically ill|sepsis|resuscitat|ventilat|hemodynam|trauma patient|hemorrhag|subarachnoid|aneurysm|\bshock\b|cellulitis in the acute|transitional care after critical|pleural|tracheostomy|preoperative|perioperative|limb ischemia|dissection|arterial catastroph|critical illness|chest x-?ray|sedation"
TEACH = r"teach|precept|facult|academ|curricul|educat|\bstudent|\bdnp\b|\bosce\b|mentor|onboarding|preclinical|nurse educator|journalism|peer review|publish|\bauthor\b|fellowship|fellows"
MEALS = r"breakfast|luncheon|\blunch\b|\bdinner\b|symposi|product theater|sponsored|supported sympos"

def mins(t):
    m = re.match(r'(\d+):(\d+)\s*(AM|PM)', t or '')
    if not m: return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == 'PM' and h != 12: h += 12
    if ap == 'AM' and h == 12: h = 0
    return h*60 + mi

def field(card, name):
    m = re.search(r'<td class="fieldName">'+re.escape(name)+r'</td>\s*<td>(.*?)</td>', card, re.S)
    if not m: return ""
    return html.unescape(re.sub(r'\s+',' ', re.sub(r'<[^>]+>',' ', m.group(1)))).strip()

def clinical_topic(title):
    t = title.lower()
    for name, pat in CLINICAL:
        if re.search(pat, t): return name
    return "Other / General"

def build():
    doc = open(SRC, encoding='utf-8', errors='replace').read()
    cards = re.split(r'<div class="card filterParent"', doc)[1:]
    out = []
    for i, c in enumerate(cards):
        hm = re.search(r'<h6>(.*?)</h6>', c, re.S)
        raw = html.unescape(re.sub(r'\s+',' ', re.sub(r'<[^>]+>','', hm.group(1)))).strip() if hm else ""
        code = raw.split(' ',1)[0] if raw and raw[0].isdigit() else ""
        title = re.sub(r'^[\d.]+\s+','', raw)
        time_raw = field(c, 'Time')
        tm = re.match(r'(.*?)\s*-\s*(.*?)\s*\((\w+),\s*([\d/]+)\)', time_raw)
        if tm: start, end, day, date = tm.group(1).strip(), tm.group(2).strip(), tm.group(3), tm.group(4)
        else:
            t2 = re.search(r'\((\w+),\s*([\d/]+)\)', time_raw)
            start, end = "", ""; day, date = (t2.group(1), t2.group(2)) if t2 else ("","")
        typ = field(c, 'Presentation Type')
        level = field(c, 'Content Level')
        ce_raw = field(c, 'CE Hours')
        ce = float(re.search(r'[\d.]+', ce_raw).group()) if re.search(r'[\d.]+', ce_raw) else 0.0
        fee_raw = field(c, 'Additional Fee')
        fee_amt = int(float(re.search(r'[\d.]+', fee_raw).group())) if re.search(r'[\d.]+', fee_raw) else 0
        fee = fee_amt > 0

        topic = clinical_topic(title)
        low = (title + ' ' + typ).lower()
        tags = [topic]                                  # primary clinical topic first
        if re.search(ACUTE, low) and "Acute Care" not in tags: tags.append("Acute Care")
        if re.search(TEACH, low): tags.append("University Teaching")
        if fee: tags.append("Extra Cost")
        if ce == 0: tags.append("Optional (no CEUs)")
        if typ == "Industry Supported Symposium" or re.search(MEALS, low): tags.append("Sponsored Meals")
        # de-dupe, keep order
        seen=set(); tags=[t for t in tags if not (t in seen or seen.add(t))]

        out.append({
            "id": code or f"s{i}", "code": code, "title": title,
            "day": day, "date": date, "dayOrder": DAYORDER.get(day, 9),
            "start": start, "end": end, "startMin": mins(start), "endMin": mins(end),
            "type": typ, "level": level, "ce": ce, "fee": fee, "feeAmt": fee_amt,
            "topic": topic, "tags": tags,
            "recordable": typ in REC_DEFAULT_TRUE,
        })

    with open(os.path.join(HERE, "data.js"), "w") as f:
        f.write("// AANP 2026 National Conference sessions — built by build_data.py from source-aanp-sessions.html\n")
        f.write("// Each session has a `tags` array (clinical topic + cross-cutting featured tags) so it can match several filters.\n")
        f.write("window.SESSIONS = " + json.dumps(out, separators=(',',':')) + ";\n")

    from collections import Counter
    tagc = Counter(t for o in out for t in o["tags"])
    print(f"wrote data.js: {len(out)} sessions")
    print("featured tag counts:")
    for k in ["Neurology","Acute Care","Pharmacology","University Teaching","Extra Cost","Optional (no CEUs)","Sponsored Meals"]:
        print(f"  {tagc.get(k,0):4d}  {k}")
    print("paid sessions (fee=true):", sum(1 for o in out if o['fee']))

if __name__ == "__main__":
    build()
