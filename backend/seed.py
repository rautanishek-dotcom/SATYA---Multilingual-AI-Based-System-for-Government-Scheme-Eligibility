import os
from database import init_db, get_db

class DummyApp: pass

def get_all_schemes():
    return [
        {
            "name": "Pradhan Mantri Awas Yojana",
            "description": "Housing for All scheme launched by the Government of India to provide affordable housing for the urban and rural poor.",
            "target_beneficiaries": "Low Income Families",
            "official_website": "https://pmaymis.gov.in/",
            "application_process": "Apply via official portal or local municipality/gram panchayat.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 600000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Ayushman Bharat",
            "description": "World's largest free healthcare scheme providing coverage up to ₹5 lakh per family per year for secondary and tertiary care hospitalization.",
            "target_beneficiaries": "Poor Families",
            "official_website": "https://pmjay.gov.in/",
            "application_process": "Check eligibility online or visit the nearest Empaneled Hospital with Ration Card/Aadhar.",
            "rules": { "min_age": 0, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Pradhan Mantri Kisan Samman Nidhi",
            "description": "An initiative by the government of India that gives all farmers up to ₹6,000 per year as minimum income support.",
            "target_beneficiaries": "Farmers",
            "official_website": "https://pmkisan.gov.in/",
            "application_process": "Register via PM-Kisan portal or CSC with land documents and Aadhar.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["farmer"] }
        },
        {
            "name": "Pradhan Mantri Mudra Yojana",
            "description": "Provides loans up to 10 lakh to the non-corporate, non-farm small/micro enterprises.",
            "target_beneficiaries": "Small Businesses",
            "official_website": "https://www.mudra.org.in/",
            "application_process": "Apply at any commercial bank, RRB, small finance bank, or NBFC.",
            "rules": { "min_age": 18, "max_age": 65, "max_income": 1000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "Sukanya Samriddhi Yojana",
            "description": "A small deposit scheme for the girl child launched as a part of the 'Beti Bachao Beti Padhao' campaign.",
            "target_beneficiaries": "Parents of Girl Child",
            "official_website": "https://www.indiapost.gov.in/",
            "application_process": "Open account in any post office or authorized bank branch.",
            "rules": { "min_age": 0, "max_age": 10, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Stand Up India Scheme",
            "description": "Facilitating bank loans between 10 lakh and 1 crore to at least one SC or ST borrower and at least one woman borrower per bank branch.",
            "target_beneficiaries": "Entrepreneurs (SC/ST/Women)",
            "official_website": "https://www.standupmitra.in/",
            "application_process": "Apply online through the Standup Mitra portal or visit a bank.",
            "rules": { "min_age": 18, "max_age": 65, "max_income": 1000000, "allowed_categories": ["sc", "st"], "gender": ["female"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "Atal Pension Yojana",
            "description": "A pension scheme for citizens of India focused on the unorganized sector workers.",
            "target_beneficiaries": "Unorganized Workers",
            "official_website": "https://npscra.nsdl.co.in/scheme-details.php",
            "application_process": "Fill registration form at your savings bank account branch.",
            "rules": { "min_age": 18, "max_age": 40, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Pradhan Mantri Jan Dhan Yojana",
            "description": "National Mission for Financial Inclusion to ensure access to financial services in an affordable manner.",
            "target_beneficiaries": "Bank Account Access for All",
            "official_website": "https://pmjdy.gov.in/",
            "application_process": "Open a zero-balance account in any bank branch or Business Correspondent outlet.",
            "rules": { "min_age": 10, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
            "description": "A government-backed life insurance scheme in India.",
            "target_beneficiaries": "Life Insurance Seekers",
            "official_website": "https://jansuraksha.gov.in/",
            "application_process": "Enroll through your bank where you have a savings account.",
            "rules": { "min_age": 18, "max_age": 50, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Pradhan Mantri Suraksha Bima Yojana",
            "description": "A government-backed accident insurance scheme in India.",
            "target_beneficiaries": "Accident Insurance Seekers",
            "official_website": "https://jansuraksha.gov.in/",
            "application_process": "Enroll through your bank with a simple auto-debit consent.",
            "rules": { "min_age": 18, "max_age": 70, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM Ujjwala Yojana",
            "description": "Providing LPG connections to women from Below Poverty Line (BPL) households.",
            "target_beneficiaries": "Women",
            "official_website": "https://www.pmuy.gov.in/",
            "application_process": "Apply at the nearest LPG distributor or online portal.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 800000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM Garib Kalyan Anna Yojana",
            "description": "Food security welfare scheme to provide free food grains to the poor.",
            "target_beneficiaries": "Poor Families",
            "official_website": "https://nfsa.gov.in/",
            "application_process": "Eligible households receive grains through Fair Price Shops via Ration Card.",
            "rules": { "min_age": 0, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Skill India Mission",
            "description": "Launched to create convergence across sectors and States in terms of skill training activities.",
            "target_beneficiaries": "Youth",
            "official_website": "https://www.skillindia.gov.in/",
            "application_process": "Register on the Skill India portal and choose a training center.",
            "rules": { "min_age": 15, "max_age": 45, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "Digital India Programme",
            "description": "A campaign to ensure that Government services are made available to citizens electronically.",
            "target_beneficiaries": "Citizens",
            "official_website": "https://www.digitalindia.gov.in/",
            "application_process": "Access various services via DigiLocker, UMANG app, or official portals.",
            "rules": { "min_age": 15, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Startup India",
            "description": "An initiative to help startups through mentorship, funding, and tax benefits.",
            "target_beneficiaries": "Entrepreneurs",
            "official_website": "https://www.startupindia.gov.in/",
            "application_process": "Register your startup on the Startup India portal or mobile app.",
            "rules": { "min_age": 18, "max_age": 45, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "Make in India",
            "description": "Designed to facilitate investment, foster innovation, and build best-in-class manufacturing infrastructure.",
            "target_beneficiaries": "Manufacturing Sector",
            "official_website": "https://www.makeinindia.gov.in/",
            "application_process": "Investors can apply for various licenses and support via the eBiz portal.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "PM Kaushal Vikas Yojana",
            "description": "The flagship scheme of the Ministry of Skill Development & Entrepreneurship (MSDE).",
            "target_beneficiaries": "Skill Training for Youth",
            "official_website": "https://www.pmkvyofficial.org/",
            "application_process": "Register online or at a PMKVY training center.",
            "rules": { "min_age": 18, "max_age": 45, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "Beti Bachao Beti Padhao",
            "description": "To generate awareness and improve the efficiency of welfare services intended for girls.",
            "target_beneficiaries": "Girls",
            "official_website": "https://wcd.nic.in/bbbp-schemes",
            "application_process": "Services available through local district administration and health centers.",
            "rules": { "min_age": 0, "max_age": 18, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM Fasal Bima Yojana",
            "description": "Government-sponsored crop insurance scheme that integrates multiple stakeholders.",
            "target_beneficiaries": "Farmers",
            "official_website": "https://pmfby.gov.in/",
            "application_process": "Register via bank or online portal with crop and land details.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["farmer"] }
        },
        {
            "name": "Soil Health Card Scheme",
            "description": "Issued to farmers which will carry crop-wise recommendations of nutrients and fertilizers.",
            "target_beneficiaries": "Farmers",
            "official_website": "https://soilhealth.dac.gov.in/",
            "application_process": "Register with the local agriculture department for soil testing.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["farmer"] }
        },
        {
            "name": "Kisan Credit Card Scheme",
            "description": "To provide adequate and timely credit support from the banking system for agriculture requirements.",
            "target_beneficiaries": "Farmers",
            "official_website": "https://www.myscheme.gov.in/",
            "application_process": "Apply at any commercial, RRB, or cooperative bank.",
            "rules": { "min_age": 18, "max_age": 75, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["farmer"] }
        },
        {
            "name": "National Rural Livelihood Mission",
            "description": "To alleviate rural poverty and create sustainable livelihood opportunities.",
            "target_beneficiaries": "Rural Poor",
            "official_website": "https://aajeevika.gov.in/",
            "application_process": "Join local Self-Help Groups (SHGs) supported by the mission.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Deen Dayal Upadhyaya Grameen Kaushalya Yojana",
            "description": "A placement linked skill training program for rural poor youth.",
            "target_beneficiaries": "Rural Youth",
            "official_website": "http://ddugky.gov.in/",
            "application_process": "Register via the Kaushal Panjee app or training centers.",
            "rules": { "min_age": 18, "max_age": 35, "max_income": 300000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "Swachh Bharat Mission",
            "description": "To accelerate the efforts to achieve universal sanitation coverage.",
            "target_beneficiaries": "Citizens",
            "official_website": "https://swachhbharatmission.gov.in/",
            "application_process": "Apply for IHHL (Individual House Hold Latrine) support online.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Smart Cities Mission",
            "description": "Urban renewal and retrofitting program to develop smart cities across the country.",
            "target_beneficiaries": "Urban Citizens",
            "official_website": "https://smartcities.gov.in/",
            "application_process": "Participate in local city consultations and project feedback.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "AMRUT Mission",
            "description": "Atal Mission for Rejuvenation and Urban Transformation to provide basic services to households.",
            "target_beneficiaries": "Urban Development",
            "official_website": "https://amrut.mohua.gov.in/",
            "application_process": "Services implemented via Urban Local Bodies (ULBs).",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "National Health Mission",
            "description": "Strengthening health systems and providing universal health coverage.",
            "target_beneficiaries": "Healthcare Seekers",
            "official_website": "https://nhm.gov.in/",
            "application_process": "Access services at government primary health centers and hospitals.",
            "rules": { "min_age": 0, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "POSHAN Abhiyaan",
            "description": "India’s flagship programme to improve nutritional outcomes for children, adolescents, pregnant women and lactating mothers.",
            "target_beneficiaries": "Children and Mothers",
            "official_website": "https://poshanabhiyaan.gov.in/",
            "application_process": "Access services through local Anganwadi centers.",
            "rules": { "min_age": 0, "max_age": 6, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Pradhan Mantri Gram Sadak Yojana",
            "description": "To provide all-weather road connectivity to unconnected habitations.",
            "target_beneficiaries": "Rural Development",
            "official_website": "https://omms.nic.in/",
            "application_process": "Projects managed by state rural road development agencies.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM SVANidhi Scheme",
            "description": "Special micro-credit facility for street vendors to provide affordable loans.",
            "target_beneficiaries": "Street Vendors",
            "official_website": "https://pmsvanidhi.mohua.gov.in/",
            "application_process": "Apply online or via local urban bodies/lending institutions.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 300000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "National Apprenticeship Promotion Scheme",
            "description": "To promote apprenticeship training and incentivize employers who wish to engage apprentices.",
            "target_beneficiaries": "Students/Job Seekers",
            "official_website": "https://www.apprenticeshipindia.gov.in/",
            "application_process": "Register on the apprenticeship portal and find opportunities.",
            "rules": { "min_age": 18, "max_age": 35, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "Free Sewing Machine Scheme",
            "description": "Providing free sewing machines to poor and labor women to make them self-reliant.",
            "target_beneficiaries": "Women",
            "official_website": "https://www.myscheme.gov.in/",
            "application_process": "Apply at the local labor/welfare department with income certificate.",
            "rules": { "min_age": 20, "max_age": 40, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Balika Samridhi Yojana",
            "description": "Providing post-delivery grants and annual scholarships to girls born in BPL families.",
            "target_beneficiaries": "Girls",
            "official_website": "https://wcd.nic.in/",
            "application_process": "Register at health centers or anganwadis after the birth of a girl child.",
            "rules": { "min_age": 0, "max_age": 18, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Indira Gandhi National Old Age Pension Scheme",
            "description": "Providing monthly pension to senior citizens from BPL families.",
            "target_beneficiaries": "Senior Citizens",
            "official_website": "https://nsap.nic.in/",
            "application_process": "Apply via local block office or municipality.",
            "rules": { "min_age": 60, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["senior_citizen"] }
        },
        {
            "name": "Indira Gandhi National Widow Pension Scheme",
            "description": "Monthly pension for widows belonging to BPL households.",
            "target_beneficiaries": "Widows",
            "official_website": "https://nsap.nic.in/",
            "application_process": "Apply via local social welfare department.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["female"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "National Scholarship Schemes",
            "description": "Various scholarships for students from class 1 to Ph.D.",
            "target_beneficiaries": "Students",
            "official_website": "https://scholarships.gov.in/",
            "application_process": "Register and apply online on the NSP portal.",
            "rules": { "min_age": 10, "max_age": 25, "max_income": 800000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "PM Research Fellowship",
            "description": "For high-quality research in various institutions of higher education in India.",
            "target_beneficiaries": "Research Students",
            "official_website": "https://pmrf.in/",
            "application_process": "Apply via participating IITs/IISc on the PMRF portal.",
            "rules": { "min_age": 21, "max_age": 30, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "National Means Cum Merit Scholarship",
            "description": "Scholarships to meritorious students of economically weaker sections to arrest their drop out.",
            "target_beneficiaries": "School Students",
            "official_website": "https://www.myscheme.gov.in/",
            "application_process": "Selection via state-level exams for class 8 students.",
            "rules": { "min_age": 13, "max_age": 18, "max_income": 350000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "PM Poshan Scheme",
            "description": "Mid-day meal scheme providing hot cooked meals to school children.",
            "target_beneficiaries": "School Children",
            "official_website": "https://pmposhan.education.gov.in/",
            "application_process": "Automatic enrollment for students in government and government-aided schools.",
            "rules": { "min_age": 6, "max_age": 14, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "Aatmanirbhar Bharat MSME Scheme",
            "description": "Emergency Credit Line to business enterprises/MSMEs.",
            "target_beneficiaries": "MSMEs",
            "official_website": "https://www.myscheme.gov.in/",
            "application_process": "Apply via linked banks or financial institutions.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 5000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "PM Matsya Sampada Yojana",
            "description": "To bring about a Blue Revolution through sustainable and responsible development of the fisheries sector.",
            "target_beneficiaries": "Fishermen",
            "official_website": "https://pmmsy.dof.gov.in/",
            "application_process": "Submit project proposal to the state fisheries department.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "National Digital Health Mission",
            "description": "Creating an integrated digital health infrastructure for the country.",
            "target_beneficiaries": "Citizens/Healthcare",
            "official_website": "https://ndhm.gov.in/",
            "application_process": "Create an ABHA Health ID online or via mobile app.",
            "rules": { "min_age": 0, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "One Nation One Ration Card",
            "description": "Portability of food security benefits across the country.",
            "target_beneficiaries": "Poor Families/Migrants",
            "official_website": "https://nfsa.gov.in/",
            "application_process": "Use existing Aadhar-linked Ration Card at any FPS shop in India.",
            "rules": { "min_age": 0, "max_age": 100, "max_income": 500000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM Shram Yogi Maandhan",
            "description": "A voluntary and contributory pension scheme for unorganized workers.",
            "target_beneficiaries": "Unorganized Workers",
            "official_website": "https://maandhan.in/",
            "application_process": "Register at any CSC or online portal providing Aadhar and bank details.",
            "rules": { "min_age": 18, "max_age": 40, "max_income": 180000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "PM Vishwakarma Scheme",
            "description": "Support for traditional artisans and craftspeople through training and credit.",
            "target_beneficiaries": "Artisans",
            "official_website": "https://pmvishwakarma.gov.in/",
            "application_process": "Register via CSC using biometric authentication.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 800000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["entrepreneur"] }
        },
        {
            "name": "PM eVidya Programme",
            "description": "A comprehensive initiative which unifies all efforts related to digital/online/on-air education.",
            "target_beneficiaries": "Students",
            "official_website": "https://pmeyvidya.education.gov.in/",
            "application_process": "Educational content available via DIKSHA portal and Swayam Prabha channels.",
            "rules": { "min_age": 6, "max_age": 25, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["student"] }
        },
        {
            "name": "PM Gati Shakti",
            "description": "National Master Plan for Multi-modal Connectivity to integrate infrastructure projects.",
            "target_beneficiaries": "Infrastructure/Citizens",
            "official_website": "https://gatishakti.gov.in/",
            "application_process": "Inter-ministerial coordination for infrastructure planning.",
            "rules": { "min_age": 18, "max_age": 100, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "National Career Service Scheme",
            "description": "Connecting job seekers with employers through a digital platform.",
            "target_beneficiaries": "Job Seekers",
            "official_website": "https://www.ncs.gov.in/",
            "application_process": "Register on the NCS portal or visit a Model Career Center.",
            "rules": { "min_age": 18, "max_age": 35, "max_income": 10000000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["all"] }
        },
        {
            "name": "Deendayal Disabled Rehabilitation Scheme",
            "description": "Providing financial assistance to NGOs for providing diagnostic, therapeutic and rehabilitation services to the disabled.",
            "target_beneficiaries": "Disabled Citizens",
            "official_website": "https://disabilityaffairs.gov.in/",
            "application_process": "Services available through empanelled NGOs and specialized centers.",
            "rules": { "min_age": 18, "max_age": 60, "max_income": 300000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["disabled"] }
        },
        {
            "name": "Rashtriya Vayoshri Yojana",
            "description": "Providing physical aids and assisted-living devices for senior citizens belonging to BPL category.",
            "target_beneficiaries": "Senior Citizens",
            "official_website": "https://socialjustice.gov.in/",
            "application_process": "Check eligibility and apply at the local district social welfare office.",
            "rules": { "min_age": 60, "max_age": 100, "max_income": 200000, "allowed_categories": ["all"], "gender": ["all"], "state": ["all"], "special_category": ["senior_citizen"] }
        }
    ]

if __name__ == "__main__":
    init_db(DummyApp())
    db = get_db()
    
    db.schemes.drop()
    print("Dropped current schemes collection.")
    
    docs = get_all_schemes()
    db.schemes.insert_many(docs)
    print(f"Successfully inserted {len(docs)} schemes into the database.")
