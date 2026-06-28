import os
from app.parsers.pdf_parser import extract_text_from_pdf, ScannedPDFError

def test_resume_extraction():
    pdf_path = os.path.join("..", "Mock", "EyadArshad-Resume.pdf")
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} does not exist.")
        return

    print(f"Reading PDF from: {pdf_path}...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    print(f"PDF Size: {len(pdf_bytes)} bytes")
    
    try:
        extracted_text = extract_text_from_pdf(pdf_bytes)
        print("\n=== Extraction Succeeded! ===")
        print(f"Extracted Length: {len(extracted_text)} characters")
        
        # Verify presence of key resume sections and projects
        keywords = {
            "Name: Eyad Arshad": "Eyad" in extracted_text and "Arshad" in extracted_text,
            "Contact: eyadyr1967@gmail.com": "eyadyr1967@gmail.com" in extracted_text,
            "Education: Air University": "Air University" in extracted_text,
            "Project: HELIX": "HELIX" in extracted_text or "Malware" in extracted_text,
            "Project: Smart Traffic": "Traffic" in extracted_text or "YOLOv8" in extracted_text,
            "Project: UtiliSOFT": "UtiliSOFT" in extracted_text or "ERP" in extracted_text,
            "Skills: Python/C++": "Python" in extracted_text or "C++" in extracted_text
        }

        print("\n=== Verification Checklist ===")
        all_passed = True
        for key, detected in keywords.items():
            status = "✓ DETECTED" if detected else "✗ MISSING"
            if not detected:
                all_passed = False
            print(f"{key}: {status}")

        if all_passed:
            print("\n🎉 PASS: Every piece of key info was successfully detected!")
        else:
            print("\n⚠️ IMPROVE: Some sections were missing from the text layer.")
            
        print("\n=== Extracted Snippet (First 800 chars) ===")
        print(extracted_text[:800])
        
    except ScannedPDFError as e:
        print("\n❌ ScannedPDFError raised:")
        print(str(e))
    except Exception as e:
        print(f"\n❌ Unexpected parser failure: {str(e)}")

if __name__ == "__main__":
    test_resume_extraction()
