from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain_community.chat_models import ChatOpenAI
import yaml
import json
import os
from pathlib import Path

class EnergyProjectsCrew:
    """Crew for analyzing energy projects"""

    def __init__(self, country: str, technology: str):
        self.country = country
        self.technology = technology
        self.load_config()
        self.setup_tools()

    def load_config(self):
        config_path = Path(__file__).parent / 'config'
        
        # Load and format agents config
        with open(config_path / 'agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
            # Format each agent's configuration with dynamic values
            for agent_key in self.agents_config:
                agent = self.agents_config[agent_key]
                for key in ['goal', 'backstory']:
                    if key in agent:
                        agent[key] = agent[key].format(
                            country=self.country,
                            technology=self.technology
                        )

        # Load and format tasks config
        with open(config_path / 'tasks.yaml', 'r') as f:
            self.tasks_config = yaml.safe_load(f)
            # Format each task's configuration with dynamic values
            for task_key in self.tasks_config:
                task = self.tasks_config[task_key]
                if 'description' in task:
                    task['description'] = task['description'].format(
                        country=self.country,
                        technology=self.technology
                    )
                if 'expected_output' in task:
                    task['expected_output'] = task['expected_output'].format(
                        country=self.country,
                        technology=self.technology
                    )

    def setup_tools(self):
        self.search_tool = SerperDevTool(api_key=os.getenv('SERPER_API_KEY'))
        self.scrape_tool = ScrapeWebsiteTool()

    def create_agents(self):
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
            backstory=self.agents_config['data_analyst']['backstory'],
            llm=ChatOpenAI(temperature=0),
            verbose=True
        )

        return [researcher, scraper, analyst]

    def create_tasks(self, agents):
        output_dir = Path(__file__).parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        tasks = [
            Task(
                description=self.tasks_config['search_task']['description'],
                agent=agents[0],
                expected_output=self.tasks_config['search_task']['expected_output'],
                output_file=str(output_dir / 'search_results.json')
            ),
            Task(
                description=self.tasks_config['scraping_task']['description'],
                agent=agents[1],
                expected_output=self.tasks_config['scraping_task']['expected_output'],
            ),
            Task(
                description=self.tasks_config['analysis_task']['description'],
                agent=agents[2],
                expected_output=self.tasks_config['analysis_task']['expected_output'],
                output_file=str(output_dir / 'analysis_results.json')
            )
        ]
        return tasks

    def create_crew(self):
        """Creates the energy projects analysis crew"""
        agents = self.create_agents()
        tasks = self.create_tasks(agents)
        
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        ) 