import streamlit as st
import os
import requests
from tavily import TavilyClient
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import time

# ── Setup ───────────────────────────────────────────────────────
load_dotenv()
OWM_KEY    = os.getenv("OPENWEATHER_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

tavily = TavilyClient(api_key=TAVILY_KEY)

st.set_page_config(page_title="City Briefing", page_icon="🌆", layout="wide")

# ── Optimized Tool Functions ────────────────────────────────────

@st.cache_data(ttl=600)
def get_weather(city: str) -> dict:
    """Fetch current weather for a city."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    # City name is normalized in the calling function
    resp = requests.get(url, params={
        "q":     city,
        "appid": OWM_KEY,
        "units": "metric",
    }, timeout=8)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=600)
def get_city_news(city: str, days: int = 3) -> list[dict]:
    """Fetch recent news articles via Tavily."""
    # City name is normalized in the calling function
    result = tavily.search(
        query=f"latest news {city}",
        topic="news",
        days=days,
        max_results=5,
        search_depth="advanced",
    )
    return result.get("results", [])

# ── UI ──────────────────────────────────────────────────────────

st.title("🌆 City Briefing Agent")
st.success("✅ NEW VERSION LOADED")

# Input city and normalize it
city_input = st.text_input("Enter a city name:", placeholder="e.g., London, Tokyo, New York")
city = city_input.strip()

# Selection menu handler
option = st.radio(
    "What would you like to fetch?",
    ("1: Weather", "2: News", "3: Both"),
    index=2
)

# Map selection to action
fetch_weather = option in ["1: Weather", "3: Both"]
fetch_news = option in ["2: News", "3: Both"]

if st.button("Get Briefing"):
    if not city:
        st.warning("Please enter a city name.")
    elif not (fetch_weather or fetch_news):
        st.warning("Please select an option.")
    else:
        # Use status container for live feedback
        with st.status(f"Fetching data for {city.title()}...", expanded=True) as status:
            start_time = time.time()

            weather_data = None
            news_data = None
            errors = []

            # Concurrency for speed
            with ThreadPoolExecutor() as executor:
                futures = {}
                if fetch_weather:
                    st.write("🌤  Fetching weather context...")
                    futures[executor.submit(get_weather, city)] = "weather"

                if fetch_news:
                    st.write("📰  Fetching recent news...")
                    futures[executor.submit(get_city_news, city)] = "news"

                for future in futures:
                    try:
                        result = future.result()
                        if futures[future] == "weather":
                            weather_data = result
                        else:
                            news_data = result
                    except Exception as e:
                        errors.append(f"{futures[future].capitalize()} error: {e}")

            if errors:
                for err in errors:
                    st.error(err)
                status.update(label="Briefing failed!", state="error")
                st.stop()

            status.update(label=f"Briefing ready! ({time.time() - start_time:.2f}s)", state="complete")

        # ── Display Results ─────────────────────────────────────

        # Display weather if fetched
        if fetch_weather and weather_data:
            st.subheader(f"⛅ Weather for {city.title()}")
            try:
                name    = f"{weather_data['name']}, {weather_data['sys']['country']}"
                temp    = weather_data["main"]["temp"]
                feels   = weather_data["main"]["feels_like"]
                cond    = weather_data["weather"][0]["description"].title()

                col_w1, col_w2, col_w3, col_w4 = st.columns(4)
                col_w1.metric("Temperature", f"{temp:.1f}°C")
                col_w2.metric("Feels like", f"{feels:.1f}°C")
                col_w3.write(f"**Condition:** {cond}")
                col_w4.write(f"**Humidity:** {weather_data['main']['humidity']}%")
            except KeyError:
                st.error("Unexpected weather response.")

        # Display news if fetched
        if fetch_news:
            st.subheader(f"📰 Recent News for {city.title()}")
            if not news_data:
                st.info("No recent news found.")
            else:
                for a in news_data:
                    with st.expander(a.get("title", "No Title")):
                        st.write(a.get("content", "No content available."))
                        if a.get("url"):
                            st.link_button("Read more", a["url"])