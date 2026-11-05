# NoticeSaathi — Elderly & Accessible Usability Testing Protocol

**Document Version:** 1.0 (Pilot Testing Standard)  
**Target Participant Cohort:** 15–20 Older Adults (Ages 55–80) Across Diverse Literacy & Accessibility Profiles  
**Location:** Community Centers & Legal Aid Clinics (Hyderabad, Warangal, Vijayawada, Tirupati)  
**Guiding Rule:** *Do not claim formal accessibility certification based solely on automated test runs.*

---

## 1. Study Objective

Evaluate whether older adults and citizens with limited English literacy can independently or semi-independently use NoticeSaathi to understand official English notices, listen to verified Telugu explanations, find proof in source documents, and safely delete their data.

---

## 2. Participant Profile Matrix

Participants are recruited across diverse functional and regional backgrounds:

| Dimension | Target Profile Criteria | Minimum Participants |
| :--- | :--- | :--- |
| **Vision Ability** | Presbyopia, cataracts, low vision (using large text / high contrast) | 6 |
| **Hearing Ability** | Mild-to-moderate age-related hearing loss (requiring clear audio + text equivalence) | 5 |
| **English Literacy** | Monoglot Telugu speakers or limited conversational English | 8 |
| **Smartphone Comfort** | Basic feature phone users or occasional smartphone users (relies on voice/caseworker) | 6 |
| **Regional Dialects** | Rural Telangana (Warangal/Nalgonda), Coastal Andhra (Guntur/Krishna), Rayalaseema (Kurnool) | 6 |

---

## 3. 10-Task Supervised Usability Protocol

Each session is conducted in Telugu by a trained bilingual facilitator and caseworker:

| Task # | Task Description | User Goal | Success Criteria | Assistance Level Scored |
| :--- | :--- | :--- | :--- | :--- |
| **Task 1** | **Open NoticeSaathi** | Launch web app on mobile or tablet browser. | Lands on Welcome screen within 15 seconds. | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |
| **Task 2** | **Select Telugu** | Ensure interface and speech are set to `te-IN`. | Taps Telugu language selector pill. | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |
| **Task 3** | **Photograph Document** | Capture physical notice using device camera. | Frame notice, ensure good lighting, tap shutter. | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |
| **Task 4** | **Understand Quality Feedback** | If photo is blurred, understand why recapture is needed. | Understands `NEEDS_RECAPTURE` message without panic. | 1 = Understood immediately, 2 = Needed explanation |
| **Task 5** | **Listen to Spoken Explanation** | Tap large voice speaker button to hear Telugu explanation. | Listens to Gnani TTS `Lavanya` audio playback. | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |
| **Task 6** | **Read Text Explanation** | Read the 3 Action Card sections (What it says, Means, Action). | Comprehends the date, amount, and appearance duty. | 1 = Fully understood, 2 = Partial, 3 = Confused |
| **Task 7** | **Ask Spoken Follow-Up** | Tap large microphone button and speak a question in Telugu. | Speaks question (e.g. "విచారణ తేదీ ఎప్పుడు?"). | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |
| **Task 8** | **Find Source Passage** | Tap "సాక్ష్యం చూడండి (View Proof)" to inspect bounding box. | Identifies highlighted box on original notice. | 1 = Found immediately, 2 = Prompted, 3 = Did not find |
| **Task 9** | **Understand Limitations** | Ask an out-of-bounds question (e.g. "నేను జైలుకు వెళ్తానా?"). | Recognizes that app cannot predict legal outcomes. | 1 = Understood disclaimer, 2 = Confused |
| **Task 10** | **Delete Document** | Tap red "పత్రాన్ని తొలగించండి (Delete Document)" button. | Confirms permanent cascade deletion. | 1 = Independent, 2 = Verbal Prompt, 3 = Demonstrated |

---

## 4. Caseworker Observation & Error Scoring Rubric

During each task, the observer records:
1. **Time to Complete (seconds)**.
2. **Hesitations & Friction Points**: Where did the user pause or ask for clarification?
3. **Misunderstandings**:
   - Did the user confuse a mandatory summons with an optional hearing?
   - Did the user believe NoticeSaathi is an official court app? (Reinforce disclaimer).
4. **Assistance Rating**:
   - **Level 1 (Independent)**: User completed task without intervention.
   - **Level 2 (Verbal Prompt)**: Facilitator gave spoken hint in Telugu.
   - **Level 3 (Demonstrated)**: Facilitator had to touch the screen or guide user hand.

---

## 5. Legal Caseworker Fidelity Review

A certified legal aid advocate examines the output generated for every test session:
- **Accuracy Audit**: Does the Telugu explanation convey the exact legal status without adding or omitting conditions?
- **Prohibited Legal Advice Check**: Did the system suggest any course of action beyond what is written in the notice?
- **Fidelity Scorecard**: 1 to 5 rating on statutory precision, tone appropriateness, and clarity for non-lawyers.

