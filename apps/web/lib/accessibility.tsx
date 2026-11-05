"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { SupportedLanguage, translations, Translations } from "./i18n";

type TextSize = "normal" | "large" | "extra-large";

interface AccessibilityContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  textSize: TextSize;
  setTextSize: (size: TextSize) => void;
  highContrast: boolean;
  setHighContrast: (hc: boolean) => void;
  t: Translations;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<SupportedLanguage>("te-IN");
  const [textSize, setTextSizeState] = useState<TextSize>("large");
  const [highContrast, setHighContrastState] = useState<boolean>(false);

  useEffect(() => {
    const savedLang = localStorage.getItem("ns_lang") as SupportedLanguage;
    if (savedLang && translations[savedLang]) {
      setLanguageState(savedLang);
    }
    const savedTextSize = localStorage.getItem("ns_text_size") as TextSize;
    if (savedTextSize) {
      setTextSizeState(savedTextSize);
    }
    const savedHC = localStorage.getItem("ns_high_contrast");
    if (savedHC !== null) {
      setHighContrastState(savedHC === "true");
    }
  }, []);

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    localStorage.setItem("ns_lang", lang);
  };

  const setTextSize = (size: TextSize) => {
    setTextSizeState(size);
    localStorage.setItem("ns_text_size", size);
  };

  const setHighContrast = (hc: boolean) => {
    setHighContrastState(hc);
    localStorage.setItem("ns_high_contrast", String(hc));
  };

  const t = translations[language] || translations["te-IN"];

  // Apply root CSS classes for accessibility sizing and contrast
  const containerClasses = [
    highContrast ? "high-contrast bg-black text-yellow-300" : "bg-slate-50 text-slate-900",
    textSize === "extra-large" ? "text-xl leading-relaxed" : textSize === "large" ? "text-lg leading-normal" : "text-base",
    "min-h-screen transition-colors duration-200"
  ].join(" ");

  return (
    <AccessibilityContext.Provider
      value={{
        language,
        setLanguage,
        textSize,
        setTextSize,
        highContrast,
        setHighContrast,
        t,
      }}
    >
      <div className={containerClasses}>{children}</div>
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error("useAccessibility must be used within an AccessibilityProvider");
  }
  return context;
}

