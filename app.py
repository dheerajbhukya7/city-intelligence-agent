
import os
import requests
import streamlit as st

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
# 1. PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="City Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main background */
    .stApp {
        background-color: #0b1120;
        color: #e5e7eb;
    }

    /* Main content */
    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Header */
    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 16px;
        margin-top: 5px;
    }

    /* Status card */
    .status-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 15px;
    }

    .status-online {
        color: #22c55e;
        font-weight: 600;
    }

    /* Metric cards */
    .metric-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        height: 120px;
    }

    .metric-value {
        font-size: 28px;
        font-weight: 700;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 13px;
    }

    /* Tool cards */
    .tool-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
    }

    /* News cards */
    .news-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .news-title {
        font-size: 17px;
        font-weight: 600;
    }

    .news-source {
        color: #64748b;
        font-size: 12px;
    }

    /* Approval */
    .approval-card {
        background: #172554;
        border: 1px solid #2563eb;
        border-radius: 14px;
        padding: 18px;
        margin: 15px 0;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. LOAD ENVIRONMENT
# ============================================================

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================
# 4. API VALIDATION
# ============================================================

missing = []

if not OPENWEATHER_API_KEY:
    missing.append("OPENWEATHER_API_KEY")

if not TAVILY_API_KEY:
    missing.append("TAVILY_API_KEY")

if not GROQ_API_KEY:
    missing.append("GROQ_API_KEY")


if missing:
    st.error(
        "Missing environment variables: "
        + ", ".join(missing)
    )
    st.stop()


# ============================================================
# 5. API CLIENTS
# ============================================================

tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)


# ============================================================
# 6. WEATHER FUNCTION
# ============================================================

def get_weather(city: str) -> str:

    url = (
        "https://api.openweathermap.org/"
        "data/2.5/weather"
    )

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
            f"for {city}."
        )

    except Exception as e:

        return f"Weather API error: {e}"


# ============================================================
# 7. NEWS FUNCTION
# ============================================================

def get_city_news(city: str) -> str:

    try:

        result = tavily.search(
            query=f"latest news in {city}",
            topic="news",
            max_results=5,
        )

        articles = result.get(
            "results",
            []
        )

        if not articles:

            return f"No recent news found for {city}."

        news = []

        for article in articles:

            news.append(
                {
                    "title": article.get(
                        "title",
                        "No title"
                    ),
                    "content": article.get(
                        "content",
                        "No summary available"
                    ),
                    "url": article.get(
                        "url",
                        ""
                    ),
                }
            )

        return str(news)

    except Exception as e:

        return f"News API error: {e}"


# ============================================================
# 8. CREATE TOOLS
# ============================================================

weather_tool = StructuredTool.from_function(
    func=get_weather,
    name="get_weather",
    description=(
        "Get current weather information "
        "for a city."
    ),
)

news_tool = StructuredTool.from_function(
    func=get_city_news,
    name="get_city_news",
    description=(
        "Get recent news about a city."
    ),
)


tools = [
    weather_tool,
    news_tool,
]


tool_map = {
    tool.name: tool
    for tool in tools
}


# ============================================================
# 9. GROQ
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
)

llm_with_tools = llm.bind_tools(
    tools
)


# ============================================================
# 10. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a City Intelligence Assistant.

You provide current city information using:

1. get_weather
   Current weather information.

2. get_city_news
   Recent city news.

Rules:

- Use weather tool for weather questions.
- Use news tool for current news.
- Use both when the user asks for both.
- Remember the most recently mentioned city.
- If the user says "both", use both tools for
  the most recently mentioned city.
- Never invent current information.
- Clearly distinguish facts from inference.
- Do not claim causation unless evidence supports it.
- If the question is unrelated to city intelligence,
  answer normally.
"""


# ============================================================
# 11. SESSION STATE
# ============================================================

if "messages" not in st.session_state:

    st.session_state.messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
        )
    ]


if "pending_tools" not in st.session_state:

    st.session_state.pending_tools = []


if "weather" not in st.session_state:

    st.session_state.weather = None


if "news" not in st.session_state:

    st.session_state.news = None


# ============================================================
# 12. SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="status-card">

        <h2>🌍 City Intelligence</h2>

        <p class="subtitle">
        AI-powered city analysis
        </p>

        <p class="status-online">
        ● System Online
        </p>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("AI Stack")

    st.markdown(
        """
        **LLM**  
        Groq — GPT-OSS 120B

        **Weather**  
        OpenWeather API

        **News**  
        Tavily Search

        **Agent**  
        LangChain Tool Calling
        """
    )

    st.divider()

    st.subheader("Connected Tools")

    st.success("✓ Weather API")

    st.success("✓ Tavily News")

    st.success("✓ Groq LLM")

    st.divider()

    if st.button(
        "🗑 Clear Conversation",
        use_container_width=True,
    ):

        st.session_state.messages = [
            SystemMessage(
                content=SYSTEM_PROMPT
            )
        ]

        st.session_state.pending_tools = []

        st.session_state.weather = None

        st.session_state.news = None

        st.rerun()


# ============================================================
# 13. HEADER
# ============================================================

st.markdown(
    """
    <div class="main-title">
        🌍 City Intelligence Agent
    </div>

    <div class="subtitle">
        Real-time weather, news and AI-powered
        city intelligence
    </div>
    """,
    unsafe_allow_html=True,
)


st.write("")


# ============================================================
# 14. DASHBOARD METRICS
# ============================================================

col1, col2, col3, col4 = st.columns(4)


with col1:

    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">🤖</div>
            <div class="metric-label">AI Agent</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with col2:

    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">☁️</div>
            <div class="metric-label">Weather</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with col3:

    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">📰</div>
            <div class="metric-label">Live News</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with col4:

    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">⚡</div>
            <div class="metric-label">Real-time</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.write("")


# ============================================================
# 15. WEATHER / NEWS DASHBOARD
# ============================================================

if st.session_state.weather:

    try:

        weather_text = st.session_state.weather

        lines = weather_text.split("\n")

        weather_values = {}

        for line in lines:

            if ":" in line:

                key, value = line.split(
                    ":",
                    1
                )

                weather_values[
                    key.strip()
                ] = value.strip()

        st.subheader(
            f"☁️ Weather — "
            f"{weather_values.get('City', '')}"
        )

        w1, w2, w3, w4 = st.columns(4)

        with w1:

            st.metric(
                "Temperature",
                weather_values.get(
                    "Temperature",
                    "--"
                )
            )

        with w2:

            st.metric(
                "Feels Like",
                weather_values.get(
                    "Feels like",
                    "--"
                )
            )

        with w3:

            st.metric(
                "Humidity",
                weather_values.get(
                    "Humidity",
                    "--"
                )
            )

        with w4:

            st.metric(
                "Wind",
                weather_values.get(
                    "Wind speed",
                    "--"
                )
            )

    except Exception:

        pass


# ============================================================
# 16. CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    if isinstance(
        message,
        HumanMessage
    ):

        with st.chat_message("user"):

            st.write(
                message.content
            )

    elif (
        hasattr(message, "content")
        and message.content
        and not isinstance(
            message,
            ToolMessage
        )
    ):

        with st.chat_message(
            "assistant"
        ):

            st.write(
                message.content
            )


# ============================================================
# 17. TOOL APPROVAL
# ============================================================

if st.session_state.pending_tools:

    st.warning(
        "The agent wants to use a tool. "
        "Your approval is required."
    )

    for index, tool_call in enumerate(
        st.session_state.pending_tools
    ):

        tool_name = tool_call["name"]

        tool_args = tool_call["args"]

        st.markdown(
            f"""
            <div class="approval-card">

            <strong>Tool Request</strong>

            <br><br>

            Tool: <strong>{tool_name}</strong>

            <br>

            Arguments:
            <code>{tool_args}</code>

            </div>
            """,
            unsafe_allow_html=True,
        )

        approve_col, deny_col = st.columns(2)

        with approve_col:

            if st.button(
                "✓ Approve",
                key=f"approve_{index}",
                use_container_width=True,
            ):

                with st.spinner(
                    f"Running {tool_name}..."
                ):

                    try:

                        result = tool_map[
                            tool_name
                        ].invoke(
                            tool_args
                        )

                        st.session_state.messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"],
                            )
                        )

                        if tool_name == "get_weather":

                            st.session_state.weather = (
                                result
                            )

                        elif tool_name == "get_city_news":

                            st.session_state.news = (
                                result
                            )

                    except Exception as e:

                        st.session_state.messages.append(
                            ToolMessage(
                                content=(
                                    f"Tool failed: {e}"
                                ),
                                tool_call_id=tool_call["id"],
                            )
                        )

                st.session_state.pending_tools.pop(
                    index
                )

                st.rerun()

        with deny_col:

            if st.button(
                "✕ Deny",
                key=f"deny_{index}",
                use_container_width=True,
            ):

                st.session_state.messages.append(
                    ToolMessage(
                        content=(
                            "User denied tool execution."
                        ),
                        tool_call_id=tool_call["id"],
                    )
                )

                st.session_state.pending_tools.pop(
                    index
                )

                st.rerun()


# ============================================================
# 18. CHAT INPUT
# ============================================================

user_input = st.chat_input(
    "Ask about a city..."
)


if user_input:

    # --------------------------------------------------------
    # Add user message
    # --------------------------------------------------------

    st.session_state.messages.append(
        HumanMessage(
            content=user_input
        )
    )

    # --------------------------------------------------------
    # Ask LLM
    # --------------------------------------------------------

    with st.spinner(
        "Agent is thinking..."
    ):

        response = llm_with_tools.invoke(
            st.session_state.messages
        )

    # --------------------------------------------------------
    # Save response
    # --------------------------------------------------------

    st.session_state.messages.append(
        response
    )

    # --------------------------------------------------------
    # Check tools
    # --------------------------------------------------------

    if response.tool_calls:

        st.session_state.pending_tools = (
            response.tool_calls
        )

    else:

        st.rerun()
