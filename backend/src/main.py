import warnings
from pydantic import PydanticDeprecatedSince20
from typing import List, Dict
import os
from datetime import datetime

# Suppress specific Pydantic warnings
warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from dotenv import load_dotenv
from src.crew import EnergyProjectsCrew
from src.config.regions import get_countries_for_region
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from sse_starlette.sse import EventSourceResponse
import asyncio
from .accumulator import ResultsAccumulator

app = FastAPI()

# Store progress updates
progress_updates = []

# Allow frontend (Next.js) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # More permissive for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def send_progress_update(country: str, step: str):
    progress_updates.append({"country": country, "step": step})

async def process_region(region: str, technology: str) -> Dict:
    """Process all countries in a region"""
    countries = get_countries_for_region(region)
    accumulator = ResultsAccumulator()
    
    for country in countries:
        await send_progress_update(country, "starting")
        try:
            # Process single country
            result = await process_country(country, technology)
            
            # Add results to accumulator
            accumulator.add_country_results(
                country=country,
                search_results=result.get("search_results", []),
                analysis_results=result.get("analysis", {})
            )
            
            await send_progress_update(country, "complete")
        except Exception as e:
            await send_progress_update(country, "error")
            print(f"Error processing {country}: {str(e)}")
            continue

    # Save final accumulated results
    accumulator.save_results()
    
    # Return the properly structured response
    final_results = accumulator.get_results()
    return {
        "timestamp": datetime.now().isoformat(),
        "search_results": final_results["search_results"],
        "analysis": {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "countries_analyzed": final_results["analysis"]["summary"]["countries_analyzed"],
                "major_developers": list(final_results["analysis"]["summary"]["major_developers"]),
                "most_promising_projects": final_results["analysis"]["summary"].get("most_promising_projects", [])
            },
            "projects_by_country": final_results["analysis"]["projects_by_country"]
        }
    }

async def process_country(country: str, technology: str) -> Dict:
    """Process a single country's data"""
    try:
        print(f"\n📍 Starting process for {country}")
        await send_progress_update(country, "searching")
        
        print(f"🔧 Creating crew for {country}")
        energy_crew = EnergyProjectsCrew(country=country, technology=technology)
        crew = energy_crew.create_crew()
        
        print(f"🚀 Executing crew for {country}")
        await send_progress_update(country, "processing")
        result = crew.kickoff()
        
        print("\n🔍 Raw Result Type:", type(result))
        print("🔍 Raw Result Content:")
        print("---START OF RAW RESULT---")
        print(result)
        print("---END OF RAW RESULT---")
        
        await send_progress_update(country, "analyzing")
        
        # Convert CrewOutput to string and parse
        try:
            # Get the string representation of CrewOutput
            result_str = str(result)
            print("\n📝 Converting CrewOutput to string:")
            print(result_str)
            
            # Find the JSON content within the string
            json_start = result_str.find('{')
            json_end = result_str.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_content = result_str[json_start:json_end]
                print("\n🔍 Extracted JSON content:")
                print(json_content)
                
                # Parse the JSON content
                parsed_result = json.loads(json_content)
                print("\n✅ Successfully parsed JSON")
                
                # Ensure output directory exists
                output_dir = Path(__file__).parent.parent / 'output'
                output_dir = output_dir.absolute()  # Get absolute path without resolving symlinks
                output_dir.mkdir(exist_ok=True)
                
                # Save country-specific analysis results
                analysis_output_file = output_dir / f'analysis_results_{country}.json'
                with open(analysis_output_file, 'w', encoding='utf-8') as f:
                    json.dump(parsed_result, f, ensure_ascii=False, indent=2)
                print(f"\n💾 Analysis results saved to: {analysis_output_file}")
                
                # Save country-specific search results if available
                search_results = []
                if "search_results" in parsed_result:
                    search_results = parsed_result["search_results"]
                
                # Always create a search results file, even if empty
                search_output_file = output_dir / f'search_results_{country}.json'
                with open(search_output_file, 'w', encoding='utf-8') as f:
                    json.dump(search_results, f, ensure_ascii=False, indent=2)
                print(f"\n💾 Search results saved to: {search_output_file}")
                
                # Standardize the result structure
                standardized_result = standardize_country_result(parsed_result, country)
                
                return standardized_result
            else:
                print("\n❌ Could not find valid JSON content in the result")
                return {"error": "Could not parse result"}
        except Exception as e:
            print(f"\n❌ Error parsing result: {str(e)}")
            return {"error": str(e)}
            
    except Exception as e:
        print(f"\n❌ Error in process_country for {country}: {str(e)}")
        return {"error": str(e)}

def standardize_project(project: Dict, country: str) -> Dict:
    """Standardize project data structure"""
    # Extract key points with flexibility for different field names
    key_points = []
    if "KeyPoints" in project and isinstance(project["KeyPoints"], list):
        key_points = project["KeyPoints"]
    elif "keyPoints" in project and isinstance(project["keyPoints"], list):
        key_points = project["keyPoints"]
    elif "key_points" in project and isinstance(project["key_points"], list):
        key_points = project["key_points"]
    
    # Ensure we have a valid list
    if not isinstance(key_points, list):
        key_points = []
    
    # Check for partners with similar flexibility
    partners = []
    if "partners" in project and isinstance(project["partners"], list):
        partners = project["partners"]
    elif "Partners" in project and isinstance(project["Partners"], list):
        partners = project["Partners"]
    
    # Always use today's date for all projects
    today_date = datetime.now().strftime("%m/%d/%Y")
    
    if 'ProjectName' in project:
        return {
            "name": project.get("ProjectName", "Unknown"),
            "location": project.get("Location", country),
            "capacity": str(project.get("Capacity_MW", "N/A")),
            "developer": project.get("Developer", "Unknown"),
            "investment": project.get("InvestmentValue", "N/A"),
            "timeline": project.get("Timeline", "N/A"),
            "source_url": project.get("source_url", ""),
            "source_name": project.get("source_name", country),
            "status": project.get("CurrentStatus", "N/A"),
            # New fields from tasks.yaml
            "category": project.get("category", "development"),
            "date": today_date,  # Always use today's date
            "keyPoints": key_points,  # Use consistent lowercase keyPoints for frontend
            "partners": partners  # Add the new partners field
        }
    return {
        "name": project.get("name", "Unknown"),
        "location": project.get("location", country),
        "capacity": str(project.get("capacity", "N/A")),
        "developer": project.get("developer", "Unknown"),
        "investment": project.get("investment", "N/A"),
        "timeline": project.get("timeline", "N/A"),
        "source_url": project.get("source_url", ""),
        "source_name": project.get("source_name", country),
        "status": project.get("status", "N/A"),
        # New fields from tasks.yaml
        "category": project.get("category", "development"),
        "date": today_date,  # Always use today's date
        "keyPoints": key_points,  # Use consistent lowercase keyPoints for frontend
        "partners": partners  # Add the new partners field
    }

def standardize_country_result(result: any, country: str) -> Dict:
    """Standardize the country result into a consistent format"""
    try:
        print(f"\n🔍 Standardizing result for {country}")
        print(f"Input result type: {type(result)}")
        
        standardized_projects = []
        
        # Handle different result structures
        projects = []
        print("\n📦 Extracting projects from result")
        
        if isinstance(result, list):
            print("Result is a list, filtering for project entries")
            projects = [p for p in result if isinstance(p, dict) and ('ProjectName' in p or 'name' in p)]
            print(f"Found {len(projects)} projects in list")
            
        elif isinstance(result, dict):
            print("Result is a dictionary, checking known structures")
            if 'Detailed Project List' in result:
                print("Found 'Detailed Project List' structure")
                projects = result.get('Detailed Project List', [])
            elif 'raw_result' in result and 'projects' in result['raw_result']:
                print("Found 'raw_result.projects' structure")
                projects = result['raw_result']['projects']
            elif 'projects' in result:
                print("Found direct 'projects' structure")
                projects = result['projects']
            
            print(f"Extracted {len(projects)} projects from dictionary")
        
        # Generate today's date in MM/DD/YYYY format - use this for ALL projects
        today_date = datetime.now().strftime("%m/%d/%Y")
        print(f"Using today's date for all projects: {today_date}")
        
        # Standardize each project
        print("\n🔄 Standardizing individual projects")
        for project in projects:
            print(f"\nProcessing project: {project.get('ProjectName') or project.get('name', 'Unknown')}")
            
            # Handle key points with more flexibility
            key_points = []
            if "KeyPoints" in project and isinstance(project["KeyPoints"], list):
                key_points = project["KeyPoints"]
            elif "keyPoints" in project and isinstance(project["keyPoints"], list):
                key_points = project["keyPoints"]
            elif "key_points" in project and isinstance(project["key_points"], list):
                key_points = project["key_points"]
            
            # Handle partners with similar flexibility
            partners = []
            if "partners" in project and isinstance(project["partners"], list):
                partners = project["partners"]
            elif "Partners" in project and isinstance(project["Partners"], list):
                partners = project["Partners"]
            
            standardized_project = {
                "name": project.get("ProjectName") or project.get("name", "Unknown"),
                "location": project.get("Location") or project.get("location", country),
                "capacity": str(project.get("Capacity_MW") or project.get("capacity", "N/A")),
                "developer": project.get("Developer") or project.get("developer", "Unknown"),
                "investment": project.get("InvestmentValue") or project.get("investment", "N/A"),
                "timeline": project.get("Timeline") or project.get("timeline", "N/A"),
                "status": project.get("CurrentStatus") or project.get("status", "N/A"),
                "source_url": project.get("source_url", ""),
                "source_name": project.get("source_name", country),
                "category": project.get("category", "development"),
                "date": today_date,  # Always use today's date
                "keyPoints": key_points,
                "partners": partners
            }
            standardized_projects.append(standardized_project)

        print(f"\n✅ Successfully standardized {len(standardized_projects)} projects")
        
        # Extract promising projects from the original result if available
        most_promising_projects = []
        if isinstance(result, dict) and "Summary" in result and "Most promising projects" in result["Summary"]:
            most_promising_projects = result["Summary"]["Most promising projects"]
            print(f"Found {len(most_promising_projects)} promising projects in original result")
        
        # Create final result structure
        standardized_result = {
            "timestamp": str(datetime.now()),
            "search_results": [],  # Will be populated by the accumulator
            "analysis": {
                "Summary": {
                    "Major developers active in the market": list(set(p["developer"] for p in standardized_projects if p["developer"] != "Unknown")),
                    "Most promising projects": most_promising_projects  # Use the original promising projects
                },
                "Detailed Project List": standardized_projects
            }
        }
        
        return standardized_result

    except Exception as e:
        print(f"\n❌ Error in standardize_country_result for {country}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        return create_empty_result()

@app.get("/api/progress")
async def get_progress():
    async def event_generator():
        while True:
            if progress_updates:
                update = progress_updates.pop(0)
                yield {
                    "event": "message",
                    "data": json.dumps(update)
                }
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())

@app.get("/api/projects")
async def get_projects(region: str, technology: str):
    try:
        load_dotenv()
        progress_updates.clear()

        # Validate environment variables
        if not os.getenv('SERPER_API_KEY'):
            raise HTTPException(status_code=500, detail="SERPER_API_KEY not found")
        if not os.getenv('OPENAI_API_KEY'):
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not found")
        
        print(f"\n🌍 Processing region {region}")
        
        if not get_countries_for_region(region):
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

        # Process the region and get results
        result = await process_region(region, technology)
        
        # The accumulator.save_results() already saved the files to the output directory
        # No need to save them again here
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir = output_dir.absolute()  # Get absolute path without resolving symlinks
        output_file = output_dir / 'accumulated_analysis.json'
        search_output_file = output_dir / 'search_results.json'
        
        print("\n💾 Results saved to:", output_file)
        print("\n💾 Search results saved to:", search_output_file)
        await send_progress_update("all", "complete")
        return result

    except Exception as e:
        print(f"\n❌ Error in get_projects: {str(e)}")
        await send_progress_update("all", "error")
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)