import warnings
from pydantic import PydanticDeprecatedSince20
from typing import List, Dict, Optional
import os
from datetime import datetime
import logging
from config.logging_config import setup_logging

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
from accumulator import ResultsAccumulator

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

# Setup logging at the start of the application
logger = setup_logging()

async def send_progress_update(country: str, step: str):
    progress_updates.append({"country": country, "step": step})

async def process_region(region: str, technology: str, start_date: Optional[str] = None) -> Dict:
    """Process all countries in a region"""
    countries = get_countries_for_region(region)
    accumulator = ResultsAccumulator()
    
    for country in countries:
        await send_progress_update(country, "starting")
        try:
            # Process single country with optional start date
            result = await process_country(country, technology, start_date)
            
            # Add results to accumulator
            accumulator.add_country_results(
                country=country,
                search_results=result.get("search_results", []),
                analysis_results=result.get("analysis", {})
            )
            
            await send_progress_update(country, "complete")
        except Exception as e:
            await send_progress_update(country, "error")
            logger.error(f"Error processing {country}: {str(e)}")
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
                "total_mw": final_results["analysis"]["summary"]["total_mw"],
                "total_investment": final_results["analysis"]["summary"]["total_investment"],
                "countries_analyzed": final_results["analysis"]["summary"]["countries_analyzed"],
                "major_developers": list(final_results["analysis"]["summary"]["major_developers"]),
                "project_locations": final_results["analysis"]["summary"]["project_locations"]
            },
            "projects_by_country": final_results["analysis"]["projects_by_country"]
        }
    }

async def process_country(country: str, technology: str, startDate: Optional[str] = None) -> Dict:
    """Process a single country's data"""
    try:
        print(f"\n📍 Starting process for {country}")
        await send_progress_update(country, "searching")
        
        print(f"🔧 Creating crew for {country}")
        energy_crew = EnergyProjectsCrew(country=country, technology=technology, start_date=startDate)
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
                print("\n✅ Successfully parsed JSON:")
                print(json.dumps(parsed_result, indent=2))
            else:
                print("\n❌ Could not find JSON content in result")
                return create_empty_result()
                
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parsing error for {country}")
            print(f"Error details: {str(e)}")
            return create_empty_result()
        except Exception as e:
            print(f"\n❌ Error processing result for {country}: {str(e)}")
            return create_empty_result()
        
        print("\n🔄 Standardizing result structure")
        standardized_result = standardize_country_result(parsed_result, country)
        
        print("\n📊 Final standardized result structure:")
        print(json.dumps(standardized_result, indent=2))
        
        return standardized_result

    except Exception as e:
        print(f"\n❌ Error in process_country for {country}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        return create_empty_result()

def create_empty_result() -> Dict:
    """Create an empty result structure"""
    return {
        "search_results": [],
        "analysis": {
            "Summary": {
                "Total MW of new projects": 0,
                "Total investment value": "0",
                "Key trends in project locations": [],
                "Major developers active in the market": [],
                "Project development timelines": []
            },
            "Detailed Project List": []
        }
    }

def standardize_country_result(result: any, country: str) -> Dict:
    """Standardize the country result into a consistent format"""
    try:
        print(f"\n🔍 Standardizing result for {country}")
        print(f"Input result type: {type(result)}")
        print("Input result structure:")
        print(json.dumps(result, indent=2))
        
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
        
        print("\n📋 Extracted projects:")
        print(json.dumps(projects, indent=2))
        
        # Standardize each project
        print("\n🔄 Standardizing individual projects")
        for project in projects:
            print(f"\nProcessing project: {project.get('ProjectName') or project.get('name', 'Unknown')}")
            standardized_project = {
                "name": project.get("ProjectName") or project.get("name", "Unknown"),
                "location": project.get("Location") or project.get("location", country),
                "capacity": str(project.get("Capacity_MW") or project.get("capacity", "N/A")),
                "developer": project.get("Developer") or project.get("developer", "Unknown"),
                "investment": project.get("InvestmentValue") or project.get("investment", "N/A"),
                "timeline": project.get("Timeline") or project.get("timeline", "N/A"),
                "status": project.get("CurrentStatus") or project.get("status", "N/A"),
                "source_url": project.get("source_url", ""),
                "source_name": project.get("source_name", country)
            }
            standardized_projects.append(standardized_project)
            print("Standardized project:", json.dumps(standardized_project, indent=2))

        print(f"\n✅ Successfully standardized {len(standardized_projects)} projects")
        
        # Create final result structure
        standardized_result = {
            "timestamp": str(datetime.now()),
            "search_results": [],  # Will be populated by the accumulator
            "analysis": {
                "Summary": {
                    "Total MW of new projects": sum(float(p["capacity"].split()[0]) 
                                                  for p in standardized_projects 
                                                  if p["capacity"] != "N/A" and p["capacity"].split()[0].replace('.','',1).isdigit()),
                    "Total investment value": "0",  # Will be calculated in accumulator
                    "Key trends in project locations": list(set(p["location"] for p in standardized_projects)),
                    "Major developers active in the market": list(set(p["developer"] for p in standardized_projects if p["developer"] != "Unknown")),
                    "Project development timelines": list(set(p["timeline"] for p in standardized_projects if p["timeline"] != "N/A"))
                },
                "Detailed Project List": standardized_projects
            }
        }
        
        print("\n📊 Final result structure:")
        print(json.dumps(standardized_result, indent=2))
        return standardized_result

    except Exception as e:
        print(f"\n❌ Error in standardize_country_result for {country}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        return create_empty_result()

def normalize_project(project: Dict, country: str) -> Dict:
    """Normalize project data to a consistent format"""
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
            "status": project.get("CurrentStatus", "N/A")
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
        "status": project.get("status", "N/A")
    }

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
async def get_projects(
    region: str, 
    technology: str,
    startDate: Optional[str] = None  # Make start date optional
):
    try:
        load_dotenv()
        progress_updates.clear()

        # Validate environment variables
        if not os.getenv('SERPER_API_KEY'):
            logger.error("SERPER_API_KEY not found in environment variables")
            raise HTTPException(status_code=500, detail="SERPER_API_KEY not found")
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not found")
        
        logger.info(f"Processing region: {region}")
        
        if not get_countries_for_region(region):
            logger.error(f"Invalid region: {region}")
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

        # Process the region and get results
        logger.info(f"Starting processing for region {region} with technology {technology}")
        result = await process_region(region, technology, startDate)
        
        # Save the results
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / 'analysis_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to: {output_file}")
        await send_progress_update("all", "complete")
        return result

    except Exception as e:
        logger.error(f"Error in get_projects: {str(e)}", exc_info=True)
        await send_progress_update("all", "error")
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    