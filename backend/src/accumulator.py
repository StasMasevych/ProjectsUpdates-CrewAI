from typing import Dict, List
import json
from pathlib import Path
from datetime import datetime

class ResultsAccumulator:
    def __init__(self):
        # Use absolute() instead of resolve() to get absolute path
        self.output_dir = Path(__file__).parent.parent / 'output'
        self.output_dir = self.output_dir.absolute()  # Get absolute path without resolving symlinks
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize accumulator storage with the correct structure
        self.accumulated_search_results = []
        self.accumulated_analysis = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "countries_analyzed": [],
                "major_developers": set(),
                "most_promising_projects": [],
            },
            "projects_by_country": {}
        }

    def add_country_results(self, country: str, search_results: List[Dict], analysis_results: Dict) -> None:
        """Add results from a single country to the accumulator"""
        # Add country to analyzed list if not already present
        if country not in self.accumulated_analysis["summary"]["countries_analyzed"]:
            self.accumulated_analysis["summary"]["countries_analyzed"].append(country)

        # Accumulate search results with country tag
        for result in search_results:
            result["country"] = country
            self.accumulated_search_results.append(result)

        # Process the analysis results
        if isinstance(analysis_results, dict):
            # Extract projects
            projects = []
            if "Detailed Project List" in analysis_results:
                projects = analysis_results["Detailed Project List"]
            elif "raw_result" in analysis_results and "projects" in analysis_results["raw_result"]:
                projects = analysis_results["raw_result"]["projects"]

            # Extract most promising projects from Summary if available
            if "Summary" in analysis_results:
                summary = analysis_results["Summary"]
                
                # Extract major developers
                if "Major developers active in the market" in summary:
                    developers = summary["Major developers active in the market"]
                    if isinstance(developers, list):
                        for dev in developers:
                            self.accumulated_analysis["summary"]["major_developers"].add(dev)
                
                # Extract most promising projects - directly use the AI's reasoning
                if "Most promising projects" in summary:
                    promising_projects = summary["Most promising projects"]
                    print(f"\n🌟 Found promising projects for {country}: {promising_projects}")
                    
                    if isinstance(promising_projects, list) and promising_projects:
                        # Add country prefix to each project if not already included
                        country_projects = []
                        for project in promising_projects:
                            if isinstance(project, str):
                                if not project.startswith(f"{country}:"):
                                    country_projects.append(f"{country}: {project}")
                                else:
                                    country_projects.append(project)
                        
                        if country_projects:
                            self.accumulated_analysis["summary"]["most_promising_projects"].extend(country_projects)
                            print(f"✅ Added {len(country_projects)} promising projects from {country}")
                            print(f"Current most_promising_projects: {self.accumulated_analysis['summary']['most_promising_projects']}")
                        else:
                            print(f"⚠️ No valid promising projects found for {country}")
                    else:
                        print(f"⚠️ No promising projects list found for {country} or invalid format")

            # Generate today's date in MM/DD/YYYY format - use this for ALL projects
            today_date = datetime.now().strftime("%m/%d/%Y")
            print(f"Using today's date for all projects: {today_date}")

            # Standardize and store projects
            standardized_projects = []
            for project in projects:
                # Debug the project structure
                print(f"Processing project: {project.get('ProjectName', project.get('name', 'Unknown'))}")
                
                # Check for KeyPoints with capital K as in tasks.yaml and analysis_results.json
                key_points = []
                if "KeyPoints" in project and isinstance(project["KeyPoints"], list):
                    key_points = project["KeyPoints"]
                elif "keyPoints" in project and isinstance(project["keyPoints"], list):
                    key_points = project["keyPoints"]
                else:
                    # Also check for key_points in the original format from analysis_results.json
                    if "key_points" in project and isinstance(project["key_points"], list):
                        key_points = project["key_points"]
                
                # Ensure we have a valid list of key points
                if not isinstance(key_points, list):
                    key_points = []
                
                # Check for partners field with more flexibility
                partners = []
                if "partners" in project and isinstance(project["partners"], list):
                    partners = project["partners"]
                elif "Partners" in project and isinstance(project["Partners"], list):
                    partners = project["Partners"]
                
                standardized_project = {
                    "name": project.get("ProjectName", project.get("name", "Unknown")),
                    "location": project.get("Location", project.get("location", country)),
                    "capacity": str(project.get("Capacity_MW", project.get("capacity", "N/A"))),
                    "developer": project.get("Developer", project.get("developer", "Unknown")),
                    "investment": project.get("InvestmentValue", project.get("investment", "N/A")),
                    "timeline": project.get("Timeline", project.get("timeline", "N/A")),
                    "status": project.get("CurrentStatus", project.get("status", "N/A")),
                    "source_url": project.get("source_url", ""),
                    "source_name": project.get("source_name", country),
                    # New fields from tasks.yaml
                    "category": project.get("category", "development"),
                    "date": today_date,  # Always use today's date
                    "keyPoints": key_points,  # Use consistent lowercase keyPoints for frontend
                    "partners": partners  # Add the partners field
                }
                standardized_projects.append(standardized_project)

            # Store standardized projects for this country
            self.accumulated_analysis["projects_by_country"][country] = standardized_projects

            # Update summary metrics
            for project in standardized_projects:
                # Update major developers
                if project["developer"] != "Unknown":
                    self.accumulated_analysis["summary"]["major_developers"].add(project["developer"])

    def get_results(self) -> Dict:
        """Get the current accumulated results"""
        return {
            "search_results": self.accumulated_search_results,
            "analysis": self.accumulated_analysis
        }

    def save_results(self) -> None:
        """Save accumulated results to files"""
        # Convert set to list for JSON serialization
        results = self.get_results()
        results["analysis"]["summary"]["major_developers"] = list(
            results["analysis"]["summary"]["major_developers"]
        )

        # Save accumulated analysis to file
        output_path = self.output_dir / 'accumulated_analysis.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Also save accumulated search results to output directory
        search_output_path = self.output_dir / 'search_results.json'
        with open(search_output_path, 'w', encoding='utf-8') as f:
            json.dump(self.accumulated_search_results, f, ensure_ascii=False, indent=2) 