from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from langchain.chat_models import ChatOpenAI
import yaml
import json
import os
from pathlib import Path

class RomanianSolarCrew:
    """Crew for analyzing Romanian solar projects"""

    def __init__(self):
        self.load_config()
        self.setup_tools()

    def load_config(self):
        config_path = Path(__file__).parent / 'config'
        with open(config_path / 'agents.yaml', 'r') as f:
            self.agents_config = yaml.safe_load(f)
        with open(config_path / 'tasks.yaml', 'r') as f:
            self.tasks_config = yaml.safe_load(f)

    def setup_tools(self):
        # Setup Serper search tool
        self.search_tool = SerperDevTool(api_key=os.getenv('SERPER_API_KEY'))
        
        # Setup web scraping tool
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
        tasks = [
            Task(
                description=self.tasks_config['search_task']['description'],
                agent=agents[0],
                expected_output=self.tasks_config['search_task']['expected_output'],
                output_file='search_results.json'
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
                output_file='analysis_results.json'
            )
        ]
        return tasks

    def create_crew(self):
        """Creates the Romanian Solar Projects Analysis crew"""
        agents = self.create_agents()
        tasks = self.create_tasks(agents)
        
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        ) 