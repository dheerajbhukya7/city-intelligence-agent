import os
import requests
from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

load_dotenv()

class CityIntelligenceEngine:
    def __init__(self):
        self.owm_key = os.getenv("OPENWEATHER_API_KEY")
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

        if not all([self.owm_key, self.tavily_key, self.groq_key]):
            raise ValueError("Missing API keys in .env")

        self.tavily = TavilyClient(api_key=self.tavily_key)
        self.llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

        self.tools = [
            StructuredTool.from_function(func=self.get_weather, name="get_weather", description="Get weather for a city."),
            StructuredTool.from_function(func=self.get_city_news, name="get_city_news", description="Get news for a city.")
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_map = {t.name: t for t in self.tools}
        self.messages = [SystemMessage(content="You are a City Intelligence Assistant.")]

    def get_weather(self, city: str) -> str:
        url = "https://api.openweathermap.org/data/2.5/weather"
        try:
            response = requests.get(url, params={"q": city, "appid": self.owm_key, "units": "metric"}, timeout=10)
            response.raise_for_status()
            data = response.json()
            import json
            return json.dumps({
                "city": data['name'],
                "temp": data['main']['temp'],
                "condition": data['weather'][0]['description'],
                "humidity": data['main']['humidity'],
                "wind_speed": data['wind']['speed']
            })
        except Exception as e:
            return f"Weather Error: {e}"

    def get_city_news(self, city: str) -> str:
        try:
            result = self.tavily.search(query=f"latest news in {city}", topic="news", max_results=5)
            articles = result.get("results", [])
            import json
            return json.dumps([{"title": a.get("title"), "url": a.get("url"), "content": a.get("content")} for a in articles])
        except Exception as e:
            return f"News Error: {e}"

    def run_agent_turn(self, messages):
        # Aggressive trimming to stay under Groq TPM limit
        # Keep only the last TURN (Human + AI) and the System message
        if len(messages) > 3:
            messages = [messages[0]] + messages[-2:]

        return self.llm_with_tools.invoke(messages)

    def execute_tool(self, tool_call):
        print(f"DEBUG: Executing tool {tool_call['name']} with args {tool_call['args']}")
        result = self.tool_map[tool_call["name"]].invoke(tool_call["args"])
        print(f"DEBUG: Tool result: {result}")
        return result
