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
    
    jds = {
        "STANDARD MATCH (FastAPI, PostgreSQL, Kubernetes)": "We want a Software Engineer to optimize PostgreSQL databases, write FastAPI backend APIs, and manage Kubernetes clusters.",
        "STRONG MATCH (Python, FastAPI, React)": "We want a Python developer with FastAPI and React frontend experience to build fullstack web applications.",
        "WEAK MATCH (Java, Spring Boot, AWS, MySQL, Terraform)": "Seeking a Senior Java Developer with Spring Boot, AWS deployment, MySQL database tuning, and Terraform infrastructure management experience."
    }
    
    for name, jd_text in jds.items():
        print(f"\n==================================================================")
        print(f" RUNNING SCENARIO: {name}")
        print(f"==================================================================")
        
        payload = {
            "user_id": "test-user-123",
            "job_id": "test-job-456",
            "jd_text": jd_text,
            "parsed_resume": parsed_resume
        }
        
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"ATS Match Score: {result['ats_score']}%")
                print(f"Tagline: {result['content_json'].get('anchor_line')}")
                print(f"Matched Skills: {result['gap_analysis']['matched_skills']}")
                print(f"Missing Skills: {result['gap_analysis']['missing_skills']}")
                
                # Check for partial matches
                partials = result['gap_analysis'].get('partial_matches', [])
                if partials:
                    print(f"Partial Matches: {[p['jd_skill'] + ' (Candidate: ' + p['user_skill'] + ')' for p in partials]}")
                
                print(f"Is Fabricated: {result['truthfulness_report']['is_fabricated']}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Connection failed: {str(e)}")

if __name__ == "__main__":
    run_scratch_test()
