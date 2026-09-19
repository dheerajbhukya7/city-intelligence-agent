# city_agent.py
# A standalone city briefing agent using OpenWeatherMap + Tavily.
# No LLM required — fetches both APIs and prints a combined report.

import os
import requests
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ───────────────────────────────────────────────────
OWM_KEY    = os.getenv("OPENWEATHER_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

tavily = TavilyClient(api_key=TAVILY_KEY)


# ── Tool 1: Weather ────────────────────────────────────────────
def get_weather(city: str) -> dict:
    """Fetch current weather for a city from OpenWeatherMap."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    resp = requests.get(url, params={
        "q":     city,
        "appid": OWM_KEY,
        "units": "metric",
    }, timeout=8)
    resp.raise_for_status()
    return resp.json()


# ── Tool 2: News ───────────────────────────────────────────────
def get_city_news(city: str, days: int = 3) -> list[dict]:
    """Fetch recent news articles about a city via Tavily."""
    result = tavily.search(
        query=f"latest news {city}",
        topic="news",
        days=days,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
    )
    return result.get("results", [])


# ── Reporter: Combine & print results ─────────────────────────
def city_briefing(city: str) -> None:
    """Run both tools and print a combined city briefing."""
    print(f"\n{'─' * 44}")
    print(f"  🌆  City Briefing — {city.title()}")
    print(f"{'─' * 44}\n")

    # ── Weather ────────────────────────────────────────────────
    print("⛅  Weather")
    print("─" * 28)
    try:
        w = get_weather(city)
        name    = f"{w['name']}, {w['sys']['country']}"
        cond    = w["weather"][0]["description"].title()
        temp    = w["main"]["temp"]
        feels   = w["main"]["feels_like"]
        humidity= w["main"]["humidity"]
        wind    = w["wind"]["speed"]
        print(f"  📍 {name}")
        print(f"  🌡  {temp:.1f}°C (feels like {feels:.1f}°C)")
        print(f"  ☁️  {cond}")
        print(f"  💧 Humidity: {humidity}%")
        print(f"  🌬  Wind: {wind} m/s")
    except requests.HTTPError as e:
        print(f"  ❌ Weather fetch failed: {e}")
    except KeyError:
        print("  ❌ Unexpected response format from OpenWeatherMap.")

    # ── News ───────────────────────────────────────────────────
    print(f"\n📰  Recent News (last 3 days)")
    print("─" * 28)
    try:
        articles = get_city_news(city)
        if not articles:
            print("  No recent news found.")
        else:
            for i, a in enumerate(articles, 1):
                pub   = a.get("published_date", "date unknown")
                title = a.get("title", "No title")
                snippet = a.get("content", "")[:160].strip()
                url   = a.get("url", "")
                print(f"\n  {i}. {title}")
                print(f"     📅 {pub}")
                print(f"     {snippet}...")
                if url:
                    print(f"     🔗 {url}")
    except Exception as e:
        print(f"  ❌ News fetch failed: {e}")

    print(f"\n{'─' * 44}\n")


# ── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    city = input("Enter a city name: ").strip()
    if not city:
        print("No city provided. Exiting.")
    else:
        city_briefing(city)

