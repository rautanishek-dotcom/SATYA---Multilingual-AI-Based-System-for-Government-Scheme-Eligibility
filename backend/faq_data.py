# FAQ data stored in English only for the transformation pipeline.
# Each FAQ has a 'scheme' tag matching scheme names in the database for precise matching.

ENGLISH_FAQS = [
    # ===== GENERAL & ABOUT SATYA (10) =====
    {"question": "What is SATYA?", "answer": "SATYA (System for AI-based Transparency and Yielding Assistance) is an AI-powered platform helping Indian citizens discover schemes, verify documents, and check eligibility instantly.", "category": "general", "scheme": ""},
    {"question": "How to check eligibility?", "answer": "Fill your profile, verify documents with AI, and get personalized scheme lists instantly.", "category": "general", "scheme": ""},
    {"question": "How does document verification work?", "answer": "Our AI uses neural OCR and QR scanning to verify Aadhaar, PAN, and Income Certificates in real-time.", "category": "general", "scheme": ""},
    {"question": "Is my data safe with SATYA?", "answer": "Yes, SATYA uses end-to-end encryption and does not store sensitive document images after verification.", "category": "general", "scheme": ""},
    {"question": "What documents can be verified?", "answer": "Aadhaar, PAN Card, Income Certificate, and Caste Certificate can be verified using our AI scanner.", "category": "general", "scheme": ""},
    {"question": "How to use the chatbot?", "answer": "Type your question or use suggested chips. The chatbot automatically detects your language.", "category": "general", "scheme": ""},
    {"question": "What happens after document verification?", "answer": "Your eligibility score updates and the system recommends schemes tailored to your profile.", "category": "general", "scheme": ""},
    {"question": "How to use the QR scanner?", "answer": "Allow camera access, then point your camera at the QR code on your Aadhaar or PAN card.", "category": "general", "scheme": ""},
    {"question": "Which languages does SATYA support?", "answer": "SATYA supports 9 languages: English, Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Gujarati, and Malayalam.", "category": "general", "scheme": ""},
    {"question": "Does SATYA charge any fee?", "answer": "No, SATYA is completely free for all Indian citizens.", "category": "general", "scheme": ""},

    # ===== PRADHAN MANTRI AWAS YOJANA (5) =====
    {"question": "What is Pradhan Mantri Awas Yojana?", "answer": "PMAY provides subsidies to build or buy affordable houses for low-income families.", "category": "housing", "scheme": "Pradhan Mantri Awas Yojana"},
    {"question": "Who is eligible for PMAY?", "answer": "Families with annual income below ₹6 lakh (EWS) or ₹18 lakh (LIG/MIG) without a pucca house.", "category": "housing", "scheme": "Pradhan Mantri Awas Yojana"},
    {"question": "How to apply for PMAY?", "answer": "Apply through the official PMAY portal or local municipal/panchayat office with Aadhaar and income proof.", "category": "housing", "scheme": "Pradhan Mantri Awas Yojana"},
    {"question": "What is the subsidy under PMAY?", "answer": "Interest subsidy of 6.5% for EWS/LIG, 4% for MIG-I, and 3% for MIG-II under CLSS.", "category": "housing", "scheme": "Pradhan Mantri Awas Yojana"},
    {"question": "What documents are needed for PMAY?", "answer": "Aadhaar Card, Income Certificate, address proof, bank details, and proof of no pucca house ownership.", "category": "housing", "scheme": "Pradhan Mantri Awas Yojana"},

    # ===== AYUSHMAN BHARAT (5) =====
    {"question": "What is Ayushman Bharat?", "answer": "Provides healthcare insurance of ₹5 lakh per family per year for hospitalization.", "category": "health", "scheme": "Ayushman Bharat"},
    {"question": "How to get Ayushman Card?", "answer": "Check eligibility on PM-JAY website and visit a CSC to get your golden card printed.", "category": "health", "scheme": "Ayushman Bharat"},
    {"question": "Who is eligible for Ayushman Bharat?", "answer": "Families listed in SECC 2011 database and workers in specific occupational categories.", "category": "health", "scheme": "Ayushman Bharat"},
    {"question": "Which hospitals accept Ayushman Bharat?", "answer": "All government hospitals and empanelled private hospitals across India.", "category": "health", "scheme": "Ayushman Bharat"},
    {"question": "What diseases are covered under Ayushman Bharat?", "answer": "Over 1,500 medical procedures including surgeries, treatments, and diagnostics.", "category": "health", "scheme": "Ayushman Bharat"},

    # ===== PM KISAN (5) =====
    {"question": "What is PM Kisan?", "answer": "PM-Kisan provides ₹6,000 per year in 3 installments to small and marginal farmers.", "category": "agriculture", "scheme": "Pradhan Mantri Kisan Samman Nidhi"},
    {"question": "Who is eligible for PM Kisan?", "answer": "Small and marginal farmers with landholdings up to 2 hectares.", "category": "agriculture", "scheme": "Pradhan Mantri Kisan Samman Nidhi"},
    {"question": "How to apply for PM Kisan?", "answer": "Apply through the official PM-Kisan portal or local CSC.", "category": "agriculture", "scheme": "Pradhan Mantri Kisan Samman Nidhi"},
    {"question": "How to check PM Kisan payment status?", "answer": "Use the 'Know Your Status' link on the PM-Kisan portal with your registration number.", "category": "agriculture", "scheme": "Pradhan Mantri Kisan Samman Nidhi"},
    {"question": "What documents are needed for PM Kisan?", "answer": "Aadhaar Card, land ownership records, and bank account details.", "category": "agriculture", "scheme": "Pradhan Mantri Kisan Samman Nidhi"},

    # ===== MUDRA YOJANA (5) =====
    {"question": "What is Mudra Loan?", "answer": "Provides loans up to ₹10 lakh for micro enterprises in three categories: Shishu, Kishor, and Tarun.", "category": "business", "scheme": "Pradhan Mantri Mudra Yojana"},
    {"question": "Who is eligible for Mudra Loan?", "answer": "Any Indian citizen with a business plan for non-corporate, non-farm income-generating activity.", "category": "business", "scheme": "Pradhan Mantri Mudra Yojana"},
    {"question": "What are the three levels of Mudra Loan?", "answer": "Shishu (up to ₹50,000), Kishor (₹50,000 to ₹5 lakh), and Tarun (₹5 lakh to ₹10 lakh).", "category": "business", "scheme": "Pradhan Mantri Mudra Yojana"},
    {"question": "How to apply for Mudra Loan?", "answer": "Apply at any commercial bank, RRB, small finance bank, or NBFC with your business proposal.", "category": "business", "scheme": "Pradhan Mantri Mudra Yojana"},
    {"question": "Is collateral needed for Mudra Loan?", "answer": "No, Mudra Loans do not require any collateral or guarantee.", "category": "business", "scheme": "Pradhan Mantri Mudra Yojana"},

    # ===== SUKANYA SAMRIDDHI (5) =====
    {"question": "What is Sukanya Samriddhi Yojana?", "answer": "A savings scheme for the girl child with high interest for education and marriage.", "category": "social", "scheme": "Sukanya Samriddhi Yojana"},
    {"question": "Who can open a Sukanya Samriddhi account?", "answer": "Parents or guardians of a girl child below 10 years of age.", "category": "social", "scheme": "Sukanya Samriddhi Yojana"},
    {"question": "What is the interest rate for Sukanya Samriddhi?", "answer": "Currently around 8.2% per annum, set by the government quarterly.", "category": "social", "scheme": "Sukanya Samriddhi Yojana"},
    {"question": "What is the minimum deposit for Sukanya Samriddhi?", "answer": "Minimum ₹250 per year and maximum ₹1.5 lakh per year.", "category": "social", "scheme": "Sukanya Samriddhi Yojana"},
    {"question": "When can money be withdrawn from Sukanya Samriddhi?", "answer": "Partial withdrawal (50%) at age 18. Full maturity at age 21.", "category": "social", "scheme": "Sukanya Samriddhi Yojana"},

    # ===== STAND UP INDIA (4) =====
    {"question": "What is Stand Up India?", "answer": "Bank loans between ₹10 lakh and ₹1 crore for SC/ST and women entrepreneurs.", "category": "business", "scheme": "Stand Up India Scheme"},
    {"question": "Who is eligible for Stand Up India?", "answer": "SC/ST and/or women entrepreneurs above 18 years for greenfield enterprises.", "category": "business", "scheme": "Stand Up India Scheme"},
    {"question": "How to apply for Stand Up India?", "answer": "Apply online through Stand Up Mitra portal or visit your nearest bank.", "category": "business", "scheme": "Stand Up India Scheme"},
    {"question": "What businesses are covered under Stand Up India?", "answer": "Manufacturing, services, or trading sector enterprises in the greenfield category.", "category": "business", "scheme": "Stand Up India Scheme"},

    # ===== ATAL PENSION YOJANA (4) =====
    {"question": "What is Atal Pension Yojana?", "answer": "Pension scheme providing ₹1,000 to ₹5,000 monthly pension after age 60.", "category": "social", "scheme": "Atal Pension Yojana"},
    {"question": "Who is eligible for Atal Pension Yojana?", "answer": "Indian citizens aged 18-40 with a savings bank account.", "category": "social", "scheme": "Atal Pension Yojana"},
    {"question": "How to apply for Atal Pension Yojana?", "answer": "Fill the registration form at your savings bank branch or via net banking.", "category": "social", "scheme": "Atal Pension Yojana"},
    {"question": "What is the monthly contribution for Atal Pension?", "answer": "As low as ₹42/month (age 18) to ₹291/month (age 35) for ₹1,000 monthly pension.", "category": "social", "scheme": "Atal Pension Yojana"},

    # ===== JAN DHAN (4) =====
    {"question": "What is PM Jan Dhan Yojana?", "answer": "Provides universal banking access with zero-balance accounts, credit, and insurance.", "category": "business", "scheme": "Pradhan Mantri Jan Dhan Yojana"},
    {"question": "What benefits come with Jan Dhan account?", "answer": "Free RuPay card, ₹2 lakh accident insurance, ₹30,000 life cover, overdraft facility.", "category": "business", "scheme": "Pradhan Mantri Jan Dhan Yojana"},
    {"question": "How to open a Jan Dhan account?", "answer": "Visit any bank branch or Business Correspondent outlet with Aadhaar/ID proof.", "category": "business", "scheme": "Pradhan Mantri Jan Dhan Yojana"},
    {"question": "Who is eligible for Jan Dhan Yojana?", "answer": "Any Indian citizen above 10 years without a bank account.", "category": "business", "scheme": "Pradhan Mantri Jan Dhan Yojana"},

    # ===== JEEVAN JYOTI / SURAKSHA BIMA (6) =====
    {"question": "What is PM Jeevan Jyoti Bima Yojana?", "answer": "Life insurance of ₹2 lakh for premium of ₹436 per year.", "category": "social", "scheme": "Pradhan Mantri Jeevan Jyoti Bima Yojana"},
    {"question": "Who can enroll in PMJJBY?", "answer": "Any person aged 18-50 with a savings bank account.", "category": "social", "scheme": "Pradhan Mantri Jeevan Jyoti Bima Yojana"},
    {"question": "How to claim PMJJBY insurance?", "answer": "Nominee submits claim form with death certificate to the bank.", "category": "social", "scheme": "Pradhan Mantri Jeevan Jyoti Bima Yojana"},
    {"question": "What is PM Suraksha Bima Yojana?", "answer": "Accidental death and disability insurance of ₹2 lakh for ₹20 per year.", "category": "social", "scheme": "Pradhan Mantri Suraksha Bima Yojana"},
    {"question": "Who can enroll in PMSBY?", "answer": "Any person aged 18-70 with a savings bank account.", "category": "social", "scheme": "Pradhan Mantri Suraksha Bima Yojana"},
    {"question": "What does PMSBY cover?", "answer": "₹2 lakh for accidental death, ₹2 lakh for total disability, ₹1 lakh for partial.", "category": "social", "scheme": "Pradhan Mantri Suraksha Bima Yojana"},

    # ===== PM UJJWALA (4) =====
    {"question": "What is PM Ujjwala Yojana?", "answer": "Free LPG connections to women from BPL households.", "category": "housing", "scheme": "PM Ujjwala Yojana"},
    {"question": "Who is eligible for Ujjwala Yojana?", "answer": "Women from BPL families above 18 years without existing LPG connection.", "category": "housing", "scheme": "PM Ujjwala Yojana"},
    {"question": "How to apply for Ujjwala Yojana?", "answer": "Visit nearest LPG distributor with Aadhaar, BPL card, and photo.", "category": "housing", "scheme": "PM Ujjwala Yojana"},
    {"question": "What benefits does Ujjwala provide?", "answer": "Free LPG connection, one free refill, stove at subsidized rates.", "category": "housing", "scheme": "PM Ujjwala Yojana"},

    # ===== PM GARIB KALYAN ANNA (3) =====
    {"question": "What is PM Garib Kalyan Anna Yojana?", "answer": "Free food grains (5 kg/person/month) to nearly 80 crore beneficiaries.", "category": "social", "scheme": "PM Garib Kalyan Anna Yojana"},
    {"question": "Who is eligible for PM Garib Kalyan Anna?", "answer": "Families covered under NFSA with Antyodaya or Priority household status.", "category": "social", "scheme": "PM Garib Kalyan Anna Yojana"},
    {"question": "How to avail PM Garib Kalyan Anna?", "answer": "Collect free rations from nearest Fair Price Shop using your ration card.", "category": "social", "scheme": "PM Garib Kalyan Anna Yojana"},

    # ===== SKILL INDIA / PMKVY (6) =====
    {"question": "What is Skill India?", "answer": "A mission providing vocational training and certification to Indian youth.", "category": "education", "scheme": "Skill India Mission"},
    {"question": "How to register for Skill India training?", "answer": "Register on Skill India portal or visit nearest PMKVY training center.", "category": "education", "scheme": "Skill India Mission"},
    {"question": "Is Skill India training free?", "answer": "Yes, training under PMKVY is completely free with certification and placement assistance.", "category": "education", "scheme": "Skill India Mission"},
    {"question": "What courses are available under Skill India?", "answer": "300+ courses in IT, retail, healthcare, construction, beauty, and more.", "category": "education", "scheme": "Skill India Mission"},
    {"question": "What is PM Kaushal Vikas Yojana?", "answer": "Flagship skill training scheme with free industry-relevant training and certification.", "category": "education", "scheme": "PM Kaushal Vikas Yojana"},
    {"question": "How to register for PMKVY?", "answer": "Register on PMKVY portal or visit a training center. Training is completely free.", "category": "education", "scheme": "PM Kaushal Vikas Yojana"},

    # ===== STARTUP INDIA / DIGITAL INDIA (5) =====
    {"question": "What is Startup India?", "answer": "Initiative to nurture startups with tax benefits, funding, and simplified compliance.", "category": "business", "scheme": "Startup India"},
    {"question": "How to register under Startup India?", "answer": "Register on Startup India portal with incorporation certificate and innovation description.", "category": "business", "scheme": "Startup India"},
    {"question": "What benefits does Startup India provide?", "answer": "3-year tax holiday, self-certification compliance, fast-track patents, and funding.", "category": "business", "scheme": "Startup India"},
    {"question": "What is Digital India?", "answer": "Campaign to make government services available electronically via improved infrastructure.", "category": "general", "scheme": "Digital India Programme"},
    {"question": "What services does Digital India offer?", "answer": "DigiLocker, UMANG app, e-Hospital, e-Sign, and digital governance services.", "category": "general", "scheme": "Digital India Programme"},

    # ===== CROP INSURANCE & AGRICULTURE (8) =====
    {"question": "What is PM Fasal Bima Yojana?", "answer": "Crop insurance protecting farmers against loss from natural calamities.", "category": "agriculture", "scheme": "PM Fasal Bima Yojana"},
    {"question": "How to apply for PM Fasal Bima?", "answer": "Register via bank or PMFBY portal with crop and land details before season deadline.", "category": "agriculture", "scheme": "PM Fasal Bima Yojana"},
    {"question": "What is the premium under PM Fasal Bima?", "answer": "2% for Kharif, 1.5% for Rabi, and 5% for commercial/horticultural crops.", "category": "agriculture", "scheme": "PM Fasal Bima Yojana"},
    {"question": "Which crops are covered under PM Fasal Bima?", "answer": "Major food crops, oilseeds, and annual commercial/horticultural crops.", "category": "agriculture", "scheme": "PM Fasal Bima Yojana"},
    {"question": "What is Kisan Credit Card?", "answer": "KCC provides farmers with timely credit for cultivation at low interest.", "category": "agriculture", "scheme": "Kisan Credit Card Scheme"},
    {"question": "How to apply for KCC?", "answer": "Apply at any commercial bank, RRB, or cooperative bank with land documents.", "category": "agriculture", "scheme": "Kisan Credit Card Scheme"},
    {"question": "What is the interest rate on KCC?", "answer": "4% interest (with 3% subvention) for loans up to ₹3 lakh on timely repayment.", "category": "agriculture", "scheme": "Kisan Credit Card Scheme"},
    {"question": "What is Soil Health Card?", "answer": "Provides soil nutrient status and crop-wise fertilizer recommendations.", "category": "agriculture", "scheme": "Soil Health Card Scheme"},

    # ===== HOUSING & INFRASTRUCTURE (6) =====
    {"question": "What is Swachh Bharat Mission?", "answer": "Aims to achieve universal sanitation and eliminate open defecation.", "category": "housing", "scheme": "Swachh Bharat Mission"},
    {"question": "How to get toilet construction subsidy?", "answer": "Apply through local SBM office. ₹12,000 subsidy per toilet under SBM-Gramin.", "category": "housing", "scheme": "Swachh Bharat Mission"},
    {"question": "What is PM SVANidhi?", "answer": "Micro-credit scheme providing affordable loans up to ₹50,000 to street vendors.", "category": "business", "scheme": "PM SVANidhi Scheme"},
    {"question": "How to apply for PM SVANidhi?", "answer": "Apply online at pmsvanidhi.mohua.gov.in or through local urban bodies.", "category": "business", "scheme": "PM SVANidhi Scheme"},
    {"question": "What is PM Vishwakarma?", "answer": "Supports artisans with training, credit up to ₹3 lakh, and digital identity.", "category": "business", "scheme": "PM Vishwakarma Scheme"},
    {"question": "What is Jal Jeevan Mission?", "answer": "Provides functional tap water connections to every rural household.", "category": "housing", "scheme": ""},

    # ===== HEALTH & NUTRITION (5) =====
    {"question": "What is Health ID / ABHA?", "answer": "A unique health ID to store and share health records digitally across India.", "category": "health", "scheme": "National Digital Health Mission"},
    {"question": "How to create an ABHA Health ID?", "answer": "Create on the ABHA portal or ABHA app using Aadhaar.", "category": "health", "scheme": "National Digital Health Mission"},
    {"question": "What is the National Health Mission?", "answer": "Provides universal access to affordable and quality healthcare.", "category": "health", "scheme": "National Health Mission"},
    {"question": "What is PM Matru Vandana Yojana?", "answer": "₹5,000 in 3 installments to pregnant and lactating mothers.", "category": "health", "scheme": ""},
    {"question": "What is PM Poshan Scheme?", "answer": "Free hot cooked meals to students in government schools.", "category": "education", "scheme": "PM Poshan Scheme"},

    # ===== EDUCATION & SCHOLARSHIPS (6) =====
    {"question": "What are National Scholarship Schemes?", "answer": "Various scholarships for students from class 1 to Ph.D.", "category": "education", "scheme": "National Scholarship Schemes"},
    {"question": "How to apply for National Scholarships?", "answer": "Register and apply on NSP at scholarships.gov.in.", "category": "education", "scheme": "National Scholarship Schemes"},
    {"question": "Are there scholarships for girl students?", "answer": "Yes, Pragati Scholarship and AICTE give priority to girls.", "category": "education", "scheme": "National Scholarship Schemes"},
    {"question": "What is PM eVidya?", "answer": "Comprehensive initiative unifying digital and online education.", "category": "education", "scheme": "PM eVidya Programme"},
    {"question": "What is National Career Service?", "answer": "Digital platform connecting job seekers with employers.", "category": "education", "scheme": "National Career Service Scheme"},
    {"question": "What is Beti Bachao Beti Padhao?", "answer": "Campaign to improve awareness and welfare services for girls.", "category": "social", "scheme": "Beti Bachao Beti Padhao"},

    # ===== SOCIAL WELFARE (8) =====
    {"question": "What is the Disability Pension?", "answer": "Monthly financial aid for individuals with 80%+ disability under NSAP.", "category": "social", "scheme": ""},
    {"question": "What are benefits for senior citizens?", "answer": "IGNOAPS pension and Vayoshri Yojana provide financial and physical aids.", "category": "social", "scheme": "Indira Gandhi National Old Age Pension Scheme"},
    {"question": "How to apply for Old Age Pension?", "answer": "Apply via local block office with age proof and BPL certificate.", "category": "social", "scheme": "Indira Gandhi National Old Age Pension Scheme"},
    {"question": "What is PM Shram Yogi Maandhan?", "answer": "Pension scheme for unorganized workers providing ₹3,000/month after age 60.", "category": "social", "scheme": "PM Shram Yogi Maandhan"},
    {"question": "What is NRLM?", "answer": "Creates livelihood opportunities for rural poor through self-help groups.", "category": "social", "scheme": "National Rural Livelihood Mission"},
    {"question": "What is MGNREGA?", "answer": "Guarantees 100 days of wage employment per year to rural households.", "category": "social", "scheme": ""},
    {"question": "What is PM Matsya Sampada Yojana?", "answer": "Sustainable development of fisheries with 40-60% subsidy.", "category": "agriculture", "scheme": "PM Matsya Sampada Yojana"},
    {"question": "What is Rashtriya Vayoshri Yojana?", "answer": "Free physical aids like wheelchairs and hearing aids for BPL senior citizens.", "category": "social", "scheme": "Rashtriya Vayoshri Yojana"},

    # ===== STATE SCHEMES - MAHARASHTRA (5) =====
    {"question": "What is Majhi Kanya Bhagyashree?", "answer": "Maharashtra scheme providing ₹50,000 insurance and financial support for girl children.", "category": "social", "scheme": "Majhi Kanya Bhagyashree"},
    {"question": "Who is eligible for Majhi Kanya Bhagyashree?", "answer": "Girl children born in Maharashtra families with income below ₹7.5 lakh.", "category": "social", "scheme": "Majhi Kanya Bhagyashree"},
    {"question": "What is Maharashtra Gharkul Yojana?", "answer": "Housing scheme providing ₹1.2 lakh for pucca house in rural Maharashtra.", "category": "housing", "scheme": "Maharashtra Gharkul Yojana"},
    {"question": "What is Mahatma Phule Jan Arogya Yojana?", "answer": "Free health insurance covering 971 surgeries for Maharashtra families.", "category": "health", "scheme": "Mahatma Phule Jan Arogya Yojana"},
    {"question": "How to avail Mahatma Phule Jan Arogya?", "answer": "Visit empaneled hospital with yellow/orange ration card for cashless treatment.", "category": "health", "scheme": "Mahatma Phule Jan Arogya Yojana"},

    # ===== STATE SCHEMES - KARNATAKA (4) =====
    {"question": "What is Karnataka Gruha Lakshmi?", "answer": "₹2,000 monthly to women heads of households in Karnataka.", "category": "social", "scheme": "Karnataka Gruha Lakshmi Scheme"},
    {"question": "How to apply for Gruha Lakshmi?", "answer": "Apply on Seva Sindhu portal with Aadhaar and ration card.", "category": "social", "scheme": "Karnataka Gruha Lakshmi Scheme"},
    {"question": "What is Karnataka Yuva Nidhi?", "answer": "₹3,000/month unemployment allowance for graduates in Karnataka.", "category": "education", "scheme": "Karnataka Yuva Nidhi Scheme"},
    {"question": "Who is eligible for Yuva Nidhi?", "answer": "Unemployed graduates/diploma holders under 30 years in Karnataka.", "category": "education", "scheme": "Karnataka Yuva Nidhi Scheme"},

    # ===== STATE SCHEMES - TAMIL NADU (3) =====
    {"question": "What is Kalaignar Magalir Urimai Thogai?", "answer": "₹1,000 monthly to eligible women in Tamil Nadu.", "category": "social", "scheme": "Tamil Nadu Kalaignar Magalir Urimai Thogai"},
    {"question": "What is Tamil Nadu Free Laptop Scheme?", "answer": "Free laptops for students in government schools and colleges in TN.", "category": "education", "scheme": "Tamil Nadu Free Laptop Scheme"},
    {"question": "How to get free laptop in Tamil Nadu?", "answer": "Automatic distribution for students enrolled in government institutions.", "category": "education", "scheme": "Tamil Nadu Free Laptop Scheme"},

    # ===== STATE SCHEMES - UTTAR PRADESH (4) =====
    {"question": "What is UP Kanya Sumangala Yojana?", "answer": "₹15,000 in 6 stages from birth to graduation for girls in UP.", "category": "social", "scheme": "UP Kanya Sumangala Yojana"},
    {"question": "How to apply for Kanya Sumangala?", "answer": "Apply online at mksy.up.gov.in with parents' details.", "category": "social", "scheme": "UP Kanya Sumangala Yojana"},
    {"question": "What is UP Berojgari Bhatta?", "answer": "₹1,000-1,500/month unemployment allowance for educated youth in UP.", "category": "education", "scheme": "UP Berojgari Bhatta"},
    {"question": "How to apply for UP Berojgari Bhatta?", "answer": "Register on UP Sewayojan portal with education certificates.", "category": "education", "scheme": "UP Berojgari Bhatta"},

    # ===== STATE SCHEMES - WEST BENGAL (4) =====
    {"question": "What is Kanyashree Prakalpa?", "answer": "₹750 annual scholarship and ₹25,000 one-time grant for girls in WB.", "category": "education", "scheme": "Kanyashree Prakalpa"},
    {"question": "How to apply for Kanyashree?", "answer": "School/college distributes forms. Income must be below ₹1.2 lakh.", "category": "education", "scheme": "Kanyashree Prakalpa"},
    {"question": "What is Lakshmir Bhandar?", "answer": "₹500-1,000/month to women in West Bengal.", "category": "social", "scheme": "Lakshmir Bhandar"},
    {"question": "How to apply for Lakshmir Bhandar?", "answer": "Apply at Duare Sarkar camp or online with Aadhaar and bank details.", "category": "social", "scheme": "Lakshmir Bhandar"},

    # ===== STATE SCHEMES - GUJARAT (3) =====
    {"question": "What is Gujarat Vahali Dikri Yojana?", "answer": "₹4,000 at Class 1, ₹6,000 at Class 9, ₹1 lakh at age 18 for girls.", "category": "social", "scheme": "Gujarat Vahali Dikri Yojana"},
    {"question": "What is Gujarat Mukhyamantri Yuva Swavalamban?", "answer": "Up to 100% tuition fee waiver for EWS students in professional courses.", "category": "education", "scheme": "Gujarat Mukhyamantri Yuva Swavalamban Yojana"},
    {"question": "How to apply for MYSY Gujarat?", "answer": "Apply on mysy.guj.nic.in with marksheets and income certificate.", "category": "education", "scheme": "Gujarat Mukhyamantri Yuva Swavalamban Yojana"},

    # ===== STATE SCHEMES - RAJASTHAN (3) =====
    {"question": "What is Rajasthan Chiranjeevi Yojana?", "answer": "Universal health insurance providing ₹25 lakh coverage in Rajasthan.", "category": "health", "scheme": "Rajasthan Chiranjeevi Yojana"},
    {"question": "How to register for Chiranjeevi Yojana?", "answer": "Register through e-Mitra kiosk with Jan Aadhaar family ID.", "category": "health", "scheme": "Rajasthan Chiranjeevi Yojana"},
    {"question": "What is Rajasthan Palanhar Yojana?", "answer": "₹500-1,000/month for orphan and destitute children in Rajasthan.", "category": "social", "scheme": "Rajasthan Palanhar Yojana"},

    # ===== STATE SCHEMES - OTHERS (15) =====
    {"question": "What is Kerala LIFE Mission?", "answer": "₹4 lakh for house construction for homeless families in Kerala.", "category": "housing", "scheme": "Kerala LIFE Mission"},
    {"question": "What is Kerala Snehapoorvam?", "answer": "₹300-750/month for orphan students in Kerala.", "category": "education", "scheme": "Kerala Snehapoorvam Scheme"},
    {"question": "What is Punjab Ashirwad Scheme?", "answer": "₹21,000 for marriage of daughters from poor families in Punjab.", "category": "social", "scheme": "Punjab Ashirwad Scheme"},
    {"question": "What is Bihar Kanya Utthan Yojana?", "answer": "₹50,000+ from birth to graduation for girls in Bihar.", "category": "social", "scheme": "Bihar Mukhyamantri Kanya Utthan Yojana"},
    {"question": "What is Bihar Student Credit Card?", "answer": "Education loan up to ₹4 lakh at 4% interest for Bihar students.", "category": "education", "scheme": "Bihar Student Credit Card Scheme"},
    {"question": "How to apply for Bihar Student Credit Card?", "answer": "Apply online at 7 Nishchay portal with 12th marksheet.", "category": "education", "scheme": "Bihar Student Credit Card Scheme"},
    {"question": "What is MP Ladli Laxmi Yojana?", "answer": "₹1,18,000 for girl children across education milestones in MP.", "category": "social", "scheme": "MP Ladli Laxmi Yojana"},
    {"question": "What is AP YSR Rythu Bharosa?", "answer": "₹13,500 per year financial assistance to farmers in Andhra Pradesh.", "category": "agriculture", "scheme": "AP YSR Rythu Bharosa"},
    {"question": "What is AP Amma Vodi?", "answer": "₹15,000/year to mothers for sending children to school in AP.", "category": "education", "scheme": "AP Amma Vodi Scheme"},
    {"question": "What is Telangana Rythu Bandhu?", "answer": "₹10,000 per acre per year investment support for Telangana farmers.", "category": "agriculture", "scheme": "Telangana Rythu Bandhu Scheme"},
    {"question": "What is Telangana Kalyana Lakshmi?", "answer": "₹1,00,116 for marriage of girls from weaker families in Telangana.", "category": "social", "scheme": "Telangana Kalyana Lakshmi Pathakam"},
    {"question": "What is Odisha KALIA Yojana?", "answer": "₹25,000 for small farmers and ₹12,500 for landless in Odisha.", "category": "agriculture", "scheme": "Odisha KALIA Yojana"},
    {"question": "What is Assam Orunodoi?", "answer": "₹1,250/month to one woman per family in Assam.", "category": "social", "scheme": "Assam Orunodoi Scheme"},
    {"question": "What is Chhattisgarh Mahtari Vandan?", "answer": "₹1,000/month to married women in Chhattisgarh.", "category": "social", "scheme": "Chhattisgarh Mahtari Vandan Yojana"},
    {"question": "What is Jharkhand Mukhyamantri Sukanya?", "answer": "Financial support from birth to age 18 for girls in Jharkhand.", "category": "social", "scheme": "Jharkhand Mukhyamantri Sukanya Yojana"},

    # ===== ADDITIONAL SCHEME QUERIES (20) =====
    {"question": "How to check scheme eligibility by state?", "answer": "Type your state name in the chatbot or use the state filter on the schemes page.", "category": "general", "scheme": ""},
    {"question": "What schemes are available for women?", "answer": "PMAY, Ujjwala, Stand Up India, Sukanya Samriddhi, Beti Bachao and many state schemes.", "category": "general", "scheme": ""},
    {"question": "What schemes are available for farmers?", "answer": "PM Kisan, KCC, Fasal Bima, Soil Health Card, PM KUSUM, and state-specific schemes.", "category": "general", "scheme": ""},
    {"question": "What schemes are available for students?", "answer": "National Scholarships, PMKVY, Skill India, PM Research Fellowship, and state schemes.", "category": "general", "scheme": ""},
    {"question": "What schemes are available for senior citizens?", "answer": "IGNOAPS, Atal Pension, Vayoshri Yojana, SCSS, and state pension schemes.", "category": "general", "scheme": ""},
    {"question": "What schemes are for small business?", "answer": "Mudra Loan, PMEGP, Stand Up India, Startup India, PM SVANidhi, and PM Vishwakarma.", "category": "general", "scheme": ""},
    {"question": "How to track my scheme application?", "answer": "Use the official scheme portal's 'Track Status' with your application/registration number.", "category": "general", "scheme": ""},
    {"question": "What is Direct Benefit Transfer?", "answer": "DBT transfers subsidies directly to your Aadhaar-linked bank account without middlemen.", "category": "general", "scheme": ""},
    {"question": "How to link Aadhaar with bank account?", "answer": "Visit your bank branch with Aadhaar card or use the bank's mobile app/net banking.", "category": "general", "scheme": ""},
    {"question": "What is PM KUSUM?", "answer": "Provides solar pumps and grid-connected solar power plants to farmers.", "category": "agriculture", "scheme": ""},
    {"question": "What is Haryana Ladli scheme?", "answer": "₹2,750/month pension to parents with only girl children in Haryana.", "category": "social", "scheme": "Haryana Ladli Social Security Allowance"},
    {"question": "What is MP Yuva Internship?", "answer": "₹8,000/month stipend for paid internship in MP government offices.", "category": "education", "scheme": "MP Mukhyamantri Yuva Internship Yojana"},
    {"question": "What is Odisha Madhu Babu Pension?", "answer": "₹500-700/month pension for elderly, widows, and disabled in Odisha.", "category": "social", "scheme": "Odisha Madhu Babu Pension Yojana"},
    {"question": "What health schemes are available?", "answer": "Ayushman Bharat, NHM, ABHA Health ID, Jan Aushadhi, and state health insurance.", "category": "general", "scheme": ""},
    {"question": "What housing schemes are available?", "answer": "PMAY, Swachh Bharat Mission, Jal Jeevan Mission, Ujjwala, and state housing schemes.", "category": "general", "scheme": ""},
    {"question": "How to apply for a pension scheme?", "answer": "Visit your bank (for APY) or block office (for IGNOAPS) with Aadhaar and bank details.", "category": "general", "scheme": ""},
    {"question": "What insurance schemes are free?", "answer": "PMSBY (₹20/year) and PMJJBY (₹436/year) provide accident and life insurance.", "category": "general", "scheme": ""},
    {"question": "How to get free education loan?", "answer": "Apply on PM Vidya Lakshmi portal or through state credit card schemes.", "category": "general", "scheme": ""},
    {"question": "What schemes exist for differently abled?", "answer": "Disability Pension under NSAP, UDID registration, and Sugamya Bharat Abhiyan.", "category": "general", "scheme": ""},
    {"question": "How to contact SATYA support?", "answer": "Use the Contact Us page link in the footer for any platform-related queries.", "category": "general", "scheme": ""},
]

def get_faqs():
    """Return the scheme-tagged FAQ list"""
    return ENGLISH_FAQS
