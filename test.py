from asyncio import run

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from playwright.async_api import async_playwright

from depends import yandex_gpt
from prompts import PROMPT_SEARCH
from schemas import State
from tools import mcp_tools

config: RunnableConfig = {"configurable": {"thread_id": "test_thread_1"}}

lalal: CompiledStateGraph = create_agent(
    model=yandex_gpt,
    tools=mcp_tools,
    # checkpointer=MemorySaver(),
    # middleware=[
    #     SummarizationMiddleware(
    #         model=yandex_gpt,
    #         trigger=("tokens", 4000),
    #         keep=("messages", 5),
    #     )
    # ],
    state_schema=State,
)


async def new_session(
    url: str,
) -> tuple:
    playw = await async_playwright().start()
    browser = await playw.chromium.launch(headless=False)
    page = await browser.new_page()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    await page.goto(url)
    return url, page


async def main():

    url, page = await new_session("arsplus.ru")

    result = await lalal.ainvoke(
        {
            "messages": [PROMPT_SEARCH],
            "page": page,
            "url": url,
            "navigate": None,
            "click": None,
            "fill": None,
            "evaluate": None,
            "get_html_content": None,
            "get_html_part": None,
        },
        config=config,
    )
    print(result)


run(main())
