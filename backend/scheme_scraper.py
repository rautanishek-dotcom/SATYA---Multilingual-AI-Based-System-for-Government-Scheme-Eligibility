"""
SATYA – Hybrid Real-Time Scheme Updation System
================================================
Architecture:
  Module 1 – config.py        : Settings & MongoDB connection
  Module 2 – dataset.py       : 25 curated built-in schemes
  Module 3 – scraper.py       : Web scraping (Wikipedia)
  Module 4 – updater.py       : MongoDB upsert logic
  Module 5 – scheme_scraper.py: Main orchestrator (run this)

Run  : python scheme_scraper.py
Log  : scraper.log (auto-created)
Schedule: run_scraper.bat (Windows Task Scheduler)
"""

# ══════════════════════════════════════════════════════════
# MODULE 1 – CONFIGURATION & MONGODB CONNECTION
# ══════════════════════════════════════════════════════════
import io, os, sys, logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Fix Windows console Unicode (prevents UnicodeEncodeError with emojis)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv()

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME    = "Satya"
COLLECTION = "schemes"

LOG_FILE = os.path.join(os.path.dirname(__file__), "scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("satya_scraper")

def get_collection():
    """Connect to MongoDB and return (client, collection)."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        col = client[DB_NAME][COLLECTION]
        log.info("[OK] MongoDB connected -> %s.%s", DB_NAME, COLLECTION)
        return client, col
    except PyMongoError as e:
        log.error("[FAIL] MongoDB: %s", e)
        sys.exit(1)


# ══════════════════════════════════════════════════════════
# MODULE 2 – BUILT-IN CURATED DATASET (25 Real Schemes)
# Primary source – always works, no internet needed.
# These are NEW schemes not present in seed.py.
# ══════════════════════════════════════════════════════════
BUILTIN_SCHEMES = [
    {
        "name": "PM e-VIDHYA",
        "eligibility": "Students from Class 1-12 in government schools.",
        "benefits": "Free digital education via DTH TV, radio and online in 12 languages.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://www.education.gov.in/",
        "description": "One Nation One Digital Platform for education.",
        "rules": {"min_age": 6, "max_age": 18, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "Har Ghar Jal Yojana (Jal Jeevan Mission)",
        "eligibility": "Rural households without a functional tap water connection.",
        "benefits": "Piped drinking water connection to every rural household.",
        "category": "Water & Sanitation",
        "state": "All India",
        "official_website": "https://jaljeevanmission.gov.in/",
        "description": "Mission to provide safe tap water supply to every rural home.",
        "rules": {"min_age": 18, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "e-Shram Portal Registration",
        "eligibility": "Unorganised sector workers aged 16-59 not covered under EPFO/ESIC.",
        "benefits": "e-Shram card and Rs 2 lakh PMSBY accident insurance coverage.",
        "category": "Social Security",
        "state": "All India",
        "official_website": "https://eshram.gov.in/",
        "description": "National database of unorganised workers for social security.",
        "rules": {"min_age": 16, "max_age": 59, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "PM Dakshata Aur Kushalta Sampann Hitgrahi (PM-DAKSH)",
        "eligibility": "SC, OBC, EBC, DNT citizens and sanitation workers aged 18-45.",
        "benefits": "Free skill training with stipend up to Rs 1500/month.",
        "category": "Skill Development",
        "state": "All India",
        "official_website": "https://pmdaksh.dosje.gov.in/",
        "description": "Upskilling scheme for SC, OBC, EBC, DNT and sanitation workers.",
        "rules": {"min_age": 18, "max_age": 45, "allowed_categories": ["sc", "st", "obc"], "gender": ["all"]},
    },
    {
        "name": "National Apprenticeship Promotion Scheme (NAPS)",
        "eligibility": "Youth aged 14-35 seeking apprenticeship training.",
        "benefits": "Rs 1500/month stipend support and basic training reimbursement.",
        "category": "Employment",
        "state": "All India",
        "official_website": "https://www.apprenticeshipindia.org/",
        "description": "Financial support for employers engaging apprentices.",
        "rules": {"min_age": 14, "max_age": 35, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "PM Annadata Aay Sanrakshan Abhiyan (PM-AASHA)",
        "eligibility": "Farmers growing notified oilseeds, pulses and copra crops.",
        "benefits": "Procurement at MSP and price deficiency payment to protect farm income.",
        "category": "Agriculture",
        "state": "All India",
        "official_website": "https://www.myscheme.gov.in/",
        "description": "Price support mechanism to protect farmers from distress sales.",
        "rules": {"min_age": 18, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"], "occupation": ["farmer"]},
    },
    {
        "name": "PM TB Mukt Bharat Abhiyan",
        "eligibility": "TB patients undergoing treatment at DOTS centres.",
        "benefits": "Rs 500/month nutritional support and free anti-TB medicines.",
        "category": "Health",
        "state": "All India",
        "official_website": "https://nikshay.in/",
        "description": "National TB elimination mission with nutritional support.",
        "rules": {"min_age": 0, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "SWAMITVA Scheme",
        "eligibility": "Residents of rural inhabited areas.",
        "benefits": "Property cards (Rights of Record) enabling institutional credit access.",
        "category": "Rural Development",
        "state": "All India",
        "official_website": "https://svamitva.nic.in/",
        "description": "Property rights mapping for rural households using drone survey.",
        "rules": {"min_age": 18, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "PM Krishi Sinchayee Yojana (PMKSY)",
        "eligibility": "Farmers with agricultural land requiring irrigation.",
        "benefits": "Subsidy on drip/sprinkler irrigation, watershed development.",
        "category": "Agriculture",
        "state": "All India",
        "official_website": "https://pmksy.gov.in/",
        "description": "Expanding irrigation coverage and improving water use efficiency.",
        "rules": {"min_age": 18, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"], "occupation": ["farmer"]},
    },
    {
        "name": "Samarth Scheme for Textiles",
        "eligibility": "Youth aged 14-35 seeking employment in textiles and apparel sector.",
        "benefits": "Free skill training with Rs 8000 stipend and placement assistance.",
        "category": "Skill Development",
        "state": "All India",
        "official_website": "https://samarth-textiles.gov.in/",
        "description": "Demand-driven placement-linked skill development for textiles.",
        "rules": {"min_age": 14, "max_age": 35, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "PM Yuva 2.0",
        "eligibility": "Indian citizens below 30 years with creative writing interest.",
        "benefits": "Rs 50,000/month stipend for 6 months, mentorship, publication support.",
        "category": "Literature & Culture",
        "state": "All India",
        "official_website": "https://www.nbtindia.gov.in/",
        "description": "Mentorship programme to train young authors and promote Indian literature.",
        "rules": {"min_age": 15, "max_age": 30, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "National Livelihood Mission - Aajeevika",
        "eligibility": "Rural BPL families, especially women and youth.",
        "benefits": "Interest subvention on loans and self-help group formation support.",
        "category": "Livelihood",
        "state": "All India",
        "official_website": "https://aajeevika.gov.in/",
        "description": "Self-employment and skill training for rural BPL families.",
        "rules": {"min_age": 18, "max_age": 60, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "Dr Ambedkar Post-Matric Scholarship for OBC",
        "eligibility": "OBC students with family income below Rs 1 lakh per annum.",
        "benefits": "Course fee, maintenance allowance and study allowance.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://scholarships.gov.in/",
        "description": "Central scholarship for OBC students in post-matriculation courses.",
        "rules": {"min_age": 14, "max_age": 35, "max_income": 100000, "allowed_categories": ["obc"], "gender": ["all"]},
    },
    {
        "name": "Pre-Matric Scholarship for SC Students",
        "eligibility": "SC students in Classes 9-10 with family income below Rs 2.5 lakh.",
        "benefits": "Maintenance allowance, ad hoc grant and study allowance.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://scholarships.gov.in/",
        "description": "Central scholarship for SC students in Classes 9 and 10.",
        "rules": {"min_age": 13, "max_age": 18, "max_income": 250000, "allowed_categories": ["sc"], "gender": ["all"]},
    },
    {
        "name": "National Fellowship for ST Students",
        "eligibility": "ST students who cleared UGC-NET or CSIR-NET.",
        "benefits": "Rs 31,000-35,000/month fellowship plus HRA for research duration.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://tribal.nic.in/",
        "description": "JRF/SRF fellowship for ST students pursuing M.Phil or PhD.",
        "rules": {"min_age": 21, "max_age": 40, "allowed_categories": ["st"], "gender": ["all"]},
    },
    {
        "name": "PM SHRI Schools Scheme",
        "eligibility": "Students enrolled in government PM SHRI schools.",
        "benefits": "Smart classrooms, labs, sports infrastructure under NEP 2020.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://pmshrischools.education.gov.in/",
        "description": "Upgradation of 14,500 government schools into modern holistic schools.",
        "rules": {"min_age": 5, "max_age": 18, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "Scheme for Adolescent Girls (Kishori)",
        "eligibility": "Out-of-school girls aged 11-14 from BPL families.",
        "benefits": "6 kg food grains/month, IFA supplements, nutrition and life skills training.",
        "category": "Women & Child",
        "state": "All India",
        "official_website": "https://wcd.gov.in/",
        "description": "Nutritional support and life skills for adolescent girls.",
        "rules": {"min_age": 11, "max_age": 14, "max_income": 100000, "allowed_categories": ["all"], "gender": ["female"]},
    },
    {
        "name": "NAMASTE Scheme",
        "eligibility": "Sanitation workers and safai mitras engaged in hazardous cleaning.",
        "benefits": "PPE kits, Rs 40,000 capital subsidy for machinery and training allowance.",
        "category": "Social Justice",
        "state": "All India",
        "official_website": "https://namaste.gov.in/",
        "description": "Mechanisation of sewer cleaning to eliminate manual scavenging.",
        "rules": {"min_age": 18, "max_age": 60, "allowed_categories": ["sc"], "gender": ["all"]},
    },
    {
        "name": "PM Janman Yojana",
        "eligibility": "Members of 75 identified Particularly Vulnerable Tribal Groups (PVTGs).",
        "benefits": "Pucca houses, safe drinking water, roads, solar lighting and mobile health.",
        "category": "Tribal Welfare",
        "state": "All India",
        "official_website": "https://tribal.nic.in/",
        "description": "Development programme for Particularly Vulnerable Tribal Groups.",
        "rules": {"min_age": 0, "max_age": 100, "allowed_categories": ["st"], "gender": ["all"]},
    },
    {
        "name": "Agnipath Scheme",
        "eligibility": "Indian youth aged 17.5 to 23 years for military enlistment.",
        "benefits": "Rs 30,000-40,000/month pay and Rs 11.71 lakh Seva Nidhi after 4 years.",
        "category": "Defence Employment",
        "state": "All India",
        "official_website": "https://joinindianarmy.nic.in/",
        "description": "Short-term military enlistment programme for Indian youth.",
        "rules": {"min_age": 17, "max_age": 23, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "One Student One Laptop Scheme",
        "eligibility": "Technical education students from EWS families (AICTE institutions).",
        "benefits": "Free laptop for pursuing technical or professional education.",
        "category": "Education",
        "state": "All India",
        "official_website": "https://www.aicte-india.org/",
        "description": "Free laptops for meritorious students from economically weaker sections.",
        "rules": {"min_age": 17, "max_age": 28, "max_income": 800000, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "PM Oilseeds and Oil Palm Mission (PMOPM)",
        "eligibility": "Farmers growing oilseeds and oil palm in designated regions.",
        "benefits": "Seed kits, crop insurance and MSP-linked price support.",
        "category": "Agriculture",
        "state": "All India",
        "official_website": "https://www.myscheme.gov.in/",
        "description": "Promotes domestic oilseed production to reduce import dependence.",
        "rules": {"min_age": 18, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"], "occupation": ["farmer"]},
    },
    {
        "name": "PM Jan Arogya Yojana - Health Wellness Centres",
        "eligibility": "All Indian citizens especially in rural and semi-urban areas.",
        "benefits": "Free OPD, diagnostics, medicines and telemedicine services.",
        "category": "Health",
        "state": "All India",
        "official_website": "https://pmjay.gov.in/",
        "description": "Health and Wellness Centres under Ayushman Bharat for primary care.",
        "rules": {"min_age": 0, "max_age": 100, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "Pradhan Mantri Garib Kalyan Rozgar Abhiyan",
        "eligibility": "Migrant workers who returned to rural areas.",
        "benefits": "125 days guaranteed employment and rural infrastructure development.",
        "category": "Employment",
        "state": "All India",
        "official_website": "https://www.rural.nic.in/",
        "description": "Employment scheme for migrant workers in rural districts.",
        "rules": {"min_age": 18, "max_age": 60, "allowed_categories": ["all"], "gender": ["all"]},
    },
    {
        "name": "National Action for Mechanised Sanitation (NAMASTE) - Training",
        "eligibility": "Urban local body sanitation workers seeking skill upgradation.",
        "benefits": "Certified training, occupational safety gear and alternative livelihood.",
        "category": "Skill Development",
        "state": "All India",
        "official_website": "https://namaste.gov.in/",
        "description": "Training arm of NAMASTE for safe sanitation work practices.",
        "rules": {"min_age": 18, "max_age": 55, "allowed_categories": ["all"], "gender": ["all"]},
    },
]


# ══════════════════════════════════════════════════════════
# MODULE 3 – WEB SCRAPER (Wikipedia – reliably unblocked)
# ══════════════════════════════════════════════════════════
import re, time, hashlib, json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
WIKI_LIST_URL = "https://en.wikipedia.org/wiki/List_of_government_schemes_in_India"
SCHEME_KEYWORDS = (
    "yojana", "scheme", "mission", "programme", "program",
    "bima", "nidhi", "vikas", "bharat", "pradhan", "rashtriya",
    "swachh", "awas", "kisan", "krishi", "mukhya",
)


def safe_get(url, timeout=15, retries=2):
    """HTTP GET with retry. Returns Response or None."""
    for i in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            log.warning("  Attempt %d/%d -> %s: %s", i, retries, url, e)
            time.sleep(3 * i)
    log.error("  Giving up: %s", url)
    return None


def get_wiki_summary(url):
    """Fetch first meaningful paragraph from a Wikipedia article."""
    resp = safe_get(url, timeout=10, retries=1)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("div", {"class": "mw-parser-output"})
    if not content:
        return ""
    for p in content.find_all("p", recursive=False):
        text = p.get_text(strip=True)
        if text and len(text) > 50:
            # Remove citation markers like [1], [2]
            text = re.sub(r"\[\d+\]", "", text)
            return text[:500]
    return ""


def scrape_wikipedia():
    """
    Scrape scheme names and descriptions from Wikipedia.
    Wikipedia is publicly accessible and does not block standard requests.
    Returns list of scheme dicts.
    """
    log.info("--- Source B: Wikipedia ---")
    schemes = []
    seen: set[str] = set()

    resp = safe_get(WIKI_LIST_URL)
    if not resp:
        log.warning("Wikipedia unreachable, skipping.")
        return schemes

    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("div", {"class": "mw-parser-output"})
    if not content:
        return schemes

    for li in content.find_all(["li", "td"]):
        a = li.find("a", href=re.compile(r"^/wiki/"), title=True)
        if not a:
            continue
        name = a.get_text(strip=True)
        href = "https://en.wikipedia.org" + a["href"]

        if not name or len(name) < 6:
            continue
        if not any(kw in name.lower() for kw in SCHEME_KEYWORDS):
            continue

        slug = _make_slug(name)
        if slug in seen:
            continue
        seen.add(slug)

        description = get_wiki_summary(href)
        time.sleep(0.5)   # polite crawl delay

        schemes.append({
            "name"            : name,
            "eligibility"     : "",
            "benefits"        : "",
            "category"        : "Government Scheme",
            "state"           : "All India",
            "official_website": href,
            "description"     : description,
            "rules"           : {"allowed_categories": ["all"], "gender": ["all"]},
        })

    log.info("Wikipedia: %d unique schemes collected.", len(schemes))
    return schemes


# ══════════════════════════════════════════════════════════
# MODULE 4 – MONGODB UPDATER (upsert with duplicate prevention)
# ══════════════════════════════════════════════════════════
from pymongo import UpdateOne
from pymongo.errors import PyMongoError


def _make_slug(name: str) -> str:
    """URL-safe unique identifier from scheme name."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s[:100]


def _fingerprint(scheme: dict) -> str:
    """MD5 of key fields to detect content changes."""
    data = json.dumps(
        {k: scheme.get(k, "") for k in ("name", "description", "benefits", "eligibility")},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.md5(data.encode()).hexdigest()


def ensure_sparse_unique_index(collection):
    """
    Create a SPARSE unique index on scheme_slug.

    Why sparse?
      Existing seed documents don't have a scheme_slug field (null).
      A regular unique index would treat all nulls as duplicates and fail.
      A sparse index simply IGNORES documents where the field is missing/null,
      so old seed data is unaffected while new scraped data is deduplicated.
    """
    existing = [i["name"] for i in collection.list_indexes()]
    if "scheme_slug_1" not in existing:
        collection.create_index("scheme_slug", unique=True, sparse=True)
        log.info("[OK] Sparse unique index created on scheme_slug.")
    else:
        log.info("[OK] Unique index already exists.")


def prepare_document(scheme: dict, source: str) -> dict:
    """
    Build the final MongoDB document from a raw scheme dict.

    MongoDB Document Schema:
    ─────────────────────────────────────────────────────────
    {
      "scheme_slug"        : "pm-e-vidhya",            ← unique key
      "source"             : "builtin" | "wikipedia",  ← data origin
      "name"               : "PM e-VIDHYA",
      "description"        : "...",
      "eligibility"        : "...",
      "benefits"           : "...",
      "category"           : "Education",
      "state"              : "All India",
      "official_website"   : "https://...",
      "rules"              : { eligibility engine fields },
      "content_hash"       : "md5 of key fields",      ← change detection
      "first_seen"         : ISODate,                   ← set only on insert
      "last_updated"       : ISODate,                   ← updated every run
      "is_active"          : true
    }
    """
    doc = dict(scheme)
    doc["scheme_slug"]  = _make_slug(scheme["name"])
    doc["source"]       = source
    doc["is_active"]    = True
    doc["content_hash"] = _fingerprint(scheme)
    # Ensure rules field always exists
    if "rules" not in doc:
        doc["rules"] = {"allowed_categories": ["all"], "gender": ["all"]}
    return doc


def upsert_to_mongodb(collection, schemes: list[dict], source: str) -> dict:
    """
    Bulk-upsert schemes using scheme_slug as the unique match key.

    Duplicate Prevention Logic:
      UpdateOne with upsert=True checks if scheme_slug exists.
      - NOT found  →  INSERT new document ($setOnInsert sets first_seen)
      - FOUND      →  UPDATE only changed fields ($set updates last_updated)
      This guarantees zero duplicate entries regardless of how many times
      the scraper runs.
    """
    if not schemes:
        return {"inserted": 0, "updated": 0, "unchanged": 0}

    now = datetime.now(timezone.utc)
    operations = []

    for scheme in schemes:
        doc = prepare_document(scheme, source)
        slug = doc.pop("scheme_slug")   # used as filter key

        # Fields to always update
        set_fields = {**doc, "last_updated": now}

        operations.append(
            UpdateOne(
                filter={"scheme_slug": slug},           # match condition
                update={
                    "$set"        : set_fields,          # update these fields
                    "$setOnInsert": {                    # only on NEW insert
                        "scheme_slug": slug,
                        "first_seen" : now,
                    },
                },
                upsert=True,                            # insert if not found
            )
        )

    try:
        result = collection.bulk_write(operations, ordered=False)
        stats = {
            "inserted" : result.upserted_count,
            "updated"  : result.modified_count,
            "unchanged": len(schemes) - result.upserted_count - result.modified_count,
        }
        log.info("[OK] %s -> New: %d | Updated: %d | Unchanged: %d",
                 source, stats["inserted"], stats["updated"], stats["unchanged"])
        return stats
    except PyMongoError as e:
        log.error("[FAIL] Bulk write (%s): %s", source, e)
        return {"inserted": 0, "updated": 0, "unchanged": 0}


def log_scrape_run(db, all_stats: dict, error: str = "") -> None:
    """Store audit record in scrape_logs collection."""
    try:
        db["scrape_logs"].insert_one({
            "run_at"  : datetime.now(timezone.utc),
            "stats"   : all_stats,
            "error"   : error,
            "sources" : ["builtin", "wikipedia"],
        })
    except PyMongoError:
        pass  # Non-critical


# ══════════════════════════════════════════════════════════
# MODULE 5 – MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════
def run_scraper():
    log.info("=" * 58)
    log.info("SATYA Scheme Updater started: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 58)

    client, collection = get_collection()
    db = client[DB_NAME]

    # Step 1: Ensure duplicate-safe index exists
    ensure_sparse_unique_index(collection)

    errors = ""
    total_stats = {"inserted": 0, "updated": 0, "unchanged": 0}

    # ── Step 2: Source A — Built-in curated dataset (always runs) ──
    log.info("--- Source A: Built-in curated dataset ---")
    log.info("  %d schemes loaded.", len(BUILTIN_SCHEMES))
    stats_a = upsert_to_mongodb(collection, BUILTIN_SCHEMES, source="builtin")
    for k in total_stats:
        total_stats[k] += stats_a[k]

    # ── Step 3: Source B — Wikipedia (highly reliable) ──
    try:
        wiki_schemes = scrape_wikipedia()
        stats_b = upsert_to_mongodb(collection, wiki_schemes, source="wikipedia")
        for k in total_stats:
            total_stats[k] += stats_b[k]
    except Exception as e:
        log.error("Source B (Wikipedia) failed: %s", e)
        errors += f"wiki:{e}; "

    # ── Step 4: Audit log ──
    log_scrape_run(db, total_stats, errors)
    client.close()

    log.info("-" * 58)
    log.info("TOTAL  ->  New: %d | Updated: %d | Unchanged: %d",
             total_stats["inserted"], total_stats["updated"], total_stats["unchanged"])
    log.info("Scraper finished. Full log: scraper.log")
    log.info("=" * 58)


if __name__ == "__main__":
    run_scraper()
