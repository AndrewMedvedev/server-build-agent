from typing import Literal

import logging
import time
from collections.abc import Callable
from functools import wraps

from langchain.tools import ToolRuntime, tool
from langgraph.types import Command

from mcp_ import click, evaluate, fill, get_html_content, get_html_part, navigate

logger = logging.getLogger(__name__)
RESULT_PREVIEW_CHARS = 1000


def log_tool_call(tool_name: str | None = None):
    """Декоратор для логирования вызовов инструментов (тулов).

    Записывает в лог:
    - Начало выполнения инструмента
    - Входные аргументы
    - Время выполнения
    - Успешный/неуспешный результат
    - Предпросмотр результата (ограниченный по длине)

    Args:
        tool_name: Имя инструмента для логирования. Если не указано, используется имя функции.

    Returns:
        Декоратор для обертки функций инструментов.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
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
                result = await func(*args, **kwargs)
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


@tool("navigate_handler", parse_docstring=True)
@log_tool_call("navigate_handler")
async def navigate_handler(
    runtime: ToolRuntime, part: Literal["header", "body", "footer"]
) -> dict:
    """Переходит по указанному URL в текущей активной сессии браузера.

    Если нет активной сессии, создает новую.

    Args:
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.
        part (Literal["header", "body", "footer"]): Часть страницы для извлечения.

    Returns:
        dict: Сообщение о навигации и первые 200 символов текстового содержимого
            страницы.
    """

    return await navigate(url=runtime.state["url"], part=part, page=runtime.state["page"])


@tool("click_handler", parse_docstring=True)
@log_tool_call("click_handler")
async def click_handler(runtime: ToolRuntime, name: str) -> dict:
    """Кликает на элемент страницы по CSS-селектору.

    Ожидает открытия новых страниц после клика и автоматически переключается на них.

    Args:
        name (str): CSS-селектор элемента для клика (переименованный параметр для совместимости).
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.

    Returns:
        dict: Подтверждение клика с указанием селектора.
    """

    return await click(page=runtime.state["page"], selector=name)


@tool("fill_handler", parse_docstring=True)
@log_tool_call("fill_handler")
async def fill_handler(runtime: ToolRuntime, selector: str, value: str) -> dict:
    """Заполняет поле ввода (input, textarea) указанным значением.

    Args:
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.
        selector (str): CSS-селектор поля ввода.
        value (str): Значение для ввода в поле.

    Returns:
        dict: Подтверждение заполнения с указанием селектора и значения.
    """

    return await fill(page=runtime.state["page"], selector=selector, value=value)


@tool("evaluate_handler", parse_docstring=True)
@log_tool_call("evaluate_handler")
async def evaluate_handler(runtime: ToolRuntime, script: str) -> dict:
    """Выполняет JavaScript код на текущей странице.

    Полезно для извлечения данных или выполнения сложных операций.

    Args:
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.
        script (str): JavaScript код для выполнения.

    Returns:
        dict: Результат выполнения скрипта.
    """

    return await evaluate(page=runtime.state["page"], script=script)


@tool("get_html_handler", parse_docstring=True)
@log_tool_call("get_html_handler")
async def get_html_handler(runtime: ToolRuntime, selector: str) -> dict:
    """Получает HTML содержимое конкретного элемента по CSS-селектору.

    Args:
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.
        selector (str): CSS-селектор элемента.

    Returns:
        dict: HTML содержимое выбранного элемента.
    """

    return await get_html_content(page=runtime.state["page"], selector=selector)


@tool("get_html_part_handler", parse_docstring=True)
@log_tool_call("get_html_part_handler")
async def get_html_part_handler(
    runtime: ToolRuntime,
    part: Literal["header", "body", "footer"],
) -> dict:
    """Извлекает HTML-содержимое определенной структурной части веб-страницы.

    Этот инструмент предназначен для получения одной из основных структурных частей
    HTML-документа: header (верхний колонтитул), body (основное содержимое) или
    footer (нижний колонтитул).

    Args:
        part (Literal["header", "body", "footer"]): Часть страницы для извлечения.
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.

    Returns:
        dict: HTML-содержимое запрошенной части страницы или сообщение об ошибке.
    """

    return await get_html_part(page=runtime.state["page"], part=part)


@tool("save_state", parse_docstring=True)  # type: ignore  # noqa: PGH003
@log_tool_call("save_state")
async def save_state(  # noqa: RUF029
    runtime: ToolRuntime,
    url: str,
    navigate: str,
    click: str,
    fill: str,
    evaluate: str,
    get_html_content: str,
    get_html_part: str,
) -> Command:
    """Сохраняет текущее состояние сессии для последующего использования.

    Этот инструмент фиксирует текущее состояние браузерной сессии, включая контекст
    страницы, историю навигации и другие параметры. Сохраненное состояние может быть
    использовано для восстановления сессии или передачи состояния между различными
    компонентами системы.

    Args:
        runtime (ToolRuntime): Объект ToolRuntime, содержащий состояние сессии.
        url (str): URL текущей страницы.
        navigate (str): Информация о последней навигации.
        fill (str): Информация о заполненных полях.
        evaluate (str): Результаты выполнения JavaScript.
        click (str): Информация о кликах по тексту.
        get_html_content (str): HTML содержимое элементов.
        get_html_part (str): Части HTML страницы.

    Returns:
        Command: с обновленным состоянием.
    """

    return Command(
        update={
            "page": runtime.state["page"],
            "url": url,
            "navigate": navigate,
            "click": click,
            "fill": fill,
            "evaluate": evaluate,
            "get_html_content": get_html_content,
            "get_html_part": get_html_part,
        }
    )


mcp_tools = [
    navigate_handler,
    click_handler,
    fill_handler,
    evaluate_handler,
    get_html_handler,
    get_html_part_handler,
    save_state,
]
