import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      "Welcome": "Welcome to SATYA",
      "Tagline": "Your Gateway to Government Schemes",
      "Get Started": "Get Started",
      "Login": "Login",
      "Register": "Register",
      "Schemes": "Govt Schemes",
      "Dashboard": "Dashboard",
      "Profile": "Profile Assessment",
      "EligibilityEngine": "Check Eligibility",
      "Chat": "Ask SATYA",
      "HomeTagline": "Discover schemes you actually qualify for, instantly.",
      "CheckEligibilityBtn": "Find Schemes Now",
      "Language": "Language",
      "Name": "Full Name",
      "Age": "Age",
      "Gender": "Gender",
      "State": "State",
      "District": "District",
      "Income": "Annual Income",
      "Occupation": "Occupation",
      "Category": "Caste Category",
      "SpecialCategory": "Special Category",
      "Submit": "Submit",
      "EligibleSchemes": "Your Eligible Schemes"
    }
  },
  hi: {
    translation: {
      "Welcome": "सत्य में आपका स्वागत है",
      "Tagline": "सरकारी योजनाओं का आपका प्रवेश द्वार",
      "Get Started": "शुरू करें",
      "Login": "लॉग इन",
      "Register": "रजिस्टर",
      "Schemes": "सरकारी योजनाएं",
      "Dashboard": "डैशबोर्ड",
      "Profile": "प्रोफ़ाइल मूल्यांकन",
      "EligibilityEngine": "पात्रता जांचें",
      "Chat": "सत्य से पूछें",
      "HomeTagline": "तुरंत उन योजनाओं की खोज करें जिनके लिए आप वास्तव में पात्र हैं।",
      "CheckEligibilityBtn": "योजनाएं खोजें",
      "Language": "भाषा",
      "Name": "पूरा नाम",
      "Age": "आयु",
      "Gender": "लिंग",
      "State": "राज्य",
      "District": "ज़िला",
      "Income": "वार्षिक आय",
      "Occupation": "व्यवसाय",
      "Category": "जाति श्रेणी",
      "SpecialCategory": "विशेष श्रेणी",
      "Submit": "जमा करें",
      "EligibleSchemes": "आपकी योग्य योजनाएं"
    }
  },
  kn: {
    translation: {
      "Welcome": "SATYA ಗೆ ಸುಸ್ವಾಗತ",
      "Tagline": "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳಿಗೆ ನಿಮ್ಮ ಗೇಟ್‌ವೇ",
      "Get Started": "ಪ್ರಾರಂಭಿಸಿ",
      "Login": "ಲಾಗಿನ್",
      "Register": "ನೋಂದಾಯಿಸಿ",
      "Schemes": "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು",
      "Dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
      "Profile": "ಪ್ರೊಫೈಲ್ ಮೌಲ್ಯಮಾಪನ",
      "EligibilityEngine": "ಅರ್ಹತೆಯನ್ನು ಪರಿಶೀಲಿಸಿ",
      "Chat": "ಸತ್ಯ ಅವರನ್ನು ಕೇಳಿ",
      "HomeTagline": "ನೀವು ನಿಜವಾಗಿಯೂ ಅರ್ಹರಾಗಿರುವ ಯೋಜನೆಗಳನ್ನು ತಕ್ಷಣವೇ ಅನ್ವೇಷಿಸಿ.",
      "CheckEligibilityBtn": "ಈಗ ಯೋಜನೆಗಳನ್ನು ಹುಡುಕಿ",
      "Language": "ಭಾಷೆ",
      "Name": "ಪೂರ್ಣ ಹೆಸರು",
      "Age": "ವಯಸ್ಸು",
      "Gender": "ಲಿಂಗ",
      "State": "ರಾಜ್ಯ",
      "District": "ಜಿಲ್ಲೆ",
      "Income": "ವಾರ್ಷಿಕ ಆದಾಯ",
      "Occupation": "ಉದ್ಯೋಗ",
      "Category": "ಜಾತಿ ವರ್ಗ",
      "SpecialCategory": "ವಿಶೇಷ ವರ್ಗ",
      "Submit": "ಸಲ್ಲಿಸು",
      "EligibleSchemes": "ನಿಮ್ಮ ಅರ್ಹ ಯೋಜನೆಗಳು"
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en", // default language
    fallbackLng: "en",
    interpolation: {
      escapeValue: false 
    }
  });

export default i18n;
