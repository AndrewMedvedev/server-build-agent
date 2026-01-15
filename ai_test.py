from typing import Any

import asyncio
import logging
import time
from collections.abc import Callable
from functools import wraps

from langchain.agents import create_agent
from langchain.tools import tool

from crawler import crawl_web_page
from depends import yandex_gpt
from prompts import PROMPT_SEARCH
from test_ import search_async

logger = logging.getLogger(__name__)
RESULT_PREVIEW_CHARS = 1000


def log_tool_call(tool_name: str | None = None):
    """Декоратор для логирования вызовов инструментов"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_id = tool_name or func.__name__
            start_time = time.time()
            logger.info(
                "🛠️ TOOL CALL START: %s",
                tool_id,
                extra={
                    "tool": tool_id,
                    "input_args": args,
                    "input_kwargs": kwargs,
                    "timestamp": start_time,
                },
            )
            try:
                result = func(*args, **kwargs)
                execution_time = round(time.time() - start_time, 2)
                result_preview = (
                    str(result)[:RESULT_PREVIEW_CHARS] + "..."
                    if len(str(result)) > RESULT_PREVIEW_CHARS
                    else str(result)
                )
                logger.info(
                    "✅ TOOL CALL SUCCESS: %s (%s s)",
                    tool_id,
                    execution_time,
                    extra={
                        "tool": tool_id,
                        "execution_time": execution_time,
                        "result_preview": result_preview,
                        "result_type": type(result).__name__,
                        "result_length": len(str(result)) if hasattr(result, "__len__") else None,
                    },
                )
            except Exception as e:
                execution_time = round(time.time() - start_time, 2)
                logger.exception(
                    "❌ TOOL CALL FAILED: %s (%s s)",
                    tool_id,
                    execution_time,
                    extra={
                        "tool": tool_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "execution_time": execution_time,
                    },
                )
                raise
            else:
                return result

        return wrapper

    return decorator


@tool(
    "web_search",
    description="""Выполняет поиск в Яндекс. Поисковик.
    Возвращает список найденных страниц с заголовками, URL и кратким описанием.
    Подходит для получения актуальной информации из интернета.""",
)
def web_search(search_query: str) -> list[dict[str, Any]]:
    """Выполняет поиск информации в интернете"""

    return asyncio.run(search_async(search_query))


@tool(
    "browse_web_page",
    description="Открывает WEB-страницу и получает её контент в формате Markdown",
)
@log_tool_call("browse_web_page")
def browse_link(link: str) -> str:
    """Просматривает WEB-страницу по ссылке"""

    try:
        return asyncio.run(crawl_web_page(link))
    except Exception:  # noqa: BLE001
        return "Не удалось открыть страницу"


lalal = create_agent(model=yandex_gpt, tools=[browse_link, web_search])

print(lalal.invoke(PROMPT_SEARCH))
