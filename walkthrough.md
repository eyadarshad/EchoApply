# Phase 6 Walkthrough: Tier-2 Agentic Auto-Apply

Phase 6 implements the Tier-2 agentic auto-apply feature, enabling an opt-in browser agent using Playwright to automate the process of navigating to job application URLs, mapping and auto-filling candidate details/screening answers, detecting blockers (like CAPTCHAs, logins, or missing required fields), and submitting forms safely.

## 1. Context: Relationship with Tier-1

To address the standing sequencing instructions:
- **Tier-1 (Semi-Auto Flow) was successfully built in Phase 4**. It parses job postings, drafts professional answers to screening questions using Gemini (visa, expected salary, notice period, technical skills), and displays them with `"Auto-Filled"` and `"Needs Input"` warning badges in a slide-out drawer where the candidate reviews and refines them.
- **Tier-2 builds directly as an opt-in layer on top of Tier-1**. By default, the Apply drawer runs in Tier-1 mode (human reviews, clicks "Submit", and the system records the application). If and only if the candidate checks the `"Opt-in to Auto-Apply Agent (Tier-2)"` checkbox, the frontend passes `opt_in_agent: true` to the backend to trigger the Playwright browser agent to automatically fill the third-party application using those Tier-1 reviewed/edited answers.

---

## 2. Changes Made

### Backend Components
- **Playwright Browser Agent Service**: Created [browser_agent.py](file:///d:/Project%20101/backend/app/services/browser_agent.py) implementing `run_auto_apply_agent`. The agent launches a headless Chromium instance, checks for logins/CAPTCHAs, maps form elements (input, textarea, checkbox, select) using case-insensitive labels and attributes to candidate profile fields (fullname, email, phone, github, linkedin) and custom screening answers.
- **Handoff Blockers**: Handles safety interrupts (login redirect, CAPTCHA detected, unmapped required fields) by stopping the agent, taking a screenshot (`auto_apply_blocked.png`), closing the browser, and returning `status="needs_action"` with instructions.
- **Local Sandbox Endpoints**: Added GET `/mock-apply-form` and POST `/mock-apply-submit` to [main.py](file:///d:/Project%20101/backend/app/main.py) to enable isolated sandboxed testing of auto-apply in CI/CD without hitting real external platforms.
- **Auto-Apply Trigger**: Integrated agent execution in the `POST /apply/submit` endpoint inside [main.py](file:///d:/Project%20101/backend/app/main.py) when `opt_in_agent` is `True`.

### Frontend Components
- **Opt-in Toggle Checkbox**: Modified [ApplyDrawer.tsx](file:///d:/Project%20101/frontend/src/components/ApplyDrawer.tsx) to add an opt-in checkbox warning users about ToS/account ban risk.
- **Agent Handoff Screens**: Added UI layout to handle `needs_action` responses, displaying a descriptive warning banner, agent screenshot indicator, and action buttons to mark the job as applied manually or return to the form.
- **Submission Mapping**: Standardized sending answers mapped by their question text keys to allow precise keyword/substring matching against page labels.

---

## 3. Verification Results

### A. Automated Sandbox Test Suite
All 4 browser agent test cases and the entire backend test suite pass with 100% success rate:
```text
tests/test_auto_apply_agent.py::test_auto_apply_success PASSED           [ 25%]
tests/test_auto_apply_agent.py::test_auto_apply_login_block PASSED       [ 50%]
tests/test_auto_apply_agent.py::test_auto_apply_captcha_block PASSED     [ 75%]
tests/test_auto_apply_agent.py::test_auto_apply_unmapped_required_field_block PASSED [100%]

============ 38 passed, 2 skipped, 3 warnings in 136.49s (0:02:16) ============
```

### B. Real-World DOM Form Verification (testpages.eviltester.com)
To prove the agent works against a real-world DOM with live input validation, dropdown lists, textareas, and submit buttons, we executed a test run against the public form at `https://testpages.eviltester.com/styled/validation/input-validation.html`.

The agent successfully:
1. Identified label fields ("First name", "Last name", "Age", "Country", "Notes").
2. Standardized inputs: filled names, numeric age, and descriptive notes.
3. Successfully selected the value `"Pakistan"` in the country select dropdown list.
4. Clicked the submit button, validated input criteria, and navigated to the response success screen.

#### Screenshot 1: Form Filled by Agent (Real-World DOM)
Below is the verification screenshot showing the auto-filled validation form captured by the Playwright agent:

![Real-World Form Auto-Filled by Playwright Agent](C:\Users\EYAD\.gemini\antigravity-ide\brain\7e7162d5-5854-4d32-83be-896086a1e4d4\auto_apply_filled.png)

#### Screenshot 2: Successful Submission (Real-World DOM)
Below is the verification screenshot showing the successful submission report page:

![Real-World Submission Success Screen](C:\Users\EYAD\.gemini\antigravity-ide\brain\7e7162d5-5854-4d32-83be-896086a1e4d4\auto_apply_success.png)
