// LanguageSync.jsx
// Ensures the language selected in Navbar is persisted and applied via i18next.
// We rely entirely on the static react-i18next resource bundles in i18n.js.
// Dynamic DOM mutation and backend translation calls have been removed to prevent
// interference with the static translation architecture.

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export default function LanguageSync() {
  const { i18n } = useTranslation();

  // On mount, sync stored language preference to i18n
  useEffect(() => {
    const stored = localStorage.getItem('language');
    if (stored && stored !== i18n.language) {
      i18n.changeLanguage(stored);
    }
  }, [i18n]);

  return null;
}
