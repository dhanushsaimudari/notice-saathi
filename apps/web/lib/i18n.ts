export type SupportedLanguage = "te-IN" | "en-IN" | "hi-IN" | "ta-IN" | "kn-IN";

export interface Translations {
  appName: string;
  tagline: string;
  privacyNotice: string;
  takePhoto: string;
  uploadDoc: string;
  recentDocs: string;
  noRecentDocs: string;
  processing: string;
  uploading: string;
  checkingQuality: string;
  verifyingEvidence: string;
  ready: string;
  needsRecapture: string;
  retakePhoto: string;
  actionCardsTitle: string;
  whatItSays: string;
  whatItMeans: string;
  whatToDo: string;
  whatIsUncertain: string;
  viewProof: string;
  listen: string;
  stop: string;
  replay: string;
  speed: string;
  askQuestion: string;
  typeQuestionPlaceholder: string;
  speakQuestion: string;
  listening: string;
  send: string;
  presetWhatIsThis: string;
  presetWhatDate: string;
  presetWhatAction: string;
  presetHowMuch: string;
  deleteDoc: string;
  deleteConfirm: string;
  cancel: string;
  confirmDelete: string;
  textLarge: string;
  contrastHigh: string;
  home: string;
  history: string;
  settings: string;
}

export const translations: Record<SupportedLanguage, Translations> = {
  "te-IN": {
    appName: "నోటీస్ సాథీ (NoticeSaathi)",
    tagline: "అధికారిక పత్రాలు మరియు నోటీసులను సులభంగా అర్థం చేసుకోండి. పూర్తి రుజువు మరియు ధృవీకరణతో.",
    privacyNotice: "మీ పత్రాలు ప్రైవేట్‌గా మరియు సురక్షితంగా ఉంటాయి. మీరు ఎప్పుడైనా శాశ్వతంగా తొలగించవచ్చు.",
    takePhoto: "ఫోటో తీయండి",
    uploadDoc: "పత్రాన్ని అప్‌లోడ్ చేయండి (PDF / Image)",
    recentDocs: "ఇటీవలి పత్రాలు",
    noRecentDocs: "ఇంతవరకు పత్రాలు ఏవీ అప్‌లోడ్ కాలేదు.",
    processing: "పత్రాన్ని ప్రాసెస్ చేస్తున్నాము...",
    uploading: "అప్‌లోడ్ అవుతోంది...",
    checkingQuality: "ఫోటో స్పష్టతను తనిఖీ చేస్తున్నాము...",
    verifyingEvidence: "వివరాలు మరియు ఆధారాలను ధృవీకరిస్తున్నాము...",
    ready: "పత్రం సిద్ధంగా ఉంది",
    needsRecapture: "ఫోటో స్పష్టంగా కనిపించడం లేదు. దయచేసి మళ్లీ ఫోటో తీయండి.",
    retakePhoto: "మళ్లీ స్పష్టంగా ఫోటో తీయండి",
    actionCardsTitle: "పత్రం ముఖ్య వివరాలు & ఆధారాలు",
    whatItSays: "పత్రంలో రాసి ఉన్నది (అసలు వాక్యం):",
    whatItMeans: "దీని సరళమైన అర్థం:",
    whatToDo: "మీరు చేయాల్సిన పని:",
    whatIsUncertain: "సందేహాస్పదమైన లేదా అస్పష్టమైన అంశాలు:",
    viewProof: "అసలు పత్రంలో ఆధారాన్ని చూడండి",
    listen: "వివరణ వినండి",
    stop: "ఆపండి",
    replay: "మళ్లీ వినండి",
    speed: "వేగం",
    askQuestion: "పత్రం గురించి ప్రశ్న అడగండి",
    typeQuestionPlaceholder: "మీ ప్రశ్నను ఇక్కడ టైప్ చేయండి...",
    speakQuestion: "మాట్లాడి ప్రశ్న అడగండి",
    listening: "వింటున్నాము... మాట్లాడండి",
    send: "పంపండి",
    presetWhatIsThis: "ఇది ఏమి పత్రం?",
    presetWhatDate: "ఇందులో ఉన్న తేదీ ఏమిటి?",
    presetWhatAction: "నేను ఏమి చేయాలి?",
    presetHowMuch: "ఎంత మొత్తం చెల్లించాలి?",
    deleteDoc: "పత్రాన్ని తొలగించండి",
    deleteConfirm: "ఈ పత్రాన్ని మరియు దాని వివరాలను శాశ్వతంగా తొలగించాలా?",
    cancel: "రద్దు చేయండి",
    confirmDelete: "అవును, తొలగించండి",
    textLarge: "పెద్ద అక్షరాలు",
    contrastHigh: "హై కాంట్రాస్ట్",
    home: "హోమ్",
    history: "చరిత్ర",
    settings: "సెట్టింగ్స్"
  },
  "en-IN": {
    appName: "NoticeSaathi",
    tagline: "Evidence-first document companion. Understand official notices with verified proof.",
    privacyNotice: "Your documents are private, protected, and can be permanently deleted at any time.",
    takePhoto: "Take a Photo",
    uploadDoc: "Upload a Document (PDF / Image)",
    recentDocs: "Recent Documents",
    noRecentDocs: "No documents processed yet.",
    processing: "Processing your document...",
    uploading: "Uploading file...",
    checkingQuality: "Checking image quality...",
    verifyingEvidence: "Verifying facts and citations...",
    ready: "Document is ready",
    needsRecapture: "Image is not clear enough. Please recapture.",
    retakePhoto: "Take a Sharper Photo",
    actionCardsTitle: "Action Cards with Proof",
    whatItSays: "What the document says (exact excerpt):",
    whatItMeans: "What it means in simple terms:",
    whatToDo: "What action it explicitly asks for:",
    whatIsUncertain: "What is uncertain or unverified:",
    viewProof: "View proof in document",
    listen: "Listen to explanation",
    stop: "Stop",
    replay: "Replay",
    speed: "Speed",
    askQuestion: "Ask a Question",
    typeQuestionPlaceholder: "Type your question here...",
    speakQuestion: "Tap to Speak",
    listening: "Listening... speak now",
    send: "Submit",
    presetWhatIsThis: "What is this notice?",
    presetWhatDate: "What date is mentioned?",
    presetWhatAction: "What do I need to do?",
    presetHowMuch: "What amount is specified?",
    deleteDoc: "Delete Document",
    deleteConfirm: "Permanently delete this document and all derived data?",
    cancel: "Cancel",
    confirmDelete: "Yes, Delete Permanently",
    textLarge: "Large Text",
    contrastHigh: "High Contrast",
    home: "Home",
    history: "History",
    settings: "Settings"
  },
  "hi-IN": {
    appName: "नोटिस साथी (NoticeSaathi)",
    tagline: "आधिकारिक दस्तावेजों को आसानी से समझें। बिना किसी अनुमान और पूरे प्रमाण के साथ।",
    privacyNotice: "आपके दस्तावेज़ पूरी तरह सुरक्षित और निजी हैं। आप इन्हें कभी भी हमेशा के लिए हटा सकते हैं।",
    takePhoto: "फोटो लें",
    uploadDoc: "दस्तावेज़ अपलोड करें (PDF / Image)",
    recentDocs: "हाल के दस्तावेज़",
    noRecentDocs: "अभी तक कोई दस्तावेज़ अपलोड नहीं किया गया है।",
    processing: "दस्तावेज़ की जाँच की जा रही है...",
    uploading: "अपलोड हो रहा है...",
    checkingQuality: "फोटो की स्पष्टता जांची जा रही है...",
    verifyingEvidence: "तथ्यों और मूल प्रमाणों की पुष्टि की जा रही है...",
    ready: "दस्तावेज़ तैयार है",
    needsRecapture: "तस्वीर पर्याप्त स्पष्ट नहीं है। कृपया दोबारा फोटो लें।",
    retakePhoto: "अधिक स्पष्ट फोटो लें",
    actionCardsTitle: "प्रमाण सहित मुख्य विवरण",
    whatItSays: "दस्तावेज़ में क्या लिखा है (मूल अंश):",
    whatItMeans: "इसका सरल अर्थ:",
    whatToDo: "आपको क्या करने को कहा गया है:",
    whatIsUncertain: "अस्पष्ट या असत्यापित बातें:",
    viewProof: "मूल दस्तावेज़ में प्रमाण देखें",
    listen: "विवरण सुनें",
    stop: "रोकें",
    replay: "दोबारा सुनें",
    speed: "गति",
    askQuestion: "दस्तावेज़ के बारे में प्रश्न पूछें",
    typeQuestionPlaceholder: "अपना प्रश्न यहाँ लिखें...",
    speakQuestion: "बोलकर पूछें",
    listening: "सुन रहे हैं... कृपया बोलें",
    send: "भेजें",
    presetWhatIsThis: "यह क्या नोटिस है?",
    presetWhatDate: "कौन सी तारीख लिखी है?",
    presetWhatAction: "मुझे क्या करना होगा?",
    presetHowMuch: "कितनी राशि लिखी है?",
    deleteDoc: "दस्तावेज़ हटाएं",
    deleteConfirm: "क्या आप इस दस्तावेज़ और संबंधित डेटा को हमेशा के लिए हटाना चाहते हैं?",
    cancel: "रद्द करें",
    confirmDelete: "हाँ, हमेशा के लिए हटाएं",
    textLarge: "बड़ा फॉन्ट",
    contrastHigh: "उच्च कंट्रास्ट",
    home: "होम",
    history: "इतिहास",
    settings: "सेटिंग्स"
  },
  "ta-IN": {
    appName: "நோட்டீஸ் சாதி (NoticeSaathi)",
    tagline: "அரசு அறிவிப்புகள் மற்றும் ஆவணங்களை எளிய தமிழில் ஆதாரத்துடன் புரிந்து கொள்ளுங்கள்.",
    privacyNotice: "உங்கள் ஆவணங்கள் தனிப்பட்டவை மற்றும் பாதுகாப்பானவை. எப்போது வேண்டுமானாலும் அழிக்கலாம்.",
    takePhoto: "படம் எடுக்கவும்",
    uploadDoc: "ஆவணத்தை பதிவேற்றவும்",
    recentDocs: "சமீபத்திய ஆவணங்கள்",
    noRecentDocs: "ஆவணங்கள் எதுவும் இல்லை.",
    processing: "செயலாக்குகிறது...",
    uploading: "பதிவேற்றப்படுகிறது...",
    checkingQuality: "படத்தின் தரம் சரிபார்க்கப்படுகிறது...",
    verifyingEvidence: "சான்றுகள் சரிபார்க்கப்படுகின்றன...",
    ready: "ஆவணம் தயார்",
    needsRecapture: "படம் தெளிவாக இல்லை. மீண்டும் எடுக்கவும்.",
    retakePhoto: "தெளிவான படம் எடுக்கவும்",
    actionCardsTitle: "சான்றுடன் கூடிய தகவல்",
    whatItSays: "ஆவணத்தில் குறிப்பிடப்பட்டுள்ள வாக்கியம்:",
    whatItMeans: "எளிய விளக்கம்:",
    whatToDo: "நீங்கள் செய்ய வேண்டிய நடவடிக்கை:",
    whatIsUncertain: "தெளிவற்ற விவரங்கள்:",
    viewProof: "ஆதாரத்தை பார்க்கவும்",
    listen: "கேட்கவும்",
    stop: "நிறுத்தவும்",
    replay: "மீண்டும் கேட்கவும்",
    speed: "வேகம்",
    askQuestion: "கேள்வி கேட்கவும்",
    typeQuestionPlaceholder: "உங்கள் கேள்வியை தட்டச்சு செய்யவும்...",
    speakQuestion: "பேசி கேட்கவும்",
    listening: "கேட்கிறது... பேசவும்",
    send: "அனுப்பவும்",
    presetWhatIsThis: "இது என்ன ஆவணம்?",
    presetWhatDate: "என்ன தேதி குறிப்பிடப்பட்டுள்ளது?",
    presetWhatAction: "நான் என்ன செய்ய வேண்டும்?",
    presetHowMuch: "எவ்வளவு தொகை குறிப்பிடப்பட்டுள்ளது?",
    deleteDoc: "நீக்கவும்",
    deleteConfirm: "இந்த ஆவணத்தை நிரந்தரமாக நீக்கவா?",
    cancel: "ரத்து செய்",
    confirmDelete: "ஆம், நீக்கு",
    textLarge: "பெரிய எழுத்துக்கள்",
    contrastHigh: "அதிக மாறுபாடு (High Contrast)",
    home: "முகப்பு",
    history: "வரலாறு",
    settings: "அமைப்புகள்"
  },
  "kn-IN": {
    appName: "ನೋಟಿಸ್ ಸಾಥಿ (NoticeSaathi)",
    tagline: "ಅಧಿಕೃತ ನೋಟಿಸ್‌ಗಳನ್ನು ಸರಳವಾಗಿ ಮತ್ತು ಪುರಾವೆಯೊಂದಿಗೆ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಿ.",
    privacyNotice: "ನಿಮ್ಮ ದಾಖಲೆಗಳು ಗೌಪ್ಯ ಮತ್ತು ಸುರಕ್ಷಿತವಾಗಿರುತ್ತವೆ. ನೀವು ಯಾವಾಗ ಬೇಕಾದರೂ ಅಳಿಸಬಹುದು.",
    takePhoto: "ಫೋಟೋ ತೆಗೆಯಿರಿ",
    uploadDoc: "ದಾಖಲೆಯನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
    recentDocs: "ಇತ್ತೀಚಿನ ದಾಖಲೆಗಳು",
    noRecentDocs: "ಯಾವುದೇ ದಾಖಲೆಗಳಿಲ್ಲ.",
    processing: "ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲಾಗುತ್ತಿದೆ...",
    uploading: "ಅಪ್‌ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
    checkingQuality: "ಫೋಟೋ ಗುಣಮಟ್ಟ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
    verifyingEvidence: "ಪುರಾವೆಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
    ready: "ದಾಖಲೆ ಸಿದ್ಧವಾಗಿದೆ",
    needsRecapture: "ಫೋಟೋ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ತೆಗೆಯಿರಿ.",
    retakePhoto: "ಮತ್ತೊಮ್ಮೆ ಸ್ಪಷ್ಟ ಫೋಟೋ ತೆಗೆಯಿರಿ",
    actionCardsTitle: "ಪುರಾವೆಯೊಂದಿಗೆ ವಿವರಣೆ",
    whatItSays: "ದಾಖಲೆಯಲ್ಲಿ ಇರುವ ನಿಖರ ಸಾಲು:",
    whatItMeans: "ಸರಳ ಅರ್ಥ:",
    whatToDo: "ನೀವು ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಕ್ರಮ:",
    whatIsUncertain: "ಅನಿಶ್ಚಿತ ವಿವರಗಳು:",
    viewProof: "ಪುರಾವೆ ನೋಡಿ",
    listen: "ವಿವರಣೆ ಕೇಳಿ",
    stop: "ನಿಲ್ಲಿಸಿ",
    replay: "ಮತ್ತೊಮ್ಮೆ ಕೇಳಿ",
    speed: "ವೇಗ",
    askQuestion: "ಪ್ರಶ್ನೆ ಕೇಳಿ",
    typeQuestionPlaceholder: "ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ...",
    speakQuestion: "ಮಾತನಾಡಿ ಕೇಳಿ",
    listening: "ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇವೆ... ಮಾತನಾಡಿ",
    send: "ಕಳುಹಿಸಿ",
    presetWhatIsThis: "ಇದು ಯಾವ ನೋಟಿಸ್?",
    presetWhatDate: "ಯಾವ ದಿನಾಂಕ ನಮೂದಿಸಲಾಗಿದೆ?",
    presetWhatAction: "ನಾನು ಏನು ಮಾಡಬೇಕು?",
    presetHowMuch: "ಎಷ್ಟು ಹಣ ಪಾವತಿಸಬೇಕು?",
    deleteDoc: "ದಾಖಲೆ ಅಳಿಸಿ",
    deleteConfirm: "ಈ ದಾಖಲೆಯನ್ನು ಶಾಶ್ವತವಾಗಿ ಅಳಿಸಬೇಕೇ?",
    cancel: "ರದ್ದುಮಾಡಿ",
    confirmDelete: "ಹೌದು, ಅಳಿಸಿ",
    textLarge: "ದೊಡ್ಡ ಅಕ್ಷರ",
    contrastHigh: "ಹೆಚ್ಚು ಕಾಂಟ್ರಾಸ್ಟ್",
    home: "ಮುಖಪುಟ",
    history: "ಇತಿಹಾಸ",
    settings: "ಸೆಟ್ಟಿಂಗ್ಸ್"
  }
};

