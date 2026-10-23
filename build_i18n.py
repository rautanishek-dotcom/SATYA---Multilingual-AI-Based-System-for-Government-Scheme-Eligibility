import re
import json

with open('./frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract 'en' translation object
en_match = re.search(r'en:\s*\{\s*translation:\s*(\{[^}]*?(?:\{[^}]*?\}[^}]*?)*?\})\s*\},', content, re.DOTALL)
if not en_match:
    # Try simpler bracket matching
    start_idx = content.find('en: {')
    trans_idx = content.find('translation: {', start_idx)
    brace_count = 0
    end_idx = trans_idx + len('translation: {') - 1
    for i in range(end_idx, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i + 1
                break
    en_json_str = content[trans_idx + len('translation:'):end_idx].strip()
    en_dict = json.loads(en_json_str)
else:
    en_dict = json.loads(en_match.group(1))

print(f"Loaded English keys: {len(en_dict)}")

# High quality native translations mapping for all key UI terms across 13 missing Eighth Schedule languages
# Language codes: as (Assamese), brx (Bodo), doi (Dogri), ks (Kashmiri), kok (Konkani), mai (Maithili),
# mni (Manipuri), ne (Nepali), or (Odia), pa (Punjabi), sa (Sanskrit), sat (Santali), sd (Sindhi), ur (Urdu)

translations = {
    'as': {  # Assamese
        "Home": "গৃহ", "Schemes": "আঁচনিসমূহ", "EligibilityEngine": "যোগ্যতা পৰীক্ষা", "Vault": "দস্তাবেজ ভল্ট",
        "Admin": "এডমিন", "Login": "লগইন", "Logout": "লগআউট", "Register": "পঞ্জীয়ন কৰক", "Welcome": "SATYA লৈ স্বাগতম",
        "Tagline": "বহুভাষিক AI সৱলীকৰণ মঞ্চ", "HomeTagline": "ভাৰতীয় নাগৰিকসকলৰ বাবে চৰকাৰী আঁচনিৰ সঠিক সন্ধান।",
        "CheckEligibilityBtn": "আঁচনি বিচাৰক", "BrowseSchemes": "আঁচনিসমূহ চাওক", "AIFeatureTitle": "AI যোগ্যতা পৰীক্ষা",
        "AIFeatureDesc": "আপোনাৰ প্ৰফাইলৰ ওপৰত ভিত্তি কৰি সঠিক পৰামৰ্শ লাভ কৰক।", "DiscoveryFeatureTitle": "স্মাৰ্ট আঁচনি অন্বেষণ",
        "DiscoveryFeatureDesc": "কেন্দ্ৰীয় আৰু ৰাজ্যিক আঁচনিসমূহ সহজে বিচাৰি পাওক।", "MultiLangFeatureTitle": "২২টা ভাৰতীয় ভাষা",
        "MultiLangFeatureDesc": "আপোনাৰ নিজৰ ভাষাত সকলো চৰকাৰী তথ্য লাভ কৰক।", "GovtSchemesDirectory": "চৰকাৰী আঁচনি নিৰ্দেশিকা",
        "BrowseAllSchemes": "সকলো উপলব্ধ চৰকাৰী আঁচনি অন্বেষণ কৰক।", "SchemesLastVerified": "আঁচনি অন্তিম পৰীক্ষিত",
        "YourSchemeDeadlines": "আপোনাৰ আঁচনিৰ শেষ সময়সীমা", "YourUpcomingSchemeDeadlines": "আপোনাৰ অহা আঁচনিৰ সময়সীমাসমূহ",
        "NoUpcomingDeadlines": "আপোনাৰ বাবে কোনো সময়সীমা নাই।", "SearchSchemesPlaceholder": "নাম বা শব্দৰে বিচাৰক...",
        "Showing": "দেখা গৈছে", "ClearAll": "ফিল্টাৰ মচি পেলাওক", "Central": "কেন্দ্ৰীয়", "State": "ৰাজ্যিক",
        "ApplyNow": "এতিয়াই আবেদন কৰক", "ViewDetails": "বিতংভাৱে চাওক", "Close": "বন্ধ কৰক", "EmailAddress": "ইমেইল ঠিকানা",
        "Password": "পাছৱৰ্ড", "Name": "নাম", "User": "ব্যৱহাৰকাৰী", "CreateAccount": "একাউণ্ট সৃষ্টি কৰক",
        "AlreadyAccount": "ইতিমধ্যে একাউণ্ট আছে?", "NoAccount": "একাউণ্ট নাই?", "SignUpSecurely": "সুৰক্ষিতভাৱে পঞ্জীয়ন কৰক",
        "LoginHere": "ইয়াত লগইন কৰক", "VerifyDocs": "দস্তাবেজ পৰীক্ষা কৰক", "AadhaarCard": "আধাৰ কাৰ্ড",
        "CasteCert": "জাতিৰ প্ৰমাণপত্ৰ", "UploadDocument": "দস্তাবেজ আপলোড কৰক", "Verified": "পৰীক্ষিত",
        "Pending": "বাকী আছে", "Failed": "ব্যৰ্থ হৈছে", "Status": "স্থিতি", "Actions": "পদক্ষেপ",
        "EmailVerification": "ইমেইল পৰীক্ষণ", "VerifyAndContinue": "পৰীক্ষা কৰি আগবাঢ়ক", "ResendCode": "ক’ড পুনৰ প্ৰেৰণ কৰক"
    },
    'brx': {  # Bodo
        "Home": "नखर", "Schemes": "आँचनिफोर", "EligibilityEngine": "पात्रता नायगिरग्रा", "Vault": "दस्तावेज भल्ट",
        "Admin": "एडमिन", "Login": "लगइन", "Logout": "लगआउट", "Register": "रजिस्टार खालाम", "Welcome": "SATYA याव सिबाय",
        "Tagline": "गोबां रावनि AI हुदा", "HomeTagline": "भारतनि सुबुंफोरनि थाखाय सरकारी आँचनिफोरनि थि सोलोंथि।",
        "CheckEligibilityBtn": "आँचनि नाय", "BrowseSchemes": "आँचनिफोर फराय", "AIFeatureTitle": "AI पात्रता नायनाय",
        "AIFeatureDesc": "नोंथांनि प्रफाइल बादै थि सिफारिस मोन्दों।", "GovtSchemesDirectory": "सरकारी आँचनि निर्देशिका",
        "Showing": "दिन्थिबाय", "ApplyNow": "दायनो आरज खालाम", "ViewDetails": "गुवारै नाय", "Close": "बन्द खालाम",
        "EmailAddress": "इमेल थौले", "Password": "पासवर्ड", "Name": "मुं", "User": "बाहायगिरि", "Verified": "जाबाय",
        "Pending": "नेनाय", "Failed": "फेलेनाव", "Status": "थासारि", "Actions": "हाबाफारि"
    },
    'doi': {  # Dogri
        "Home": "घर", "Schemes": "योजना", "EligibilityEngine": "पात्रता जांच", "Vault": "दस्तावेज वाल्ट",
        "Admin": "एडमिन", "Login": "लॉगिन", "Logout": "लॉगआउट", "Register": "पंजीकरण करो", "Welcome": "SATYA च स्वागत ए",
        "Tagline": "बहुभाषी AI सशक्तिकरण", "HomeTagline": "भारतीय नागरिकें तांई सरकारी योजनाएं दी सही जानकारी।",
        "CheckEligibilityBtn": "योजना लब्भो", "BrowseSchemes": "योजनाएं देखो", "AIFeatureTitle": "AI पात्रता जांच",
        "GovtSchemesDirectory": "सरकारी योजना निर्देशिका", "Showing": "दिखाया जा करदा", "ApplyNow": "हुन आवेदन करो",
        "ViewDetails": "विवरण देखो", "Close": "बंद करो", "EmailAddress": "ईमेल पता", "Password": "पासवर्ड",
        "Name": "नां", "User": "उपयोगकर्ता", "Verified": "सत्यापित", "Pending": "लंबित", "Failed": "विफल", "Status": "स्थिति"
    },
    'ks': {  # Kashmiri
        "Home": "घर", "Schemes": "स्कीम", "EligibilityEngine": "अहलियत जांच", "Vault": "दस्तावेज़ वाल्ट",
        "Admin": "एडमिन", "Login": "लॉगिन", "Logout": "लॉगआउट", "Register": "रजिस्टर करिव", "Welcome": "SATYA मन्ज़ खुश आमदीद",
        "Tagline": "बाहुभाषी AI प्लेटफार्म", "HomeTagline": "भारतीय शहरियन बापत सरकारी स्कीमन हिन्द सही मालूमात।",
        "CheckEligibilityBtn": "स्कीम वोछिव", "BrowseSchemes": "स्कीम परिव", "GovtSchemesDirectory": "सरकारी स्कीम डिरैक्टरी",
        "Showing": "हावनावान", "ApplyNow": "वुनुइ दरखास्त दियिव", "ViewDetails": "तफसील वोछिव", "Close": "बंद करिव",
        "EmailAddress": "ईमेल पता", "Password": "पासवर्ड", "Name": "नाव", "User": "उपयोगकर्ता", "Verified": "सत्यापित",
        "Pending": "लंबित", "Failed": "नाकाम", "Status": "स्थिति"
    },
    'kok': {  # Konkani
        "Home": "घर", "Schemes": "योजना", "EligibilityEngine": "पात्रता तपासणी", "Vault": "दस्तऐवज वॉल्ट",
        "Admin": "प्रशासन", "Login": "लॉगिन", "Logout": "लॉगआउट", "Register": "नोंदणी करा", "Welcome": "SATYA त येवकार",
        "Tagline": "बहुभाषिक AI मंच", "HomeTagline": "भारतीय नागरिकां खातीर सरकारी योजनांची अचूक माहिती.",
        "CheckEligibilityBtn": "योजना सोधा", "BrowseSchemes": "योजना पळायात", "AIFeatureTitle": "AI पात्रता तपासणी",
        "GovtSchemesDirectory": "सरकारी योजना सूची", "Showing": "दाखयता", "ApplyNow": "आत्ताच अर्ज करा",
        "ViewDetails": "तपशील पळायात", "Close": "बंध करा", "EmailAddress": "ईमेल पत्तो", "Password": "पासवर्ड",
        "Name": "नाव", "User": "वापरपी", "Verified": "तपासिल्ले", "Pending": "उरिल्ले", "Failed": "अपयशी", "Status": "स्थिती"
    },
    'mai': {  # Maithili
        "Home": "घर", "Schemes": "योजना सभ", "EligibilityEngine": "पात्रता जाँच", "Vault": "दस्तावेज़ तिजोरी",
        "Admin": "प्रशासक", "Login": "लॉगिन", "Logout": "लॉगआउट", "Register": "पंजीकरण करू", "Welcome": "SATYA मे स्वागत अछि",
        "Tagline": "बहुभाषी AI सशक्तिकरण", "HomeTagline": "भारतीय नागरिक सभ लेल सरकारी योजनाक सटीक जानकारी।",
        "CheckEligibilityBtn": "योजना खोजू", "BrowseSchemes": "योजना सभ देखू", "AIFeatureTitle": "AI पात्रता जाँच",
        "GovtSchemesDirectory": "सरकारी योजना निर्देशिका", "Showing": "देखाओल जा रहल अछि", "ApplyNow": "अखने आवेदन करू",
        "ViewDetails": "विवरण देखू", "Close": "बंद करू", "EmailAddress": "ईमेल पता", "Password": "पासवर्ड",
        "Name": "नाम", "User": "उपयोगकर्ता", "Verified": "सत्यापित", "Pending": "लंबित", "Failed": "असफल", "Status": "स्थिति"
    },
    'mni': {  # Manipuri
        "Home": "য়ুম", "Schemes": "থৌরাংশিং", "EligibilityEngine": "চানবা থিগদবা", "Vault": "চে-চাং ৱাল্ট",
        "Admin": "এদমিন", "Login": "লগইন", "Logout": "লগআউট", "Register": "রেজিষ্টার তৌবা", "Welcome": "SATYA দা তরাম্না ওকচরি",
        "Tagline": "লোন কয়াগী AI পাঙ্গল", "HomeTagline": "ভারতকি প্রজাসিংগীদমক লৈঙাক্কী থৌরাংশিংগী অচুম্বা পাও।",
        "CheckEligibilityBtn": "থৌরাং থীবা", "BrowseSchemes": "থৌরাংশিং য়েংবা", "GovtSchemesDirectory": "লৈঙাক্কী থৌরাং মমিং",
        "Showing": "উৎলি", "ApplyNow": "হৌজিক অর্জি তৌবা", "ViewDetails": "অকুপ্পা য়েংবা", "Close": "থিংジンবা",
        "EmailAddress": "ইমেল এদ্ৰেছ", "Password": "পাসৱাৰ্দ", "Name": "মিং", "User": "শীজিন্নরিবা", "Verified": "য়ারবা",
        "Pending": "ঙাইরিবা", "Failed": "মাই পাকদ্রবা", "Status": "ফিভম"
    },
    'ne': {  # Nepali
        "Home": "गृह", "Schemes": "योजनाहरू", "EligibilityEngine": "योग्यता जाँच", "Vault": "कागजात भल्ट",
        "Admin": "प्रशासक", "Login": "लगइन", "Logout": "लगआउट", "Register": "दर्ता गर्नुहोस्", "Welcome": "SATYA मा स्वागत छ",
        "Tagline": "बहुभाषी AI सशक्तिकरण", "HomeTagline": "भारतीय नागरिकहरूका लागि सरकारी योजनाहरूको सही जानकारी।",
        "CheckEligibilityBtn": "योजना खोज्नुहोस्", "BrowseSchemes": "योजनाहरू हेर्नुहोस्", "AIFeatureTitle": "AI योग्यता जाँच",
        "GovtSchemesDirectory": "सरकारी योजना निर्देशिका", "Showing": "देखाउँदै", "ApplyNow": "अहिले आवेदन दिनुहोस्",
        "ViewDetails": "विवरण हेर्नुहोस्", "Close": "बन्द गर्नुहोस्", "EmailAddress": "इमेल ठेगाना", "Password": "पासवर्ड",
        "Name": "नाम", "User": "प्रयोगकर्ता", "Verified": "प्रमाणित", "Pending": "बाँकी", "Failed": "असफल", "Status": "स्थिति"
    },
    'or': {  # Odia
        "Home": "ମୁଖ୍ୟ ପୃଷ୍ଠା", "Schemes": "ଯୋଜନାସମୂହ", "EligibilityEngine": "ଯୋଗ୍ୟତା ଯାଞ୍ଚ", "Vault": "ଦଲିଲ ଭଲ୍ଟ",
        "Admin": "ଆଡମିନ୍", "Login": "ଲଗ୍ ଇନ୍", "Logout": "ଲଗ୍ ଆଉଟ୍", "Register": "ପଞ୍ଜୀକରଣ କରନ୍ତୁ", "Welcome": "SATYA କୁ ସ୍ୱାଗତ",
        "Tagline": "ବହୁଭାଷୀ AI ସଶକ୍ତିକରଣ", "HomeTagline": "ଭାରତୀୟ ନାଗରିକମାନଙ୍କ ପାଇଁ ସରକାରୀ ଯୋଜନାର ସଠିକ୍ ସୂଚନା।",
        "CheckEligibilityBtn": "ଯୋଜନା ଖୋଜନ୍ତୁ", "BrowseSchemes": "ଯୋଜନାସମୂହ ଦେଖନ୍ତୁ", "AIFeatureTitle": "AI ଯୋଗ୍ୟତା ଯାଞ୍ଚ",
        "GovtSchemesDirectory": "ସରକାରୀ ଯୋଜନା ନିର୍ଦ୍ଦେଶିକା", "Showing": "ଦର୍ଶାଯାଉଛି", "ApplyNow": "ବର୍ତ୍ତମାନ ଆବେଦନ କରନ୍ତୁ",
        "ViewDetails": "ବିବରଣୀ ଦେଖନ୍ତୁ", "Close": "ବନ୍ଦ କରନ୍ତୁ", "EmailAddress": "ଇମେଲ୍ ଠିକଣା", "Password": "ପାସୱାର୍ଡ",
        "Name": "ନାମ", "User": "ବ୍ୟବହାରକାରୀ", "Verified": "ଯାଞ୍ଚ ହୋଇଛି", "Pending": "ବ୍ରାକୀ ଅଛି", "Failed": "ବିଫଳ", "Status": "ସ୍ଥିତି"
    },
    'pa': {  # Punjabi
        "Home": "ਮੁੱਖ ਪੰਨਾ", "Schemes": "ਯੋਜਨਾਵਾਂ", "EligibilityEngine": "ਯੋਗਤਾ ਜਾਂਚ", "Vault": "ਦਸਤਾਵੇਜ਼ ਵਾਲਟ",
        "Admin": "ਐਡਮਿਨ", "Login": "ਲੌਗਇਨ", "Logout": "ਲੌਗਆਊਟ", "Register": "ਰਜਿਸਟਰ ਕਰੋ", "Welcome": "SATYA ਵਿੱਚ ਜੀ ਆਇਆਂ ਨੂੰ",
        "Tagline": "ਬਹੁਭਾਸ਼ਾਈ AI ਸਸ਼ਕਤੀਕਰਨ", "HomeTagline": "ਭਾਰਤੀ ਨਾਗਰਿਕਾਂ ਲਈ ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਦੀ ਸਹੀ ਜਾਣਕਾਰੀ।",
        "CheckEligibilityBtn": "ਯੋਜਨਾਵਾਂ ਲੱਭੋ", "BrowseSchemes": "ਯੋਜਨਾਵਾਂ ਵੇਖੋ", "AIFeatureTitle": "AI ਯੋਗਤਾ ਜਾਂਚ",
        "GovtSchemesDirectory": "ਸਰਕਾਰੀ ਯੋਜਨਾ ਨਿਰਦੇਸ਼ਿਕਾ", "Showing": "ਦਿਖਾਇਆ ਜਾ ਰਿਹਾ ਹੈ", "ApplyNow": "ਹੁਣੇ ਅਪਲਾਈ ਕਰੋ",
        "ViewDetails": "ਵੇਰਵੇ ਵੇਖੋ", "Close": "ਬੰਦ ਕਰੋ", "EmailAddress": "ਈਮੇਲ ਪਤਾ", "Password": "ਪਾਸਵਰਡ",
        "Name": "ਨਾਮ", "User": "ਉਪਭੋਗਤਾ", "Verified": "ਸਤਿਆਪਿਤ", "Pending": "ਬਕਾਇਆ", "Failed": "ਅਸਫਲ", "Status": "ਸਥਿਤੀ"
    },
    'sa': {  # Sanskrit
        "Home": "मुख्यपृष्ठम्", "Schemes": "योजनाः", "EligibilityEngine": "पात्रतापरीक्षा", "Vault": "दस्तावेज़कोषः",
        "Admin": "प्रशासकः", "Login": "प्रवेशः", "Logout": "निर्गमः", "Register": "पञ्जीकरणं करोतु", "Welcome": "SATYA मध्ये स्वागतम्",
        "Tagline": "बहुभाषीय AI सशक्तिकरणम्", "HomeTagline": "भारतीयनागरिकाणां कृते सर्वकारीययोजनानां यथार्थज्ञानम्।",
        "CheckEligibilityBtn": "योजनाः अन्विषतु", "BrowseSchemes": "योजनाः पश्यतु", "AIFeatureTitle": "AI पात्रतापरीक्षा",
        "GovtSchemesDirectory": "सर्वकारीययोजनानिर्देशिका", "Showing": "प्रदर्शितम्", "ApplyNow": "अधुना आवेदनं करोतु",
        "ViewDetails": "विवरणं पश्यतु", "Close": "पिदधातु", "EmailAddress": "ईमेल-सङ्केतः", "Password": "कूटशब्दः",
        "Name": "नाम", "User": "उपयोक्ता", "Verified": "सत्यापितम्", "Pending": "लम्बितम्", "Failed": "विफलम्", "Status": "स्थितिः"
    },
    'sat': {  # Santali
        "Home": "ᱚᱲᱟᱜ", "Schemes": "ᱡᱚᱡᱚᱱᱟ", "EligibilityEngine": "ᱞᱟᱹᱠᱛᱤᱭᱟᱱ ᱡᱟᱸᱪ", "Vault": "ᱫᱚᱞᱤᱞ ᱵᱷᱚᱞᱴ",
        "Admin": "ᱮᱰᱢᱤᱱ", "Login": "ᱞᱚᱜᱤᱱ", "Logout": "ᱞᱚᱜᱽᱟᱣᱩᱴ", "Register": "ᱨᱮᱡᱤᱥᱴᱟᱨ", "Welcome": "SATYA ᱨᱮ ᱥᱟᱹᱜᱩᱱ ᱫᱟᱨᱟᱢ",
        "Tagline": "ᱟᱭᱢᱟ ᱯᱟᱹᱨᱥᱤ AI ᱫᱟᱲᱮ", "HomeTagline": "ᱵᱷᱟᱨᱚᱛᱤᱭᱟᱹ ᱱᱟᱹᱜᱟᱹᱨᱤᱭᱟᱹ ᱠᱚ ᱞᱟᱹᱜᱤᱫ ᱥᱚᱨᱠᱟᱨᱤ ᱡᱚᱡᱚᱱᱟ ᱨᱮᱱᱟᱜ ᱥᱟᱹᱨᱤ ᱠᱟᱛᱷᱟ᱾",
        "CheckEligibilityBtn": "ᱡᱚᱡᱚᱱᱟ ᱯᱟᱸᱡᱟᱭ ᱢᱮ", "BrowseSchemes": "ᱡᱚᱡᱚᱱᱟ ᱧᱮᱞ ᱢᱮ", "GovtSchemesDirectory": "ᱥᱚᱨᱠᱟᱨᱤ ᱡᱚᱡᱚᱱᱟ ᱞᱤᱥᱴ",
        "Showing": "ᱩᱫᱩᱜᱚᱜ ᱠᱟᱱᱟ", "ApplyNow": "ᱱᱤᱛᱚᱜ ᱟᱨᱫᱟᱥ ᱢᱮ", "ViewDetails": "ᱵᱤᱵᱚᱨᱚᱱ ᱧᱮᱞ ᱢᱮ", "Close": "ᱵᱚᱸᱫᱚᱭ ᱢᱮ",
        "EmailAddress": "ᱤᱢᱮᱞ ᱴᱷᱤᱠᱟᱹᱱᱟ", "Password": "ᱯᱟᱥᱣᱟᱨᱰ", "Name": "ᱧᱩᱛᱩᱢ", "User": "ᱵᱮᱣᱦᱟᱨᱤᱭᱟᱹ", "Verified": "ᱡᱟᱸᱪ ᱮᱱᱟ",
        "Pending": "ᱵᱟᱹᱠᱤ", "Failed": "ᱵᱟᱝ ᱦᱩᱭ ᱞᱮᱱᱟ", "Status": "ᱦᱟᱞᱚᱛ"
    },
    'sd': {  # Sindhi
        "Home": "گھر", "Schemes": "اسڪيمون", "EligibilityEngine": "اهليت جي چڪاس", "Vault": "دستاويز والٽ",
        "Admin": "ايڊمن", "Login": "لاگ ان", "Logout": "لاگ آئوٽ", "Register": "رجسٽر ڪريو", "Welcome": "SATYA ۾ ڀلي ڪري آيا",
        "Tagline": "گهڻ-ٻولي AI سگهه", "HomeTagline": "بهارتي شهريءَ لاءِ سرڪاري اسڪيمن جي صحيح معلومات.",
        "CheckEligibilityBtn": "اسڪيمون ڳوليو", "BrowseSchemes": "اسڪيمون ڏسو", "GovtSchemesDirectory": "سرڪاري اسڪيم ڊائريڪٽري",
        "Showing": "ڏيکاري پيو", "ApplyNow": "هاڻي درخواست ڏيو", "ViewDetails": "تفصيل ڏسو", "Close": "بند ڪريو",
        "EmailAddress": "اي ميل پتو", "Password": "پاسورڊ", "Name": "نالو", "User": "واپرائيندڙ", "Verified": "تصديق ٿيل",
        "Pending": "بقايا", "Failed": "ناڪام", "Status": "حالت"
    },
    'ur': {  # Urdu
        "Home": "ہوم", "Schemes": "اسکیمیں", "EligibilityEngine": "اہلیت کی جانچ", "Vault": "دستاویز والٹ",
        "Admin": "ایڈمن", "Login": "لاگ ان", "Logout": "لاگ آؤٹ", "Register": "رجسٹر کریں", "Welcome": "SATYA میں خوش آمدید",
        "Tagline": "کثیر لسانی AI بااختیار بنانا", "HomeTagline": "ہندوستانی شہریوں کے لیے سرکاری اسکیموں کی درست معلومات۔",
        "CheckEligibilityBtn": "اسکیمیں تلاش کریں", "BrowseSchemes": "اسکیمیں دیکھیں", "AIFeatureTitle": "AI اہلیت کی جانچ",
        "GovtSchemesDirectory": "سرکاری اسکیموں کی ڈائریکٹری", "Showing": "دکھایا جا رہا ہے", "ApplyNow": "ابھی اپلائی کریں",
        "ViewDetails": "تفصیلات دیکھیں", "Close": "بند کریں", "EmailAddress": "ای میل ایڈریس", "Password": "پاس ورڈ",
        "Name": "نام", "User": "صارف", "Verified": "تصدیق شدہ", "Pending": "زیر التواء", "Failed": "ناکام", "Status": "حیثیت"
    }
}

# Construct full entries for missing languages using fallback to EN dictionary so every key exists
new_resources_code = ""

for lang_code, lang_trans in translations.items():
    full_dict = {}
    for key, default_en_val in en_dict.items():
        # Use translated value if available, else fallback value
        full_dict[key] = lang_trans.get(key, default_en_val)
    
    dict_json = json.dumps(full_dict, ensure_ascii=False, indent=6)
    new_resources_code += f",\n  {lang_code}: {{\n    translation: {dict_json}\n  }}"

# Append all 13 new languages right before `};` ending resources in i18n.js
insert_point = content.rfind('};\n\ni18n')
if insert_point == -1:
    insert_point = content.rfind('};\ni18n')

updated_content = content[:insert_point] + new_resources_code + "\n" + content[insert_point:]

with open('./frontend/src/i18n.js', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print(f"Successfully added {len(translations)} new languages to i18n.js!")
