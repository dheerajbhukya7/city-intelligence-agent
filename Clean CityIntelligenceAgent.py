
import os
import requests

from dotenv import load_dotenv
from tavily import TavilyClient

from langchain_groq import ChatGroq
from langchain_core.tools import StructuredTool
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
)


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================
# 2. CHECK API KEYS
# ============================================================

if not OPENWEATHER_API_KEY:
    raise ValueError(
        "OPENWEATHER_API_KEY is missing from your .env file"
    )

if not TAVILY_API_KEY:
    raise ValueError(
        "TAVILY_API_KEY is missing from your .env file"
    )

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY is missing from your .env file"
    )


# ============================================================
# 3. INITIALIZE TAVILY
# ============================================================

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)


# ============================================================
# 4. WEATHER FUNCTION
# ============================================================

def get_weather(city: str) -> str:
    """
    Get current weather information for a city.
    """

    url = "https://api.openweathermap.org/data/2.5/weather"

    try:

        response = requests.get(
            url,
            params={
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        weather = data["weather"][0]

        return (
            f"City: {data['name']}\n"
            f"Country: {data['sys']['country']}\n"
            f"Temperature: {data['main']['temp']} °C\n"
            f"Feels like: {data['main']['feels_like']} °C\n"
            f"Condition: {weather['description']}\n"
            f"Humidity: {data['main']['humidity']}%\n"
            f"Wind speed: {data['wind']['speed']} m/s"
        )

    except requests.exceptions.HTTPError:

        return (
            f"Could not find weather information "
            f"for '{city}'."
        )

    except requests.exceptions.RequestException as e:

        return f"Weather API error: {e}"

    except Exception as e:

        return f"Unexpected weather error: {e}"


# ============================================================
# 5. NEWS FUNCTION
# ============================================================

def get_city_news(city: str) -> str:
    """
    Get recent news about a city using Tavily.
    """

    try:

        result = tavily.search(
            query=f"latest news in {city}",
            topic="news",
            max_results=5,
        )

        articles = result.get("results", [])

        if not articles:

            return f"No recent news found for {city}."

        news = []

        for index, article in enumerate(
            articles,
            start=1
        ):

            title = article.get(
                "title",
                "No title"
            )

            content = article.get(
                "content",
                "No summary available"
            )

            url = article.get(
                "url",
                ""
            )

            news.append(
                f"{index}. {title}\n"
                f"   {content}\n"
                f"   Source: {url}"
            )

        return "\n\n".join(news)

    except Exception as e:

        return f"News API error: {e}"


# ============================================================
# 6. CREATE STRUCTURED TOOLS
# ============================================================

weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description=(
        "Get current weather information for a city. "
        "Use this when the user asks about temperature, "
        "weather conditions, humidity, wind, or current weather."
    ),
)


news_tool = StructuredTool.from_function(
    func=get_city_news,
    name="get_city_news",
    description=(
        "Get recent news about a city. "
        "Use this when the user asks about current or latest news."
    ),
)


# ============================================================
# 7. TOOL REGISTRY
# ============================================================

tools = [
    weather_tool,
    news_tool,
]

tool_map = {
    tool.name: tool
    for tool in tools
}


# ============================================================
# 8. INITIALIZE GROQ
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)


# ============================================================
# 9. BIND TOOLS
# ============================================================

llm_with_tools = llm.bind_tools(tools)


# ============================================================
# 10. SYSTEM PROMPT
# ============================================================

system_message = SystemMessage(
    content="""
You are a City Intelligence Assistant.

Your job is to provide accurate and useful information
about cities.

Available tools:

1. get_weather
   - Gets current weather information.

2. get_city_news
   - Gets recent news about a city.

Rules:

- Use get_weather when the user asks about weather.
- Use get_city_news when the user asks about news.
- If the user asks for both weather and news, use both tools.
- If the user provides only a city name, remember that city.
- If the user says "both", use both tools for the most recently
  mentioned city.
- If the user asks a general question unrelated to city
  intelligence, answer normally without calling a tool.
- Never invent current weather or news.
- Clearly distinguish retrieved information from inference.
- Do not claim that two events are causally related unless
  the retrieved information supports that conclusion.
"""
)


# ============================================================
# 11. CONVERSATION HISTORY
# ============================================================

messages = [
    system_message
]


# ============================================================
# 12. DISPLAY HEADER
# ============================================================

print()
print("=" * 60)
print("CITY INTELLIGENCE AGENT")
print("=" * 60)
print("Weather : OpenWeather")
print("News    : Tavily")
print("LLM     : Groq")
print("Human   : Tool approval")
print()
print("Type 'exit' to quit.")
print("=" * 60)


# ============================================================
# 13. MAIN CHAT LOOP
# ============================================================

while True:

    try:

        user_input = input("\nYou: ").strip()

        # ----------------------------------------------------
        # Empty input
        # ----------------------------------------------------

        if not user_input:
            continue

        # ----------------------------------------------------
        # Exit
        # ----------------------------------------------------

        if user_input.lower() in {
            "exit",
            "quit",
        }:

            print("\nGoodbye!")
            break

        # ----------------------------------------------------
        # Add user message
        # ----------------------------------------------------

        messages.append(
            HumanMessage(
                content=user_input
            )
        )

        # ====================================================
        # AGENT LOOP
        # ====================================================

        while True:

            print("\nAgent is thinking...")

            try:

                response = llm_with_tools.invoke(
                    messages
                )

            except Exception as e:

                print(
                    f"\nLLM Error: {e}"
                )

                break

            # ------------------------------------------------
            # Save AI response
            # ------------------------------------------------

            messages.append(response)

            # =================================================
            # NO TOOL REQUIRED
            # =================================================

            if not response.tool_calls:

                print(
                    f"\nAgent: {response.content}"
                )

                break

            # =================================================
            # TOOL CALLS
            # =================================================

            for tool_call in response.tool_calls:

                tool_name = tool_call["name"]

                tool_args = tool_call.get(
                    "args",
                    {}
                )

                tool_call_id = tool_call["id"]

                print()
                print("-" * 60)
                print("TOOL REQUEST")
                print("-" * 60)

                print(
                    f"Tool      : {tool_name}"
                )

                print(
                    f"Arguments : {tool_args}"
                )

                # --------------------------------------------
                # Check tool
                # --------------------------------------------

                if tool_name not in tool_map:

                    print(
                        f"Unknown tool: {tool_name}"
                    )

                    messages.append(
                        ToolMessage(
                            content=(
                                f"Unknown tool: {tool_name}"
                            ),
                            tool_call_id=tool_call_id,
                        )
                    )

                    continue

                # --------------------------------------------
                # Human approval
                # --------------------------------------------

                approval = input(
                    "Approve tool execution? (y/n): "
                ).strip().lower()

                # --------------------------------------------
                # DENIED
                # --------------------------------------------

                if approval not in {
                    "y",
                    "yes",
                }:

                    print(
                        "Tool execution denied."
                    )

                    messages.append(
                        ToolMessage(
                            content=(
                                "The user denied permission "
                                "to execute this tool."
                            ),
                            tool_call_id=tool_call_id,
                        )
                    )

                    continue

                # --------------------------------------------
                # EXECUTE TOOL
                # --------------------------------------------

                print(
                    f"Executing {tool_name}..."
                )

                try:

                    tool_result = tool_map[
                        tool_name
                    ].invoke(
                        tool_args
                    )

                except Exception as e:

                    tool_result = (
                        f"Tool execution failed: {e}"
                    )

                print(
                    "Tool execution completed."
                )

                # --------------------------------------------
                # Send result back to LLM
                # --------------------------------------------

                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call_id,
                    )
                )

            # ------------------------------------------------
            # Continue agent loop
            # ------------------------------------------------

            continue

    except KeyboardInterrupt:

        print(
            "\n\nProgram stopped."
        )

        break

    except Exception as e:

        print(
            f"\nUnexpected error: {e}"
        )