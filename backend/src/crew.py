from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool, FirecrawlScrapeWebsiteTool
from langchain.chat_models import ChatOpenAI
import yaml
import json
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class EnergyProjectsCrew:
    """Crew for analyzing energy projects"""

    def __init__(self, country: str, technology: str, start_date: Optional[str] = None):
        self.country = country
        self.technology = technology
        self.start_date = start_date
        self.agents_config = {}
        self.tasks_config = {}
        self.load_config()
        self.setup_tools()


    def load_config(self):
        """Load configuration from YAML files"""
        try:
            logger.info(f"Loading configuration files for {self.country}")
            
            # Calculate date for search query
            logging.info(self.start_date)
            search_date = self.start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Load agents config
            agents_path = Path(__file__).parent / 'config' / 'agents.yaml'
            with open(agents_path, 'r') as f:
                self.agents_config = yaml.safe_load(f)
            logger.debug("Loaded agents config")

            # Load tasks config
            tasks_path = Path(__file__).parent / 'config' / 'tasks.yaml'
            with open(tasks_path, 'r') as f:
                self.tasks_config = yaml.safe_load(f)
            logger.debug("Loaded tasks config")

            # Format task descriptions with country, technology and date
            logger.info("\n🔄 Formatting task descriptions")
            for task_key, task in self.tasks_config.items():
                if 'description' in task:
                    try:
                        task['description'] = task['description'].format(
                            country=self.country,
                            technology=self.technology,
                            date=search_date
                        )
                        logger.info(f"✅ Formatted {task_key} description")
                    except KeyError as e:
                        logger.error(f"❌ Error formatting {task_key} description: {str(e)}")
                        raise
                if 'expected_output' in task:
                    try:
                        task['expected_output'] = task['expected_output'].format(
                            country=self.country,
                            technology=self.technology
                        )
                        logger.info(f"✅ Formatted {task_key} expected output")
                    except KeyError as e:
                        logger.error(f"❌ Error formatting {task_key} expected output: {str(e)}")
                        raise

            # Format agent configurations
            logger.info("\n🔄 Formatting agent configurations")
            for agent_key, agent in self.agents_config.items():
                for field in ['role', 'goal', 'backstory']:
                    if field in agent:
                        try:
                            agent[field] = agent[field].format(
                                country=self.country,
                                technology=self.technology
                            )
                            logger.info(f"✅ Formatted {agent_key} {field}")
                        except KeyError as e:
                            logger.error(f"❌ Error formatting {agent_key} {field}: {str(e)}")
                            raise

        except Exception as e:
            logger.error(f"❌ Error in load_config: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            raise

    def setup_tools(self):
        """Setup tools with date-restricted search capabilities"""
        # Use provided start date or calculate date 6 months ago

        self.search_tool = SerperDevTool(
            api_key=os.getenv('SERPER_API_KEY')
        )
        self.scrape_tool = FirecrawlScrapeWebsiteTool()

    def create_agents(self):
        """Creates the required agents for the crew"""
        try:
            logger.info("\n🤖 Creating agents")
            
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
            logger.info("✅ Created analyst with GPT-4")

            return [researcher, scraper, analyst]
            
        except Exception as e:
            logger.error(f"❌ Error creating agents: {str(e)}")
            raise

    def create_tasks(self, agents):
        """Creates the tasks for the crew"""
        try:
            logger.info("\n📋 Creating tasks")
            
            # Get the absolute path to the backend directory
            backend_dir = Path(__file__).parent.parent.absolute()
            output_dir = backend_dir / 'output'
            output_dir.mkdir(exist_ok=True)
            
            logger.info(f"Using output directory: {output_dir}")
            
            # Create tasks with absolute paths
            search_task = Task(
                description=self.tasks_config['search_task']['description'],
                agent=agents[0],
                expected_output=self.tasks_config['search_task']['expected_output'],
                output_file='search_results.json',  # Use relative path
                output_dir=str(output_dir)  # Specify output directory
            )
            logger.info("✅ Created task for web_researcher")

            scrape_task = Task(
                description=self.tasks_config['scraping_task']['description'],
                agent=agents[1],
                expected_output=self.tasks_config['scraping_task']['expected_output']
            )
            logger.info("✅ Created task for web_scraper")

            analysis_task = Task(
                description=self.tasks_config['analysis_task']['description'],
                agent=agents[2],
                expected_output=self.tasks_config['analysis_task']['expected_output'],
                output_file='analysis_results.json',  # Use relative path
                output_dir=str(output_dir)  # Specify output directory
            )
            logger.info("✅ Created task for data_analyst")

            return [search_task, scrape_task, analysis_task]
            
        except Exception as e:
            logger.error(f"❌ Error creating tasks: {str(e)}")
            raise

    def create_crew(self):
        """Creates the energy projects analysis crew"""
        try:
            logger.info("\n👥 Creating crew")
            agents = self.create_agents()
            tasks = self.create_tasks(agents)
            
            crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            logger.info("✅ Successfully created crew")
            return crew
            
        except Exception as e:
            logger.error(f"❌ Error creating crew: {str(e)}")
            raise 