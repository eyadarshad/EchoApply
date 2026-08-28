from unittest.mock import patch
from app.schemas import ResumeParsedData, ExperienceEntry
from app.parsers.llm_extractor import extract_resume_data

def test_eval_resume_parsing_accuracy():
    """Evaluate resume parsing accuracy on test validation dataset."""
    mock_resumes = [
        {
            "raw_text": "Eyad Ahmed. Email: eyad@example.com. Karachi. Skills: Python, FastAPI, SQL. Experience: Software Engineer at Google (2020-2023).",
            "expected": {
                "name": "Eyad Ahmed",
                "email": "eyad@example.com",
                "skills": ["Python", "FastAPI", "SQL"],
                "experience": [
                    {
                        "role": "Software Engineer",
                        "company": "Google",
                        "start_date": "2020",
                        "end_date": "2023",
                        "bullets": []
                    }
                ]
            }
        }
    ]
    
    for case in mock_resumes:
        mock_output = ResumeParsedData(
            name=case["expected"]["name"],
            email=case["expected"]["email"],
            skills=case["expected"]["skills"],
            experience=[ExperienceEntry(**exp) for exp in case["expected"]["experience"]]
        )
        
        with patch("app.parsers.llm_extractor.llm_client.generate_structured", return_value=mock_output) as mock_gen:
            parsed = extract_resume_data(case["raw_text"])
            
            mock_gen.assert_called_once()
            assert parsed.name == case["expected"]["name"]
            assert parsed.email == case["expected"]["email"]
            for skill in case["expected"]["skills"]:
                assert skill in parsed.skills
            assert len(parsed.experience) == 1
            assert parsed.experience[0].company == "Google"
