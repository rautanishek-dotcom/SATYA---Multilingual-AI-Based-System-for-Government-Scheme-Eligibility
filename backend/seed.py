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
    
    # 1. Clear existing data
    print("Purging existing schemes and FAQs...")
    db.schemes.delete_many({})
    db.faqs.delete_many({})
    
    # ================================================================
    # 2. Define Comprehensive Schemes
    #    - 25 Central (All India) schemes
    #    - 2 per state for: Maharashtra, Karnataka, Tamil Nadu,
    #      Andhra Pradesh, Telangana, Kerala, West Bengal, Bihar,
    #      Madhya Pradesh, Uttar Pradesh, Gujarat, Rajasthan,
    #      Odisha, Assam, Chhattisgarh, Punjab, Haryana, Jharkhand
    #    = 25 + (18 states x 2) = 25 + 36 = 61 schemes
    # ================================================================
    schemes = [

        # ============================================================
        # CENTRAL SCHEMES (All India) — 25 schemes
        # ============================================================
        {
            "name": "Pradhan Mantri Awas Yojana",
            "description": "Provides subsidies to build or buy affordable houses for low-income families in India.",
            "official_website": "https://pmaymis.gov.in/",
            "target_beneficiaries": "EWS, LIG, and MIG families without a pucca house.",
            "application_process": "Apply online through the PMAY portal or via local municipal offices.",
            "benefits": "Interest subsidies on housing loans and direct financial assistance for house construction.",
            "steps": "1. Visit the PMAY official website. 2. Choose 'Citizen Assessment'. 3. Enter Aadhaar details. 4. Fill out the application form. 5. Submit and track status.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 70, "max_income": 1800000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Ayushman Bharat",
            "description": "Universal health insurance providing ₹5 lakh per family per year for secondary and tertiary hospitalization.",
            "official_website": "https://pmjay.gov.in/",
            "target_beneficiaries": "Families listed in SECC 2011 and specific occupational workers.",
            "application_process": "Check eligibility on PM-JAY website and visit a Common Service Center (CSC).",
            "benefits": "Cashless access to health services for over 1,500 medical procedures.",
            "steps": "1. Visit pmjay.gov.in and check eligibility. 2. Verify identity at an empanelled hospital. 3. Get your Ayushman Card. 4. Use card for cashless treatment.",
            "state": "All India",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Pradhan Mantri Kisan Samman Nidhi",
            "description": "Provides ₹6,000 per year in three equal installments to small and marginal farmers.",
            "official_website": "https://pmkisan.gov.in/",
            "target_beneficiaries": "Small and marginal farmer families with landholdings.",
            "application_process": "Register via the PM-Kisan portal or through local revenue officers.",
            "benefits": "Direct income support of ₹6,000 annually credited to bank accounts.",
            "steps": "1. Go to 'Farmers Corner' on PM-Kisan portal. 2. Click 'New Farmer Registration'. 3. Fill Aadhaar and land details. 4. Submit for verification.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },
        {
            "name": "Pradhan Mantri Mudra Yojana",
            "description": "Provides loans up to ₹10 lakh for micro/small non-corporate, non-farm enterprises.",
            "official_website": "https://www.mudra.org.in/",
            "target_beneficiaries": "Small business owners and entrepreneurs.",
            "application_process": "Apply at any commercial bank, RRB, or NBFC.",
            "benefits": "Collateral-free loans categorized as Shishu (up to ₹50K), Kishor (up to ₹5L), and Tarun (up to ₹10L).",
            "steps": "1. Prepare a business plan. 2. Approach a bank branch. 3. Fill the Mudra application form. 4. Submit KYC and business proof.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 65, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Sukanya Samriddhi Yojana",
            "description": "Small deposit scheme for the girl child offering high interest rates to meet education and marriage expenses.",
            "official_website": "https://www.nsiindia.gov.in/",
            "target_beneficiaries": "Parents/guardians of a girl child below 10 years.",
            "application_process": "Open account at any Post Office or authorized bank branch.",
            "benefits": "High interest rates (currently 8.2%) and tax savings under Section 80C.",
            "steps": "1. Visit Post Office or Bank with girl child's birth certificate. 2. Fill the SSY application form. 3. Deposit the initial amount (minimum ₹250).",
            "state": "All India",
            "rules": {"min_age": 0, "max_age": 10, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Stand Up India Scheme",
            "description": "Facilitates bank loans between ₹10 lakh and ₹1 crore to SC/ST and women entrepreneurs for greenfield enterprises.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "SC/ST and Women entrepreneurs above 18 years of age.",
            "application_process": "Apply via the Standup Mitra portal or directly at a bank branch.",
            "benefits": "Access to high-value credit for starting new manufacturing, services, or trading units.",
            "steps": "1. Visit Standup Mitra portal. 2. Register as a borrower. 3. Choose your bank. 4. Submit project report and KYC documents.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 70, "max_income": 100000000, "allowed_categories": ["sc", "st"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Atal Pension Yojana",
            "description": "Guaranteed minimum pension of ₹1,000 to ₹5,000 per month for unorganized sector workers after age 60.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Indian citizens in the unorganized sector aged 18 to 40.",
            "application_process": "Apply through any bank or Post Office where you have a savings account.",
            "benefits": "Fixed monthly pension for life and death benefit to the spouse or nominee.",
            "steps": "1. Visit your bank branch. 2. Fill the APY registration form. 3. Choose your pension amount. 4. Set up auto-debit for contributions.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 40, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Pradhan Mantri Jan Dhan Yojana",
            "description": "Universal banking access with zero balance savings accounts, financial insurance, and RuPay debit card.",
            "official_website": "https://pmjdy.gov.in/",
            "target_beneficiaries": "Indian citizens without a bank account.",
            "application_process": "Visit any bank branch or Business Correspondent (Bank Mitr) outlet.",
            "benefits": "Interest on deposits, ₹1 lakh accident insurance, RuPay debit card, and overdraft facility up to ₹10,000.",
            "steps": "1. Fill the PMJDY account opening form. 2. Submit Aadhaar or other valid KYC. 3. Collect your passbook and RuPay card.",
            "state": "All India",
            "rules": {"min_age": 10, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Ujjwala Yojana",
            "description": "Provides free LPG connections to women from BPL (Below Poverty Line) households.",
            "official_website": "https://www.pmuy.gov.in/",
            "target_beneficiaries": "Adult women of BPL families without an existing LPG connection.",
            "application_process": "Apply at the nearest LPG distributor with required documents.",
            "benefits": "Free LPG cylinder, pressure regulator, and installation with a deposit-free connection.",
            "steps": "1. Fill the application form at LPG distributor. 2. Attach Aadhaar, BPL card, and bank details. 3. Wait for KYC verification. 4. Receive connection.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Skill India Mission",
            "description": "National mission to provide vocational training and industry-specific skills to Indian youth for better employment.",
            "official_website": "https://www.skillindia.gov.in/",
            "target_beneficiaries": "Indian youth seeking skill development and employment.",
            "application_process": "Register on the Skill India portal or visit a PM Kaushal Vikas Kendra (PMKK).",
            "benefits": "Free skill certification, industry exposure, and placement assistance.",
            "steps": "1. Register on the Skill India portal. 2. Browse available courses. 3. Find a nearby training center. 4. Enroll and attend classes.",
            "state": "All India",
            "rules": {"min_age": 14, "max_age": 45, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Beti Bachao Beti Padhao",
            "description": "A national campaign to generate awareness and improve the efficiency of welfare services intended for girls.",
            "official_website": "https://wcd.gov.in/",
            "target_beneficiaries": "Pregnant women, mothers, and girls across India.",
            "application_process": "Community-based awareness program; benefits are often linked to other schemes like SSY.",
            "benefits": "Focus on protecting the girl child and ensuring their education through systemic policy changes.",
            "steps": "1. Contact your local Anganwadi or WCD office. 2. Inquire about BBBP linked district-level initiatives. 3. Register for education and nutrition support.",
            "state": "All India",
            "rules": {"min_age": 0, "max_age": 18, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "PM Fasal Bima Yojana",
            "description": "Crop insurance scheme protecting farmers against crop loss due to natural calamities, pests, and diseases.",
            "official_website": "https://pmfby.gov.in/",
            "target_beneficiaries": "All farmers including sharecroppers and tenant farmers growing notified crops.",
            "application_process": "Apply via banks, Common Service Centers, or the PMFBY online portal.",
            "benefits": "Financial support to farmers suffering crop loss with very low premium rates.",
            "steps": "1. Log in to PMFBY portal. 2. Register your crop for the current season (Kharif/Rabi). 3. Pay the low premium amount. 4. Upload land records.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },
        {
            "name": "PM Vishwakarma Scheme",
            "description": "Supports traditional artisans and craftspeople with training, modern tools, and credit access.",
            "official_website": "https://pmvishwakarma.gov.in/",
            "target_beneficiaries": "Traditional artisans and craftspeople in 18 identified trades.",
            "application_process": "Register on the PM Vishwakarma portal using Aadhaar.",
            "benefits": "PM Vishwakarma Certificate and ID card, skill upgradation training, toolkit incentive of ₹15,000, and credit support up to ₹3 lakh.",
            "steps": "1. Registration on PM Vishwakarma portal. 2. Verification by Gram Panchayat/ULB. 3. Skill training enrollment. 4. Benefit disbursement.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM SVANidhi Scheme",
            "description": "Micro-credit facility for street vendors to restart their businesses after COVID-19 impact.",
            "official_website": "https://pmsvanidhi.mohua.gov.in/",
            "target_beneficiaries": "Street vendors with a valid Certificate of Vending or Letter of Recommendation.",
            "application_process": "Apply online on the PM SVANidhi portal or via local urban body offices.",
            "benefits": "Working capital loan up to ₹50,000 with 7% interest subsidy and digital payment incentives.",
            "steps": "1. Check eligibility on the portal. 2. Submit application with vendor ID. 3. Bank approval and disbursement.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Startup India",
            "description": "Government initiative to promote and support startups with tax benefits, funding, and simplified compliance.",
            "official_website": "https://www.startupindia.gov.in/",
            "target_beneficiaries": "Innovative startups and entrepreneurs across India.",
            "application_process": "Register on the Startup India portal and apply for DPIIT recognition.",
            "benefits": "3-year income tax exemption, self-certification under labour and environmental laws, and access to Fund of Funds.",
            "steps": "1. Incorporate your business entity. 2. Register on Startup India portal. 3. Apply for DPIIT recognition. 4. Avail benefits and funding.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 100000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Garib Kalyan Anna Yojana",
            "description": "Provides free food grains (5 kg per person per month) to over 80 crore NFSA beneficiaries.",
            "official_website": "https://nfsa.gov.in/",
            "target_beneficiaries": "Priority Households (PHH) and Antyodaya Anna Yojana (AAY) families.",
            "application_process": "Automatic for existing NFSA ration card holders. No separate application needed.",
            "benefits": "Free monthly ration of wheat, rice, and coarse grains through Fair Price Shops.",
            "steps": "1. Present your ration card at the nearest Fair Price Shop. 2. Verify identity through biometric/OTP. 3. Collect your free food grains.",
            "state": "All India",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Kaushal Vikas Yojana",
            "description": "Flagship scheme providing industry-relevant skill training to youth for employment and entrepreneurship.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Indian youth aged 15-45 seeking skill development.",
            "application_process": "Register at PMKVY training centers or on the Skill India Digital portal.",
            "benefits": "Free skill training, NSQF-aligned certification, and placement support.",
            "steps": "1. Find a PMKVY training center near you. 2. Enroll for a relevant course. 3. Complete training and assessment. 4. Receive certification.",
            "state": "All India",
            "rules": {"min_age": 15, "max_age": 45, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
            "description": "Affordable life insurance scheme providing ₹2 lakh death cover at a premium of just ₹436 per year.",
            "official_website": "https://jansuraksha.gov.in/",
            "target_beneficiaries": "Indian citizens aged 18-50 with a bank account.",
            "application_process": "Apply through your savings bank account with auto-debit consent.",
            "benefits": "Life insurance cover of ₹2 lakh in case of death due to any reason.",
            "steps": "1. Visit your bank branch or use net banking. 2. Give consent for auto-debit of ₹436/year. 3. Policy gets activated automatically.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 50, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Pradhan Mantri Suraksha Bima Yojana",
            "description": "Accidental death and disability insurance of ₹2 lakh at an ultra-low premium of ₹20 per year.",
            "official_website": "https://jansuraksha.gov.in/",
            "target_beneficiaries": "Indian citizens aged 18-70 with a bank account.",
            "application_process": "Apply through your savings bank account with auto-debit consent.",
            "benefits": "₹2 lakh for accidental death, ₹1 lakh for partial permanent disability.",
            "steps": "1. Visit your bank or give consent via net banking. 2. Annual premium of ₹20 auto-debited from account.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 70, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "National Scholarship Portal",
            "description": "One-stop digital platform for all scholarship schemes offered by Central and State governments.",
            "official_website": "https://scholarships.gov.in/",
            "target_beneficiaries": "Students from Class 1 to PhD level across India.",
            "application_process": "Register and apply online on the NSP portal during the application window.",
            "benefits": "Direct bank transfer of scholarship amount covering tuition fees, maintenance allowance, and more.",
            "steps": "1. Register on NSP with Aadhaar. 2. Fill the scholarship application form. 3. Upload required documents. 4. Submit for institutional verification.",
            "state": "All India",
            "rules": {"min_age": 6, "max_age": 35, "max_income": 250000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Shram Yogi Maandhan",
            "description": "Voluntary pension scheme for unorganized workers ensuring ₹3,000 monthly pension after age 60.",
            "official_website": "https://maandhan.in/",
            "target_beneficiaries": "Unorganized sector workers (street vendors, domestic workers, rickshaw pullers, etc.) aged 18-40.",
            "application_process": "Register at the nearest Common Service Center (CSC) with Aadhaar and bank details.",
            "benefits": "Guaranteed monthly pension of ₹3,000 after attaining the age of 60.",
            "steps": "1. Visit nearest CSC. 2. Provide Aadhaar number and bank account details. 3. Choose monthly contribution amount. 4. Enrollment confirmation.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 40, "max_income": 180000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Kisan Credit Card Scheme",
            "description": "Provides farmers with timely and hassle-free access to institutional credit for cultivation and other needs.",
            "official_website": "https://www.myscheme.gov.in/schemes/kcc",
            "target_beneficiaries": "All farmers, sharecroppers, tenant farmers, and fisheries/animal husbandry practitioners.",
            "application_process": "Apply at any commercial bank, cooperative bank, or Regional Rural Bank (RRB).",
            "benefits": "Short-term credit at subsidized interest rates (4% effective rate) with flexible repayment.",
            "steps": "1. Visit your bank branch with land ownership documents. 2. Fill the KCC application form. 3. Bank processes and issues the card.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 75, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },
        {
            "name": "Swachh Bharat Mission",
            "description": "Nationwide cleanliness campaign providing financial aid for toilet construction and solid waste management.",
            "official_website": "https://swachhbharatmission.gov.in/",
            "target_beneficiaries": "Rural and urban households without proper sanitation facilities.",
            "application_process": "Apply online on the SBM portal or through local Gram Panchayat/Municipality.",
            "benefits": "₹12,000 incentive for construction of individual household toilets in rural areas.",
            "steps": "1. Apply on the SBM(G) portal or contact Panchayat. 2. Upload photos of construction site. 3. Get approval and incentive after completion.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Poshan Scheme",
            "description": "Provides hot cooked nutritious meals to children in government and government-aided schools.",
            "official_website": "https://pmposhan.education.gov.in/",
            "target_beneficiaries": "Students of Classes 1-8 in government and government-aided schools.",
            "application_process": "Automatic for all enrolled students. No separate application required.",
            "benefits": "Free nutritious mid-day meals improving nutrition, enrollment, and attendance.",
            "steps": "1. Enroll your child in a government school. 2. Meals served daily during school hours.",
            "state": "All India",
            "rules": {"min_age": 6, "max_age": 14, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "PM Surya Ghar Muft Bijli Yojana",
            "description": "Provides subsidies for rooftop solar installations to give free electricity (up to 300 units/month) to households.",
            "official_website": "https://pmsuryaghar.gov.in/",
            "target_beneficiaries": "All Indian households with suitable rooftop space.",
            "application_process": "Apply online on the PM Surya Ghar portal with electricity bill details.",
            "benefits": "Central subsidy of ₹30,000 to ₹78,000 for solar panel installation and free electricity generation.",
            "steps": "1. Register on pmsuryaghar.gov.in. 2. Select a registered vendor. 3. Install rooftop solar system. 4. Submit completion report and claim subsidy.",
            "state": "All India",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # ============================================================
        # STATE SCHEMES — 2 per state (18 states × 2 = 36 schemes)
        # ============================================================

        # --- MAHARASHTRA (2) ---
        {
            "name": "Majhi Kanya Bhagyashree",
            "description": "Maharashtra government scheme to improve the girl child ratio by providing financial assistance for education.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Girl children born in Maharashtra families (up to 2 girls per family).",
            "application_process": "Apply at local Anganwadi center, CDPO office, or through the WCD department.",
            "benefits": "Financial assistance linked to girl child's education milestones and a bank deposit at birth.",
            "steps": "1. Register birth at local hospital. 2. Visit nearest Anganwadi/CDPO office. 3. Submit birth certificate, Aadhaar, and bank details. 4. Track benefit disbursement.",
            "state": "Maharashtra",
            "rules": {"min_age": 0, "max_age": 18, "max_income": 750000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Mahatma Phule Jan Arogya Yojana",
            "description": "Maharashtra's health insurance scheme providing cashless treatment for over 1,000 medical procedures.",
            "official_website": "https://www.jeevandayee.gov.in/",
            "target_beneficiaries": "Maharashtra families holding Orange, Yellow, or White ration cards.",
            "application_process": "No prior registration needed. Present ration card at any empanelled hospital.",
            "benefits": "Cashless medical treatment covering surgeries, therapies, and follow-up care up to ₹2.5 lakh per family per year.",
            "steps": "1. Visit any empanelled hospital with your ration card. 2. Identity verification at the Arogya Mitra desk. 3. Avail cashless treatment.",
            "state": "Maharashtra",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- KARNATAKA (2) ---
        {
            "name": "Karnataka Gruha Lakshmi Scheme",
            "description": "Provides ₹2,000 monthly direct cash transfer to women heads of households in Karnataka.",
            "official_website": "https://sevasindhuservices.karnataka.gov.in/",
            "target_beneficiaries": "Women who are the head of the family in Karnataka with a valid ration card.",
            "application_process": "Apply online through the Seva Sindhu portal or at designated camps.",
            "benefits": "₹2,000 per month transferred directly to the beneficiary's bank account.",
            "steps": "1. Visit Seva Sindhu portal or camp. 2. Submit Aadhaar and Ration card details. 3. Verification by authorities. 4. Monthly DBT to your bank account.",
            "state": "Karnataka",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Karnataka Yuva Nidhi Scheme",
            "description": "Provides monthly unemployment stipend to recent graduates and diploma holders in Karnataka.",
            "official_website": "https://sevasindhuservices.karnataka.gov.in/",
            "target_beneficiaries": "Unemployed graduates and diploma holders from Karnataka who have not found a job within 6 months.",
            "application_process": "Register on the Seva Sindhu 2.0 portal with graduation certificate.",
            "benefits": "Monthly stipend of ₹3,000 (graduates) or ₹1,500 (diploma holders) for up to 2 years.",
            "steps": "1. Complete your degree or diploma. 2. Wait for 6 months after passing. 3. Register on Seva Sindhu portal. 4. Submit verification documents.",
            "state": "Karnataka",
            "rules": {"min_age": 18, "max_age": 30, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- TAMIL NADU (2) ---
        {
            "name": "Tamil Nadu Kalaignar Magalir Urimai Thogai",
            "description": "Monthly income support of ₹1,000 for eligible women heads of families in Tamil Nadu.",
            "official_website": "https://kmut.tn.gov.in/",
            "target_beneficiaries": "Women heads of families in Tamil Nadu with annual family income below limit.",
            "application_process": "Apply at special enrollment camps or through the official KMUT portal.",
            "benefits": "₹1,000 per month directly transferred to eligible women's bank accounts.",
            "steps": "1. Check eligibility using ration card. 2. Visit enrollment camp or apply online. 3. Submit Aadhaar and bank details. 4. Receive monthly DBT.",
            "state": "Tamil Nadu",
            "rules": {"min_age": 21, "max_age": 100, "max_income": 250000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Tamil Nadu Chief Minister Health Insurance",
            "description": "Comprehensive health insurance for Tamil Nadu families providing cashless treatment at empanelled hospitals.",
            "official_website": "https://www.cmchistn.com/",
            "target_beneficiaries": "Tamil Nadu families with income below ₹1.2 lakh per year.",
            "application_process": "Present family card or Aadhaar at empanelled hospitals for cashless treatment.",
            "benefits": "Health insurance cover up to ₹5 lakh per family per year covering 1,027 procedures.",
            "steps": "1. Visit any empanelled hospital. 2. Show your family/ration card and Aadhaar. 3. Get verified by the hospital desk. 4. Avail cashless treatment.",
            "state": "Tamil Nadu",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 120000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- ANDHRA PRADESH (2) ---
        {
            "name": "AP Amma Vodi Scheme",
            "description": "Financial assistance of ₹15,000 per year to mothers who send their children to school in Andhra Pradesh.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Mothers/guardians from eligible families in AP whose children attend school with 75%+ attendance.",
            "application_process": "Automatic verification through schools. No separate application needed.",
            "benefits": "₹15,000 annual grant directly credited to mother's bank account.",
            "steps": "1. Ensure child has 75%+ school attendance. 2. Complete EKYC at school. 3. Amount credited via DBT.",
            "state": "Andhra Pradesh",
            "rules": {"min_age": 20, "max_age": 60, "max_income": 100000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "AP YSR Rythu Bharosa",
            "description": "Investment support scheme for farmers in Andhra Pradesh providing direct financial assistance.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "All eligible farmers in Andhra Pradesh with land holdings.",
            "application_process": "Automatic based on land records in the WebLand portal. No separate application.",
            "benefits": "₹13,500 per year (₹7,500 from state + ₹6,000 from PM-KISAN) in seasonal installments.",
            "steps": "1. Ensure land records are updated. 2. Link Aadhaar with bank account. 3. Amount automatically credited before each crop season.",
            "state": "Andhra Pradesh",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },

        # --- TELANGANA (2) ---
        {
            "name": "Telangana Rythu Bandhu Scheme",
            "description": "Investment support of ₹10,000 per acre per year for all land-owning farmers in Telangana.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "All land-owning farmers registered in the Dharani portal in Telangana.",
            "application_process": "Automatic based on Dharani land records. No separate application required.",
            "benefits": "₹10,000 per acre per year (₹5,000 each in Kharif and Rabi seasons) for investment support.",
            "steps": "1. Ensure land is registered in Dharani portal. 2. Link Aadhaar with bank account. 3. Amount auto-disbursed before each season.",
            "state": "Telangana",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },
        {
            "name": "Telangana Kalyana Lakshmi Pathakam",
            "description": "One-time financial assistance of ₹1,00,116 to eligible unmarried girls at the time of marriage in Telangana.",
            "official_website": "https://telanganaepass.cgg.gov.in/",
            "target_beneficiaries": "Unmarried girls from BPL families in Telangana (age 18+).",
            "application_process": "Apply through the ePASS portal before marriage with required documents.",
            "benefits": "One-time grant of ₹1,00,116 deposited directly to the bride's bank account.",
            "steps": "1. Register on ePASS portal. 2. Upload required documents. 3. Submit application before marriage. 4. Benefit credited after verification.",
            "state": "Telangana",
            "rules": {"min_age": 18, "max_age": 35, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },

        # --- KERALA (2) ---
        {
            "name": "Kerala LIFE Mission",
            "description": "Comprehensive housing scheme to provide homes to all homeless families and those living in unsafe shelters in Kerala.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Homeless families and those living in dilapidated houses in Kerala.",
            "application_process": "Selection through Gram Sabha identification and survey-based beneficiary lists.",
            "benefits": "Financial assistance for constructing a new house (₹4 lakh for landless, ₹6 lakh for land-owning homeless).",
            "steps": "1. Identification through survey. 2. Selection by Gram Sabha. 3. Approval and fund allocation. 4. House construction.",
            "state": "Kerala",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Kerala Snehapoorvam Scheme",
            "description": "Monthly scholarship for orphan children and children of parents with critical illness in Kerala.",
            "official_website": "https://socialsecuritymission.gov.in/",
            "target_beneficiaries": "Orphan children and children of critically ill parents in Kerala aged 5-18.",
            "application_process": "Apply through the school or on the Kerala Social Security Mission E-Suraksha portal.",
            "benefits": "Monthly scholarship from ₹300 to ₹500 depending on age and education level.",
            "steps": "1. Submit application to school or local body. 2. Attach death/medical certificates. 3. Verification by authorities. 4. Monthly scholarship disbursement.",
            "state": "Kerala",
            "rules": {"min_age": 5, "max_age": 18, "max_income": 100000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- WEST BENGAL (2) ---
        {
            "name": "WB Lakshmir Bhandar",
            "description": "Monthly income support for women heads of families in West Bengal for social security and empowerment.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Women aged 25-60 in West Bengal families.",
            "application_process": "Apply at Duare Sarkar camps or through the Social Security portal.",
            "benefits": "Monthly stipend of ₹1,000 for SC/ST women and ₹500 for General category women.",
            "steps": "1. Collect form at Duare Sarkar camp. 2. Submit with Aadhaar, bank details, and Swasthya Sathi card. 3. Verification. 4. Monthly bank credit.",
            "state": "West Bengal",
            "rules": {"min_age": 25, "max_age": 60, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "WB Kanyashree Prakalpa",
            "description": "Conditional cash transfer scheme to support education and delay marriage of girl children in West Bengal.",
            "official_website": "https://wbkanyashree.gov.in/",
            "target_beneficiaries": "Girls aged 13-18 from economically disadvantaged families in West Bengal.",
            "application_process": "Apply through the school or Kanyashree portal with required documents.",
            "benefits": "Annual scholarship of ₹750 and one-time grant of ₹25,000 at age 18 (if unmarried and in education).",
            "steps": "1. Enroll through school. 2. Submit income certificate and ID proof. 3. Receive annual scholarship. 4. One-time grant at age 18.",
            "state": "West Bengal",
            "rules": {"min_age": 13, "max_age": 18, "max_income": 120000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },

        # --- BIHAR (2) ---
        {
            "name": "Bihar Mukhyamantri Kanya Utthan Yojana",
            "description": "Comprehensive scheme providing financial aid to girls in Bihar from birth to graduation for education and empowerment.",
            "official_website": "https://medhasoft.bihar.gov.in/",
            "target_beneficiaries": "Girl students in Bihar at various education milestones.",
            "application_process": "Apply through school or the Medhasoft/E-Kalyan portal after passing 12th or Graduation.",
            "benefits": "Total benefit of ₹50,000+ per girl across milestones from birth to graduation.",
            "steps": "1. Register birth. 2. School enrollment verification. 3. Apply on Medhasoft portal after passing 12th or Graduation. 4. Amount credited to bank.",
            "state": "Bihar",
            "rules": {"min_age": 0, "max_age": 25, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Bihar Student Credit Card Scheme",
            "description": "Education loan up to ₹4 lakh at subsidized interest for Bihar students pursuing higher education.",
            "official_website": "https://www.7nishchay-yuvaupmission.bihar.gov.in/",
            "target_beneficiaries": "Students in Bihar who have passed 12th and seek to pursue higher education.",
            "application_process": "Register on the 7 Nishchay Yuva Upmission portal and visit the DRCC.",
            "benefits": "Loan up to ₹4 lakh at 4% interest (0% for female, SC/ST, and differently-abled students). No collateral required.",
            "steps": "1. Register online on 7 Nishchay portal. 2. Visit DRCC with documents. 3. Loan processing and approval. 4. Amount disbursed to institution.",
            "state": "Bihar",
            "rules": {"min_age": 18, "max_age": 25, "max_income": 1000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- MADHYA PRADESH (2) ---
        {
            "name": "MP Ladli Laxmi Yojana",
            "description": "Financial support for girl children in Madhya Pradesh with milestone-based payments totaling ₹1.43 lakh.",
            "official_website": "https://ladlilaxmi.mp.gov.in/",
            "target_beneficiaries": "Girl children born in Madhya Pradesh families below poverty line.",
            "application_process": "Register on the Ladli Laxmi portal within one year of birth.",
            "benefits": "₹1,43,000 in milestone payments from birth to age 21 linked to education and non-marriage conditions.",
            "steps": "1. Register within 1 year of birth on the portal. 2. Submit birth certificate and domicile. 3. Successive milestone claims at Class 6, 9, 12, and Graduation.",
            "state": "Madhya Pradesh",
            "rules": {"min_age": 0, "max_age": 21, "max_income": 500000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "MP Mukhyamantri Yuva Internship Yojana",
            "description": "Professional training and monthly stipend for unemployed graduates in Madhya Pradesh government departments.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Unemployed graduates in Madhya Pradesh aged 21-30.",
            "application_process": "Register on the Yuva Internship portal and apply for available internships.",
            "benefits": "₹8,000 monthly stipend during internship and hands-on government department experience.",
            "steps": "1. Complete graduation. 2. Register on the portal. 3. Apply for internships. 4. Attend interview and join if selected.",
            "state": "Madhya Pradesh",
            "rules": {"min_age": 21, "max_age": 30, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- UTTAR PRADESH (2) ---
        {
            "name": "UP Kanya Sumangala Yojana",
            "description": "Financial support of ₹15,000 in six installments for girl children in Uttar Pradesh from birth to graduation.",
            "official_website": "https://mksy.up.gov.in/",
            "target_beneficiaries": "Girls born in UP families with annual income below ₹3 lakh.",
            "application_process": "Apply online on the official MKSY portal with required documents.",
            "benefits": "₹15,000 in six milestones: at birth, vaccination, Class 1, Class 6, Class 9, and Graduation.",
            "steps": "1. Register on mksy.up.gov.in. 2. Submit girl child's birth certificate. 3. Successive claims at each milestone. 4. Amount credited to bank.",
            "state": "Uttar Pradesh",
            "rules": {"min_age": 0, "max_age": 25, "max_income": 300000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "UP Berojgari Bhatta",
            "description": "Monthly unemployment allowance for educated unemployed youth in Uttar Pradesh registered on the Sewayojan portal.",
            "official_website": "https://sewayojan.up.nic.in/",
            "target_beneficiaries": "Educated unemployed youth in UP aged 18-35 with at least 12th pass qualification.",
            "application_process": "Register as a job seeker on the Sewayojan portal and apply for the allowance.",
            "benefits": "Monthly allowance of ₹1,000-₹1,500 for a period of time while seeking employment.",
            "steps": "1. Register on sewayojan.up.nic.in. 2. Complete profile with education details. 3. Apply for Berojgari Bhatta. 4. Verification and disbursement.",
            "state": "Uttar Pradesh",
            "rules": {"min_age": 18, "max_age": 35, "max_income": 300000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- GUJARAT (2) ---
        {
            "name": "Gujarat Vahali Dikri Yojana",
            "description": "Welfare scheme for girl children in Gujarat providing milestone-based financial assistance up to ₹1.10 lakh.",
            "official_website": "https://wcd.gujarat.gov.in/",
            "target_beneficiaries": "First two girl children in Gujarat families with annual income below ₹2 lakh.",
            "application_process": "Submit physical application form at the local ICDS office or CDPO.",
            "benefits": "₹4,000 at Class 1, ₹6,000 at Class 9, and ₹1 lakh at age 18 (if unmarried).",
            "steps": "1. Apply within 1 year of birth at CDPO office. 2. Submit birth certificate and family income proof. 3. Update status at Class 1 and 9 milestones.",
            "state": "Gujarat",
            "rules": {"min_age": 0, "max_age": 18, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Gujarat Mukhyamantri Yuva Swavalamban Yojana",
            "description": "Scholarship covering up to 50% tuition fees for meritorious students pursuing professional courses in Gujarat.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Merit students in Gujarat with 80+ percentile in 12th and family income below ₹6 lakh.",
            "application_process": "Apply online on the MYSY portal during the application window.",
            "benefits": "Tuition fee waiver up to 50% for engineering, medical, and other professional courses.",
            "steps": "1. Score 80+ percentile in class 12th. 2. Register on mysy.guj.nic.in. 3. Upload documents. 4. Get verified by institution.",
            "state": "Gujarat",
            "rules": {"min_age": 17, "max_age": 25, "max_income": 600000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- RAJASTHAN (2) ---
        {
            "name": "Rajasthan Chiranjeevi Yojana",
            "description": "Universal health insurance scheme providing cashless treatment up to ₹25 lakh for all Rajasthan residents.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "All families of Rajasthan state.",
            "application_process": "Register on the SSO portal or visit an e-Mitra center.",
            "benefits": "Cashless health insurance cover of up to ₹25 lakh per family per year at empanelled hospitals.",
            "steps": "1. Login to SSO portal (sso.rajasthan.gov.in). 2. Register family for Chiranjeevi. 3. Download Chiranjeevi card. 4. Avail cashless treatment at hospitals.",
            "state": "Rajasthan",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Rajasthan Palanhar Yojana",
            "description": "Financial assistance for care, education, and upbringing of orphan or destitute children in Rajasthan.",
            "official_website": "https://sje.rajasthan.gov.in/",
            "target_beneficiaries": "Guardians (Palanhars) of orphan, destitute, or abandoned children in Rajasthan.",
            "application_process": "Apply through the Social Justice & Empowerment Department portal or local office.",
            "benefits": "Monthly assistance of ₹500 (age 0-5) and ₹1,000 (age 6-18) plus ₹2,000/year for clothing and shoes.",
            "steps": "1. Contact local SJE office. 2. Submit orphan certificate or relevant proof. 3. Fill application form. 4. Monthly assistance credited.",
            "state": "Rajasthan",
            "rules": {"min_age": 0, "max_age": 18, "max_income": 120000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- ODISHA (2) ---
        {
            "name": "Odisha KALIA Yojana",
            "description": "Financial assistance for cultivation and livelihood support for small and marginal farmers in Odisha.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Small/marginal farmers, landless agricultural laborers, and vulnerable families in Odisha.",
            "application_process": "Apply through the KALIA portal or Common Service Centers.",
            "benefits": "₹10,000 per year to small/marginal farmers, and ₹12,500 per year to vulnerable families.",
            "steps": "1. Submit form on KALIA portal or at CSC. 2. Gram Panchayat verification. 3. Approval by district officials. 4. Amount credited to bank in two installments.",
            "state": "Odisha",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"], "occupation": ["farmer"]}
        },
        {
            "name": "Odisha Madhu Babu Pension Yojana",
            "description": "Monthly social security pension for elderly, widows, and differently-abled persons in Odisha.",
            "official_website": "https://ssepd.odisha.gov.in/",
            "target_beneficiaries": "Elderly (60+), widows, and differently-abled persons in Odisha from BPL families.",
            "application_process": "Apply at the local Jana Seva Kendra or through the SSEPD portal.",
            "benefits": "Monthly pension of ₹500 to ₹900 depending on age and category.",
            "steps": "1. Visit Jana Seva Kendra. 2. Fill application form with proof documents. 3. Verification by inspector. 4. Pension card issuance and monthly credit.",
            "state": "Odisha",
            "rules": {"min_age": 60, "max_age": 100, "max_income": 40000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- ASSAM (2) ---
        {
            "name": "Assam Orunodoi Scheme",
            "description": "Monthly financial assistance of ₹1,250 to women from economically weaker households in Assam.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Women nominees of eligible families in Assam (preference to widows, separated wives, and unmarried women).",
            "application_process": "Selection through Village Council Development Committees (VCDCs) and Gaon Panchayats.",
            "benefits": "₹1,250 per month transferred to the woman nominee's bank account.",
            "steps": "1. Identification by Gaon Panchayat. 2. Beneficiary list publication. 3. Verification by VCDC. 4. Monthly DBT to bank account.",
            "state": "Assam",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Assam Pragyan Bharati Scheme",
            "description": "Merit-based scooter and financial incentive for high-performing students in Assam.",
            "official_website": "https://directorateofhighereducation.assam.gov.in/",
            "target_beneficiaries": "Meritorious students who scored well in HSLC and HS examinations in Assam.",
            "application_process": "Automatic selection based on board examination results via Directorate of Higher Education.",
            "benefits": "Free scooty or financial incentive for meritorious students.",
            "steps": "1. Appear for HSLC/HS exam. 2. Merit list prepared by education directorate. 3. Distribution ceremony. 4. Receive benefit.",
            "state": "Assam",
            "rules": {"min_age": 14, "max_age": 25, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- CHHATTISGARH (2) ---
        {
            "name": "Chhattisgarh Mahtari Vandan Yojana",
            "description": "Monthly income support of ₹1,000 for married women in Chhattisgarh for financial empowerment.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Married women aged 21-60 in Chhattisgarh.",
            "application_process": "Apply through the official portal or at local enrollment camps.",
            "benefits": "₹12,000 per year (₹1,000/month) directly transferred to beneficiary bank account.",
            "steps": "1. Visit portal or enrollment camp. 2. Submit marriage certificate, Aadhaar, and bank details. 3. EKYC verification. 4. Monthly DBT.",
            "state": "Chhattisgarh",
            "rules": {"min_age": 21, "max_age": 60, "max_income": 300000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Chhattisgarh Godhan Nyay Yojana",
            "description": "Government procures cow dung from livestock owners to promote organic farming and vermicompost production.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Cattle rearers and livestock owners in Chhattisgarh.",
            "application_process": "Sell cow dung at designated Gauthans (cattle shelters) across the state.",
            "benefits": "Government purchases cow dung at ₹2 per kg, providing additional income to cattle owners.",
            "steps": "1. Register at the nearest Gauthan. 2. Bring cow dung regularly. 3. Get weighed and paid. 4. Payment credited to bank account.",
            "state": "Chhattisgarh",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- PUNJAB (2) ---
        {
            "name": "Punjab Ashirwad Scheme",
            "description": "Financial grant of ₹51,000 for the marriage of daughters from economically weaker families in Punjab.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "SC/ST/BC and economically weaker families in Punjab.",
            "application_process": "Apply at the block office or District Social Security Office.",
            "benefits": "One-time grant of ₹51,000 for marriage expenses.",
            "steps": "1. Apply at block office before or during marriage. 2. Submit income certificate and caste certificate. 3. Verification by authorities. 4. Disbursement to bank account.",
            "state": "Punjab",
            "rules": {"min_age": 18, "max_age": 100, "max_income": 32000, "allowed_categories": ["sc", "st", "bc"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Punjab Atta Dal Scheme",
            "description": "Subsidized food grains (wheat flour and dal) to eligible BPL families in Punjab.",
            "official_website": "https://epos.punjab.gov.in/",
            "target_beneficiaries": "BPL families with valid ration cards in Punjab.",
            "application_process": "Automatic for ration card holders. Collect from designated Fair Price Shops.",
            "benefits": "Wheat flour at ₹2/kg and dal at ₹20/kg for eligible families.",
            "steps": "1. Visit your designated Fair Price Shop. 2. Present ration card. 3. Biometric verification. 4. Collect subsidized food grains.",
            "state": "Punjab",
            "rules": {"min_age": 0, "max_age": 100, "max_income": 50000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- HARYANA (2) ---
        {
            "name": "Haryana Ladli Social Security Allowance",
            "description": "Monthly pension for parents in Haryana who have only girl children and no son.",
            "official_website": "https://socialjusticehry.gov.in/",
            "target_beneficiaries": "Parents aged 45-60 in Haryana with only daughters (no son).",
            "application_process": "Apply at the local District Welfare Officer's office or through the Social Justice portal.",
            "benefits": "Monthly pension of ₹2,750 per family to support parents with only daughters.",
            "steps": "1. Visit DWO office. 2. Submit proof of children and income certificate. 3. Verification. 4. Monthly pension credited.",
            "state": "Haryana",
            "rules": {"min_age": 45, "max_age": 60, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },
        {
            "name": "Haryana Mukhyamantri Parivar Samridhi Yojana",
            "description": "Social security scheme ensuring life insurance, pension, and accidental cover for all eligible families in Haryana.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Families in Haryana with annual income below ₹1.8 lakh and land below 5 acres.",
            "application_process": "Apply through Antyodaya Saral Centers or Common Service Centers.",
            "benefits": "Auto-enrollment in PMJJBY, PMSBY, PM-SYM, and PM Kisan schemes with premium paid by state government.",
            "steps": "1. Visit Antyodaya Saral Kendra. 2. Submit family details and Parivar Pehchan Patra. 3. Choose benefit option. 4. Enrollment confirmation.",
            "state": "Haryana",
            "rules": {"min_age": 18, "max_age": 60, "max_income": 180000, "allowed_categories": ["all"], "gender": ["all"], "special_category": ["all"]}
        },

        # --- JHARKHAND (2) ---
        {
            "name": "Jharkhand Mukhyamantri Sukanya Yojana",
            "description": "Financial milestone-based assistance for girls from economically weaker families in Jharkhand.",
            "official_website": "https://www.myscheme.gov.in/",
            "target_beneficiaries": "Girl children from BPL/SECC families in Jharkhand.",
            "application_process": "Apply at local Anganwadi center or block office with birth certificate.",
            "benefits": "Multiple installments from birth to Class 12 completion totaling significant financial support.",
            "steps": "1. Register at Anganwadi center after birth. 2. Submit documents at block office. 3. Claim installments at education milestones.",
            "state": "Jharkhand",
            "rules": {"min_age": 0, "max_age": 18, "max_income": 100000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
        {
            "name": "Jharkhand Savitri Bai Phule Kishori Samriddhi Yojana",
            "description": "Financial incentive for girls studying in Classes 8-12 in Jharkhand to promote their education and empowerment.",
            "official_website": "https://jharkhand.gov.in/",
            "target_beneficiaries": "Girls enrolled in Classes 8 to 12 in government schools in Jharkhand from SECC families.",
            "application_process": "Apply through school or block office with required documents.",
            "benefits": "₹2,500 in Class 8, ₹5,000 in Class 9-12, and ₹20,000 at age 18 if unmarried.",
            "steps": "1. Enroll in government school. 2. Submit application through school. 3. Verification by block office. 4. Amount credited to bank/post office account.",
            "state": "Jharkhand",
            "rules": {"min_age": 13, "max_age": 19, "max_income": 100000, "allowed_categories": ["all"], "gender": ["female"], "special_category": ["all"]}
        },
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
