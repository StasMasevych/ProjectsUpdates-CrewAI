from dotenv import load_dotenv
from crew import RomanianSolarCrew
import json

def main():
    load_dotenv()
    
    # Create and run the crew
    solar_crew = RomanianSolarCrew()
    crew = solar_crew.create_crew()  # Create the crew first
    result = crew.kickoff()  # Then kick it off
    
    # Save results
    try:
        parsed_result = json.loads(result)
        with open('solar_projects_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(parsed_result, f, ensure_ascii=False, indent=2)
        print("\nAnalysis saved to solar_projects_analysis.json")
    except json.JSONDecodeError:
        print("\nRaw result:")
        print(result)

if __name__ == "__main__":
    main() 