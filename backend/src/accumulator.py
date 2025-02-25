from typing import Dict, List
import json
from pathlib import Path
from datetime import datetime

class ResultsAccumulator:
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / 'output'
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize accumulator storage with the correct structure
        self.accumulated_search_results = []
        self.accumulated_analysis = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_mw": 0.0,
                "total_investment": 0.0,
                "countries_analyzed": [],
                "major_developers": set(),
                "project_locations": []
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

            # Standardize and store projects
            standardized_projects = []
            for project in projects:
                standardized_project = {
                    "name": project.get("ProjectName", project.get("name", "Unknown")),
                    "location": project.get("Location", project.get("location", country)),
                    "capacity": str(project.get("Capacity_MW", project.get("capacity", "N/A"))),
                    "developer": project.get("Developer", project.get("developer", "Unknown")),
                    "investment": project.get("InvestmentValue", project.get("investment", "N/A")),
                    "timeline": project.get("Timeline", project.get("timeline", "N/A")),
                    "status": project.get("CurrentStatus", project.get("status", "N/A")),
                    "source_url": project.get("source_url", ""),
                    "source_name": project.get("source_name", country)
                }
                standardized_projects.append(standardized_project)

            # Store standardized projects for this country
            self.accumulated_analysis["projects_by_country"][country] = standardized_projects

            # Update summary metrics
            for project in standardized_projects:
                # Update total MW
                try:
                    mw = float(project["capacity"].split()[0])
                    self.accumulated_analysis["summary"]["total_mw"] += mw
                except (ValueError, IndexError):
                    pass

                # Update project locations
                if project["location"] not in self.accumulated_analysis["summary"]["project_locations"]:
                    self.accumulated_analysis["summary"]["project_locations"].append(project["location"])

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

        # Save to file
        output_path = self.output_dir / 'accumulated_analysis.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2) 