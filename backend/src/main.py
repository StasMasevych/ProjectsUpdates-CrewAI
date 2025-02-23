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

async def process_country(country: str, technology: str) -> Dict:
    """Process a single country's data"""
    await send_progress_update(country, "searching")
    energy_crew = EnergyProjectsCrew(country=country, technology=technology)
    crew = energy_crew.create_crew()
    
    await send_progress_update(country, "processing")
    result = crew.kickoff()
    
    await send_progress_update(country, "analyzing")
    # Convert CrewOutput to string if it's not already
    if hasattr(result, '__str__'):
        result = str(result)
    
    # Parse and standardize the result
    parsed_result = json.loads(result)
    return standardize_country_result(parsed_result, country)

def standardize_country_result(result: any, country: str) -> Dict:
    """Standardize the country result into a consistent format"""
    standardized_projects = []
    
    if isinstance(result, list):
        # Handle Bulgaria-style format
        summary = None
        for item in result:
            if isinstance(item, dict):
                if 'summary' in item:
                    summary = item['summary']
                elif 'ProjectName' in item or 'name' in item:
                    project = {
                        "name": item.get("ProjectName") or item.get("name", "Unknown"),
                        "location": item.get("Location") or item.get("location", country),
                        "capacity": str(item.get("Capacity_MW") or item.get("capacity", "N/A")),
                        "developer": item.get("Developer") or item.get("developer", "Unknown"),
                        "investment": item.get("InvestmentValue") or item.get("investment", "N/A"),
                        "timeline": item.get("Timeline") or item.get("timeline", "N/A"),
                        "status": item.get("CurrentStatus") or item.get("status", "N/A"),
                        "source_url": item.get("source_url", ""),
                        "source_name": item.get("source_name", country)
                    }
                    standardized_projects.append(project)
    elif isinstance(result, dict):
        # Handle Romania-style format
        projects = (result.get('raw_result', {}).get('projects', []) or 
                   result.get('projects', []))
        
        for item in projects:
            project = {
                "name": item.get("name", "Unknown"),
                "location": item.get("location", country),
                "capacity": str(item.get("capacity", "N/A")),
                "developer": item.get("developer", "Unknown"),
                "investment": item.get("investment", "N/A"),
                "timeline": item.get("timeline", "N/A"),
                "status": item.get("status", "N/A"),
                "source_url": item.get("source_url", ""),
                "source_name": item.get("source_name", country)
            }
            standardized_projects.append(project)

    # Create standardized result structure
    standardized_result = {
        "timestamp": str(datetime.now()),
        "raw_result": {
            "projects": standardized_projects,
            "search_results": [],  # We can add this if needed
            "token_usage": {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0
            }
        }
    }
    
    print(f"\n📋 Standardized result for {country}:")
    for project in standardized_projects:
        print(f"  - {project['name']}: {project['capacity']} ({project['location']})")
    
    return standardized_result

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
async def get_projects(region: str, technology: str):
    try:
        load_dotenv()
        progress_updates.clear()

        # Validate environment variables
        if not os.getenv('SERPER_API_KEY'):
            raise HTTPException(status_code=500, detail="SERPER_API_KEY not found")
        if not os.getenv('OPENAI_API_KEY'):
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY not found")
        
        countries = get_countries_for_region(region)
        print(f"\n🌍 Processing region {region} with countries: {countries}")
        
        if not countries:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

        all_results = []
        
        # Process each country
        for country in countries:
            print(f"\n🚀 Starting processing for {country}...")
            await send_progress_update(country, "starting")
            try:
                # Get raw result from crew
                energy_crew = EnergyProjectsCrew(country=country, technology=technology)
                crew = energy_crew.create_crew()
                
                await send_progress_update(country, "processing")
                result = crew.kickoff()
                
                # Convert to string if needed and parse
                if hasattr(result, '__str__'):
                    result = str(result)
                country_result = json.loads(result)
                
                # Add to results
                if isinstance(country_result, list):
                    # Skip the summary object if present
                    projects = [p for p in country_result if 'ProjectName' in p]
                    all_results.extend(projects)
                    print(f"Added {len(projects)} projects from {country}")
                    print("Projects:", json.dumps(projects, indent=2))
                
                print(f"✅ Successfully processed {country}")
                
            except Exception as e:
                print(f"❌ Error processing {country}: {str(e)}")
                continue

        await send_progress_update("all", "combining")
        print("\n🔄 Combining results from all countries...")

        # Create final combined result with standardized project structure
        standardized_projects = []
        for project in all_results:
            standardized_project = {
                "name": project.get("ProjectName", project.get("name", "Unknown")),
                "location": project.get("Location", project.get("location", "Unknown")),
                "capacity": str(project.get("Capacity_MW", project.get("capacity", "N/A"))),
                "developer": project.get("Developer", project.get("developer", "Unknown")),
                "investment": project.get("InvestmentValue", project.get("investment", "N/A")),
                "timeline": project.get("Timeline", project.get("timeline", "N/A")),
                "status": project.get("CurrentStatus", project.get("status", "N/A")),
                "source_url": project.get("source_url", ""),
                "source_name": project.get("source_name", "")
            }
            standardized_projects.append(standardized_project)

        combined_result = {
            "timestamp": str(datetime.now()),
            "raw_result": {
                "projects": standardized_projects,
                "search_results": [],
                "token_usage": {
                    "total_tokens": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0
                }
            }
        }

        print(f"\n📊 Final combined results:")
        print(f"Total projects found: {len(standardized_projects)}")
        print(f"Projects per country:")
        for country in countries:
            country_projects = [p for p in standardized_projects 
                              if country.lower() in p['location'].lower()]
            print(f"- {country}: {len(country_projects)} projects")
            for project in country_projects:
                print(f"  - {project['name']}: {project['capacity']}")

        # Save combined results
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / 'analysis_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_result, f, ensure_ascii=False, indent=2)
        
        print("\n💾 Results saved to:", output_file)
        await send_progress_update("all", "complete")
        return combined_result

    except Exception as e:
        print(f"\n❌ Error in get_projects: {str(e)}")
        await send_progress_update("all", "error")
        return {"error": f"Server error: {str(e)}"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)