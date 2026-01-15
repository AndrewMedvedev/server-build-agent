from asyncio import run

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from depends import yandex_gpt
from prompts import PROMPT_SEARCH
from schemas import State
from tools import mcp_tools

config: RunnableConfig = {"configurable": {"thread_id": "test_thread_1"}}

lalal: CompiledStateGraph = create_agent(
    model=yandex_gpt,
    tools=mcp_tools,
    checkpointer=InMemorySaver(),
    middleware=[
        SummarizationMiddleware(
            model=yandex_gpt,
            trigger=("tokens", 4000),
            keep=("messages", 5),
        )
    ],
    state_schema=State,
)
result = run(
    lalal.ainvoke(
        {
            "messages": [PROMPT_SEARCH],
            "url": None,
            "browser": None,
            "page": None,
            "navigate": None,
            "click": None,
            "fill": None,
            "evaluate": None,
            "click_text": None,
            "get_text_content": None,
            "get_html_content": None,
            "get_html_part": None,
        },
        config=config,
    )
)
print(result)
