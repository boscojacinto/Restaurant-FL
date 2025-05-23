from smolagents import CodeAgent, ToolCallingAgent, OpenAIServerModel, DuckDuckGoSearchTool, FinalAnswerTool, HfApiModel, load_tool, tool
import datetime
import requests
import pytz
import yaml

@tool
def my_custom_tool(arg1:str, arg2:int)-> str: # it's important to specify the return type
    # Keep this format for the tool description / args description but feel free to modify the tool
    """A tool that does nothing yet 
    Args:
        arg1: the first argument
        arg2: the second argument
    """
    return "What magic will you build ?"

@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """A tool that fetches the current local time in a specified timezone.
    Args:
        timezone: A string representing a valid timezone (e.g., 'America/New_York').
    """
    try:
        # Create timezone object
        tz = pytz.timezone(timezone)
        # Get current time in that timezone
        local_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"The current local time in {timezone} is: {local_time}"
    except Exception as e:
        return f"Error fetching time for timezone '{timezone}': {str(e)}"

@tool
def suggest_menu(occasion: str) -> str:
	"""
	Suggests a menu based on the occasion.
	Args:
		occasion (str): The type of occasion for the party. Allowed values are:
						- "casual": Menu for casual party
						- "formal": Menu for formal party
						- "superhero": Menu for superhero party
						- "custom": Custom menu
	"""

	if occasion == "casual":
		return "Pizza, snacks and drinks."
	elif occasion == "formal":
		return "3-course dinner with wine and dessert."
	elif occasion == "superhero":
		return "Buffet with high energy and healthy food."
	else:
		return "Custom menu for the butler."


final_answer = FinalAnswerTool()
duckduck_tool = DuckDuckGoSearchTool()

model = OpenAIServerModel(
			model_id="PowerInfer/SmallThinker-3B-Preview",
			api_base="http://127.0.0.1:5000/v1",
			api_key="sk-no-key-required",
			max_tokens=2096,
			temperature=0.5,
			custom_role_conversions=None,
		)

with open("prompts.yaml", 'r') as stream:
	prompt_templates = yaml.safe_load(stream)

agent = CodeAgent(
		model=model,
		tools=[final_answer, DuckDuckGoSearchTool()],
		max_steps=6,
		verbosity_level=2,
		grammar=None,
		planning_interval=None,
		name=None,
		description=None,
		prompt_templates=prompt_templates

)

#agent.run("What is the current time in New York")
agent.run("Search for the best music recommendations for a party at the Wayne's mansion.")
#agent.run("Prepare a formal menu for the party.")
