import httpx
import json

def run_scratch_test():
    url = "http://localhost:8000/tailor"
    
    # Define candidate profile data matching schema
    parsed_resume = {
        "name": "Eyad Ahmed",
        "email": "eyad.ahmed@example.com",
        "phone": "+92-300-1234567",
        "links": ["github.com/eyad-dev"],
        "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
        "education": [{
            "degree": "B.S. Computer Science",
            "school": "NUCES",
            "date": "2024"
        }],
        "experience": [
            {
                "role": "Backend Engineer Intern",
                "company": "TechCorp",
                "start_date": "2023-06",
                "end_date": "2023-12",
                "bullets": [
                    "Developed backend services using Python and FastAPI.",
                    "Optimized database queries decreasing latency by 20%."
                ]
            }
        ],
        "projects": []
    }
    
    # Define job description context
    payload = {
        "user_id": "test-user-123",
        "job_id": "test-job-456",
        "jd_text": "We want a Software Engineer to optimize PostgreSQL databases, write FastAPI backend APIs, and manage Kubernetes clusters.",
        "parsed_resume": parsed_resume
    }
    
    print("Sending tailor request to local server...")
    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n=== ATS Score ===")
            print(f"{result['ats_score']}%")
            
            print("\n=== Tagline (Anchor Line) ===")
            print(result['content_json'].get('anchor_line'))
            
            print("\n=== Highlights Strip ===")
            print(json.dumps(result['content_json'].get('highlights_strip'), indent=2))
            
            print("\n=== Gap Analysis ===")
            print(f"Matched Skills: {result['gap_analysis']['matched_skills']}")
            print(f"Missing Skills: {result['gap_analysis']['missing_skills']}")
            
            print("\n=== Truthfulness Report ===")
            print(f"Is Fabricated: {result['truthfulness_report']['is_fabricated']}")
            print(f"Report: {json.dumps(result['truthfulness_report']['verification_report'], indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection failed: {str(e)}")

if __name__ == "__main__":
    run_scratch_test()
