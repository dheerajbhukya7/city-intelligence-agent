from dotenv import load_dotenv
import os
import requests

load_dotenv()

from langchain_groq import ChatGroq
from langchain.tools import tool
from tavily import TavilyClient
from langchain.agents import create_agent

# =========================
# 🌦️ Weather Tool
# =========================

from weather import fetch_weather

@tool
def get_weather(city: str) -> str:
    """Get current weather of a city."""
    return fetch_weather(city)


# =========================
# 📰 News Tool (Tavily)
# =========================

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def get_news(city: str) -> str:
    """Get latest news about a city"""
    
    response = tavily_client.search(
        query=f"latest news in {city}",
        search_depth="basic",
        max_results=3
    )
    
    results = response.get("results", [])
    
    if not results:
        return f"No news found for {city}"
    
    news_list = []
    
    for r in results:
        title = r.get("title", "No title")
        url = r.get("url", "")
        snippet = r.get("content", "")
        
        news_list.append(
            f"- {title}\n  🔗 {url}\n  📝 {snippet[:100]}..."
        )
    
    return f"Latest news in {city}:\n\n" + "\n\n".join(news_list)
# =========================
# 🧠 LLM Setup
# =========================

llm = ChatGroq(model="openai/gpt-oss-120b")
SYSTEM_PROMPT = """
You are an intelligent City Intelligence Assistant.

You have access to two external tools:

- get_weather(city): retrieves current weather information.
- get_news(city): retrieves recent news about a city.

TOOL RULES:

1. If the user asks specifically about weather:
   → Call get_weather.

2. If the user asks specifically about news:
   → Call get_news.

3. If the user asks for a city overview, city briefing, or general
   information about a city:
   → Call BOTH get_weather and get_news.

4. If the user asks for current/latest/recent information:
   → Use the appropriate tool. Never rely on your internal knowledge
     for information that can change over time.

5. Never fabricate weather data, news articles, URLs, temperatures,
   or other real-time information.

6. If a tool returns an error:
   → Explain that the requested external information could not be retrieved.
   → Do not invent replacement information.

RESPONSE FORMAT:

For a city briefing, respond using:

## 🌦️ Weather
- Condition:
- Temperature:

## 📰 Latest News
- News headline
- Brief summary
- Source URL

## 📍 City Insight
Provide a short summary connecting the weather and news when there
is a meaningful connection.

For simple questions, do not force this full format.

STYLE:

- Be concise and informative.
- Use clear headings and bullet points.
- Do not repeat the user's question.
- Use °C for temperature.
- Preserve URLs returned by the news tool.
- If the user provides an ambiguous city name, ask for clarification.
""" 

agent = create_agent(
    llm,
    tools = [get_weather,get_news],
    system_prompt= SYSTEM_PROMPT
)


