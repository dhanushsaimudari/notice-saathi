"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { SupportedLanguage, translations, Translations } from "./i18n";

export type TextSize = "normal" | "large" | "extra-large";

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

  // Load user preferences from localStorage on initial render
  useEffect(() => {
    try {
      const savedLang = localStorage.getItem("ns_lang") as SupportedLanguage;
      if (savedLang && translations[savedLang]) {
        setLanguageState(savedLang);
      }
      const savedTextSize = localStorage.getItem("ns_text_size") as TextSize;
      if (savedTextSize === "normal" || savedTextSize === "large" || savedTextSize === "extra-large") {
        setTextSizeState(savedTextSize);
      }
      const savedHC = localStorage.getItem("ns_high_contrast");
      if (savedHC !== null) {
        setHighContrastState(savedHC === "true");
      }
    } catch (e) {
      // localStorage may fail in restricted/incognito environments
      console.warn("NoticeSaathi: Failed to read accessibility preferences from storage", e);
    }
  }, []);

  // Sync text size to the root html element so that all rem typography scales globally
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-text-size", textSize);
    }
  }, [textSize]);

  // Sync high contrast mode to the root html element
  useEffect(() => {
    if (typeof document !== "undefined") {
      if (highContrast) {
        document.documentElement.classList.add("high-contrast");
        document.documentElement.setAttribute("data-high-contrast", "true");
      } else {
        document.documentElement.classList.remove("high-contrast");
        document.documentElement.removeAttribute("data-high-contrast");
      }
    }
  }, [highContrast]);

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    try {
      localStorage.setItem("ns_lang", lang);
    } catch {}
  };

  const setTextSize = (size: TextSize) => {
    setTextSizeState(size);
    try {
      localStorage.setItem("ns_text_size", size);
    } catch {}
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-text-size", size);
    }
  };

  const setHighContrast = (hc: boolean) => {
    setHighContrastState(hc);
    try {
      localStorage.setItem("ns_high_contrast", String(hc));
    } catch {}
  };

  const t = translations[language] || translations["te-IN"];

  // Apply root CSS classes for accessibility background, contrast, and sizing
  const containerClasses = [
    highContrast ? "high-contrast bg-black text-yellow-300" : "bg-slate-50 text-slate-900",
    textSize === "extra-large" ? "text-xl leading-relaxed" : textSize === "large" ? "text-lg leading-normal" : "text-base",
    "min-h-screen transition-colors duration-200 w-full overflow-x-hidden"
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
      <div className={containerClasses} data-text-size={textSize}>
        {children}
      </div>
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
