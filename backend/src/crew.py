from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain.chat_models import ChatOpenAI
import yaml
import json
import os
from pathlib import Path

class EnergyProjectsCrew:
    """Crew for analyzing energy projects"""

    def __init__(self, country: str, technology: str):
        self.country = country
        self.technology = technology
        self.agents_config = {}
        self.tasks_config = {}
        self.load_config()
        self.setup_tools()

    def load_config(self):
        """Load configuration from YAML files"""
        try:
            print(f"\n📝 Loading configuration files for {self.country}")
            
            # Load agents config
            agents_path = Path(__file__).parent / 'config' / 'agents.yaml'
            with open(agents_path, 'r') as f:
                self.agents_config = yaml.safe_load(f)
            print("✅ Loaded agents config")

            # Load tasks config
            tasks_path = Path(__file__).parent / 'config' / 'tasks.yaml'
            with open(tasks_path, 'r') as f:
                self.tasks_config = yaml.safe_load(f)
            print("✅ Loaded tasks config")

            # Format task descriptions with country and technology
            print("\n🔄 Formatting task descriptions")
            for task_key, task in self.tasks_config.items():
                if 'description' in task:
                    try:
                        task['description'] = task['description'].format(
                            country=self.country,
                            technology=self.technology
                        )
                        print(f"✅ Formatted {task_key} description")
                    except KeyError as e:
                        print(f"❌ Error formatting {task_key} description: {str(e)}")
                        raise
                if 'expected_output' in task:
                    try:
                        task['expected_output'] = task['expected_output'].format(
                            country=self.country,
                            technology=self.technology
                        )
                        print(f"✅ Formatted {task_key} expected output")
                    except KeyError as e:
                        print(f"❌ Error formatting {task_key} expected output: {str(e)}")
                        raise

            # Format agent configurations
            print("\n🔄 Formatting agent configurations")
            for agent_key, agent in self.agents_config.items():
                for field in ['role', 'goal', 'backstory']:
                    if field in agent:
                        try:
                            agent[field] = agent[field].format(
                                country=self.country,
                                technology=self.technology
                            )
                            print(f"✅ Formatted {agent_key} {field}")
                        except KeyError as e:
                            print(f"❌ Error formatting {agent_key} {field}: {str(e)}")
                            raise

        except Exception as e:
            print(f"❌ Error in load_config: {str(e)}")
            print("Full error details:")
            import traceback
            traceback.print_exc()
            raise

    def setup_tools(self):
        self.search_tool = SerperDevTool(api_key=os.getenv('SERPER_API_KEY'))
        self.scrape_tool = ScrapeWebsiteTool()

    def create_agents(self):
        """Creates the required agents for the crew"""
        try:
            print("\n🤖 Creating agents")
            
            researcher = Agent(
                role=self.agents_config['web_researcher']['role'],
                goal=self.agents_config['web_researcher']['goal'],
                backstory=self.agents_config['web_researcher']['backstory'],
                tools=[self.search_tool],
                verbose=True
            )

            scraper = Agent(
                role=self.agents_config['web_scraper']['role'],
                goal=self.agents_config['web_scraper']['goal'],
                backstory=self.agents_config['web_scraper']['backstory'],
                tools=[self.scrape_tool],
                verbose=True
            )
      
            analyst = Agent(
                role=self.agents_config['data_analyst']['role'],
                goal=self.agents_config['data_analyst']['goal'],
                backstory="""You are a precise data analyst specializing in energy projects.
                Your key responsibilities:
                1. Verify all data sources are reliable and accessible
                2. Ensure all URLs are complete and working (starting with https://)""",
                llm=ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0
                ),
                verbose=True
            )
            print("✅ Created analyst with GPT-4")

            return [researcher, scraper, analyst]
            
        except Exception as e:
            print(f"❌ Error creating agents: {str(e)}")
            raise

    def create_tasks(self, agents):
        """Creates the tasks for the crew"""
        try:
            print("\n📋 Creating tasks")
            
            # Create tasks without the extra commas that were creating tuples
            search_task = Task(
                description=self.tasks_config['search_task']['description'],
                agent=agents[0],
                expected_output=self.tasks_config['search_task']['expected_output'],
                output_file='search_results.json'
            )
            print("✅ Created task for web_researcher")

            scrape_task = Task(
                description=self.tasks_config['scraping_task']['description'],
                agent=agents[1],
                expected_output=self.tasks_config['scraping_task']['expected_output']
            )
            print("✅ Created task for web_scraper")

            analysis_task = Task(
                description=self.tasks_config['analysis_task']['description'],
                agent=agents[2],
                expected_output=self.tasks_config['analysis_task']['expected_output'],
                output_file='analysis_results.json'
            )
            print("✅ Created task for data_analyst")

            return [search_task, scrape_task, analysis_task]
            
        except Exception as e:
            print(f"❌ Error creating tasks: {str(e)}")
            raise

    def create_crew(self):
        """Creates the energy projects analysis crew"""
        try:
            print("\n👥 Creating crew")
            agents = self.create_agents()
            tasks = self.create_tasks(agents)
            
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            print("✅ Successfully created crew")
            return crew
            
        except Exception as e:
            print(f"❌ Error creating crew: {str(e)}")
            raise

    def search_task(self, context):
        # ... existing code ...
        
        # Make sure to return the search results in a structured format
        return {
            "search_results": search_results,
            "message": f"Found {len(search_results)} search results for {self.country}"
        } 