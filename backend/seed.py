import os
import sys
from pymongo import MongoClient
from faq_data import get_faqs

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def seed_database():
    print("Connecting to MongoDB...")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["Satya"]
    
    # 1. Clear existing data (Optional/Safe for Seeding)
    print("Purging existing schemes and FAQs...")
    db.schemes.delete_many({})
    db.faqs.delete_many({})
    
    # 2. Define Core Schemes
    schemes = [
        {
            "name": "Pradhan Mantri Awas Yojana",
            "description": "Provides subsidies to build or buy affordable houses for low-income families in India.",
            "official_website": "https://pmay-urban.gov.in/",
            "target_beneficiaries": "EWS, LIG, and MIG families without a pucca house.",
            "application_process": "Apply online through the PMAY portal or via local municipal offices.",
            "benefits": "Interest subsidies on housing loans and direct financial assistance for house construction.",
            "steps": "1. Visit the PMAY official website. 2. Choose 'Citizen Assessment'. 3. Enter Aadhaar details. 4. Fill out the application form. 5. Submit and track status.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 70,
                "max_income": 1800000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Ayushman Bharat",
            "description": "Universal health insurance providing ₹5 lakh per family per year for secondary and tertiary hospitalization.",
            "official_website": "https://pmjay.gov.in/",
            "target_beneficiaries": "Families listed in SECC 2011 and specific occupational workers.",
            "application_process": "Check eligibility on PM-JAY website and visit a Common Service Center (CSC).",
            "benefits": "Cashless and paperless access to health services for over 1,500 medical procedures.",
            "steps": "1. Search your name in PM-JAY database. 2. Verify identity at an empanelled hospital. 3. Get your Ayushman Card. 4. Use card for cashless treatment.",
            "state": "All India",
            "rules": {
                "min_age": 0,
                "max_age": 100,
                "max_income": 100000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Pradhan Mantri Kisan Samman Nidhi",
            "description": "Provides ₹6,000 per year in three equal installments to small and marginal farmers.",
            "official_website": "https://pmkisan.gov.in/",
            "target_beneficiaries": "Small and marginal farmer families with combined landholding of up to 2 hectares.",
            "application_process": "Register via the PM-Kisan portal or through local revenue officers.",
            "benefits": "Direct income support of ₹6,000 annually credited to bank accounts.",
            "steps": "1. Go to 'Farmers Corner' on PM-Kisan portal. 2. Click 'New Farmer Registration'. 3. Fill Aadhaar and land details. 4. Submit for verification.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 100,
                "max_income": 200000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"],
                "occupation": ["farmer"]
            }
        },
        {
            "name": "Pradhan Mantri Mudra Yojana",
            "description": "Provides loans up to ₹10 lakh for micro/small non-corporate, non-farm enterprises.",
            "official_website": "https://www.mudra.org.in/",
            "target_beneficiaries": "Small business owners and entrepreneurs.",
            "application_process": "Apply at any commercial bank, RRB, Small Finance Bank, or NBFC.",
            "benefits": "Collateral-free loans in three categories: Shishu, Kishor, and Tarun.",
            "steps": "1. Prepare a business plan. 2. Approach a bank branch. 3. Fill Mudra application form. 4. Submit ID, address, and business proof.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 65,
                "max_income": 10000000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Sukanya Samriddhi Yojana",
            "description": "Small deposit scheme for the girl child to meet her education and marriage expenses.",
            "official_website": "https://www.indiapost.gov.in/",
            "target_beneficiaries": "Parents/guardians of a girl child below 10 years.",
            "application_process": "Open an account at any Post Office or authorized branch of commercial banks.",
            "benefits": "High interest rates and tax savings under Section 80C.",
            "steps": "1. Visit a Post Office/Bank with the girl child's birth certificate. 2. Fill the SSY form. 3. Deposit the initial amount (min ₹250).",
            "state": "All India",
            "rules": {
                "min_age": 0,
                "max_age": 10,
                "max_income": 10000000,
                "allowed_categories": ["all"],
                "gender": ["female"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Stand Up India Scheme",
            "description": "Facilitates bank loans between ₹10 lakh and ₹1 crore to SC/ST and women entrepreneurs for greenfield enterprises.",
            "official_website": "https://www.standupmitra.in/",
            "target_beneficiaries": "SC/ST and Women entrepreneurs above 18-years of age.",
            "application_process": "Apply via the Standup Mitra portal or directly at a bank branch.",
            "benefits": "Access to high-value credit for starting new manufacturing, services, or trading units.",
            "steps": "1. Visit Standup Mitra portal. 2. Register as a trainee or direct borrower. 3. Choose your bank. 4. Submit project report and KYC docs.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 70,
                "max_income": 100000000,
                "allowed_categories": ["sc", "st"],
                "gender": ["female"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Atal Pension Yojana",
            "description": "Pension scheme for unorganized sector workers providing a guaranteed minimum pension of ₹1000 to ₹5000 after 60.",
            "official_website": "https://www.npscra.nsdl.co.in/",
            "target_beneficiaries": "Indian citizens in the unorganized sector aged 18 to 40.",
            "application_process": "Apply through any bank or Post Office where you have a savings account.",
            "benefits": "Fixed monthly pension for life and death benefit to the spouse/nominee.",
            "steps": "1. Visit your bank branch. 2. Fill the APY registration form. 3. Choose your pension amount. 4. Set up auto-debit for contributions.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 40,
                "max_income": 500000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Pradhan Mantri Jan Dhan Yojana",
            "description": "Universal access to banking with zero balance savings accounts and financial insurance.",
            "official_website": "https://pmjdy.gov.in/",
            "target_beneficiaries": "Indian citizens without a bank account.",
            "application_process": "Visit any bank branch or Business Correspondent (Bank Mitr) outlet.",
            "benefits": "Interest on deposits, ₹1 lakh accident insurance, RuPay debit card, and overdraft facility.",
            "steps": "1. Fill the PMJDY account opening form. 2. Submit Aadhaar or other valid KYC. 3. Collect your passbook and RuPay card.",
            "state": "All India",
            "rules": {
                "min_age": 10,
                "max_age": 100,
                "max_income": 10000000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "PM Ujjwala Yojana",
            "description": "Provides free LPG connections to women from BPL (Below Poverty Line) households.",
            "official_website": "https://www.pmuy.gov.in/",
            "target_beneficiaries": "Adult women of BPL families without an existing LPG connection.",
            "application_process": "Apply at the nearest LPG distributor or online via PMUY portal.",
            "benefits": "Free cylinder, pressure regulator, and installation with a deposit-free connection.",
            "steps": "1. Fill the application form. 2. Attach Aadhaar, BPL card, and bank details. 3. Submit to a local distributor. 4. Wait for KYC verification.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 100,
                "max_income": 100000,
                "allowed_categories": ["all"],
                "gender": ["female"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Skill India Mission",
            "description": "National mission to provide vocational training and industry-specific skills to Indian youth.",
            "official_website": "https://www.skillindia.gov.in/",
            "target_beneficiaries": "Indian youth seeking skill development and employment.",
            "application_process": "Register on the Skill India portal or visit a PM Kaushal Vikas Kendra (PMKK).",
            "benefits": "Free certification, industry exposure, and placement assistance.",
            "steps": "1. Register on the portal. 2. Browse available courses. 3. Find a nearby training center. 4. Enroll and attend classes.",
            "state": "All India",
            "rules": {
                "min_age": 14,
                "max_age": 45,
                "max_income": 10000000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"]
            }
        },
        {
            "name": "Beti Bachao Beti Padhao",
            "description": "A campaign to generate awareness and improve the efficiency of welfare services intended for girls.",
            "official_website": "https://wcd.nic.in/bbb-padhao",
            "target_beneficiaries": "Pregnant women, mothers, and girls across India.",
            "application_process": "Community-based awareness; benefits often linked to other schemes (e.g., SSY).",
            "benefits": "Focus on protecting girl children and ensuring their education through systemic changes.",
            "steps": "1. Contact your local Anganwadi/WCD office. 2. Inquire about BBBP linked district-level initiatives. 3. Register for education/nutrition support.",
            "state": "All India",
            "rules": {
                "min_age": 0,
                "max_age": 18,
                "max_income": 10000000,
                "allowed_categories": ["all"],
                "gender": ["female"],
                "special_category": ["all"]
            }
        },
        {
            "name": "PM Fasal Bima Yojana",
            "description": "Crop insurance scheme protecting farmers against crop loss due to natural calamities.",
            "official_website": "https://pmfby.gov.in/",
            "target_beneficiaries": "All farmers including sharecroppers and tenant farmers.",
            "application_process": "Apply via banks, CSCs, or the PMFBY online portal.",
            "benefits": "Financial support to farmers suffering crop loss and specialized risk coverage.",
            "steps": "1. Log in to PMFBY portal. 2. Register for the specific season (Kharif/Rabi). 3. Pay the low premium amount. 4. Upload land records and crop pics.",
            "state": "All India",
            "rules": {
                "min_age": 18,
                "max_age": 100,
                "max_income": 200000,
                "allowed_categories": ["all"],
                "gender": ["all"],
                "special_category": ["all"],
                "occupation": ["farmer"]
            }
        }
    ]
    
    # 3. Insert Schemes
    print(f"Inserting {len(schemes)} schemes...")
    db.schemes.insert_many(schemes)
    
    # 4. Insert FAQs from faq_data.py
    faqs_data = get_faqs()
    print(f"Inserting {len(faqs_data)} FAQs...")
    db.faqs.insert_many(faqs_data)
    
    print("Database seeding completed successfully!")
    client.close()

if __name__ == "__main__":
    seed_database()
