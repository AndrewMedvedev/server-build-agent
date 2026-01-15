from typing import Literal

import logging
import time
from collections.abc import Callable
from functools import wraps

from langchain.tools import tool

from mcp_ import click, evaluate, fill, get_html_content, get_html_part, navigate, new_session
from schemas import State

logger = logging.getLogger(__name__)
RESULT_PREVIEW_CHARS = 1000


def log_tool_call(tool_name: str | None = None):
    """
    Декоратор для логирования вызовов инструментов (тулов).

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

            # Логирование начала вызова инструмента
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
                # Выполнение основной функции инструмента
                result = await func(*args, **kwargs)
                execution_time = round(time.time() - start_time, 2)

                # Формирование предпросмотра результата (ограниченной длины)
                result_preview = (
                    str(result)[:RESULT_PREVIEW_CHARS] + "..."
                    if len(str(result)) > RESULT_PREVIEW_CHARS
                    else str(result)
                )

                # Логирование успешного выполнения
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
                # Логирование ошибки при выполнении
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


@tool("new_session_handler")  # Декоратор LangChain для регистрации инструмента
@log_tool_call("new_session_handler")  # Применение декоратора логирования
async def new_session_handler(state: State, url: str) -> str:
    """
    Создает новую сессию браузера для автоматизации веб-страниц.
    Запускает браузер Chrome и открывает новую страницу.

    Параметры:
        - state (State): Состояние сессии, содержит контекст браузера и страницы
        - url (str): URL для первоначальной навигации.
          Если не указан, откроется пустая страница.
          Если URL не начинается с http:// или https://, автоматически добавляется https://

    Возвращает:
        dict: Успешное сообщение о создании сессии.
    Пример: {"url": "google.com"}
    """
    print(state)
    return await new_session(state, url)


@tool("navigate_handler")
@log_tool_call("navigate_handler")
async def navigate_handler(state: State) -> str:
    """
    Переходит по указанному URL в текущей активной сессии браузера.
    Если нет активной сессии, создает новую.

    Параметры:
        - state (State): Состояние сессии
        - url (str): URL для навигации.
          Если URL не начинается с http:// или https://, автоматически добавляется https://

    Возвращает:
        dict: Сообщение о навигации и первые 200 символов текстового содержимого страницы.
    Пример: {"url": "https://example.com"}
    """
    print(state)
    return await navigate(state)


@tool("click_handler")
@log_tool_call("click_handler")
async def click_handler(name: str, state: State) -> str:
    """
    Кликает на элемент страницы по CSS-селектору.
    Ожидает открытия новых страниц после клика и автоматически переключается на них.

    Параметры:
        - name (str): CSS-селектор элемента для клика (переименованный параметр для совместимости)
        - state (State): Состояние сессии

    Возвращает:
        dict: Подтверждение клика с указанием селектора.
    Пример: {"selector": "button.submit"}
    """
    print(state)
    return await click(state=state, str_=name)


# Закомментированный инструмент для клика по тексту
# @tool("click_text_handler")
# @log_tool_call("click_text_handler")
# async def click_text_handler(name: str, arguments: dict | None) -> list[TextContent]:
#     """
#     Кликает на элемент по текстовому содержимому.
#     Ищет элемент, содержащий указанный текст, и кликает на первый найденный.
#     Ожидает открытия новых страниц после клика.
#
#     Параметры:
#         - text (str, обязательно): Текст элемента для клика.
#
#     Возвращает: Подтверждение клика с указанием текста.
#     Пример: {"text": "Войти"}
#     """
#     return await ClickTextToolHandler().handle(name, arguments)


@tool("fill_handler")
@log_tool_call("fill_handler")
async def fill_handler(state: State, selector: str, value: str) -> str:
    """
    Заполняет поле ввода (input, textarea) указанным значением.

    Параметры:
        - state (State): Состояние сессии
        - selector (str): CSS-селектор поля ввода
        - value (str): Значение для ввода в поле

    Возвращает:
        dict: Подтверждение заполнения с указанием селектора и значения.
    Пример: {"selector": "#search-input", "value": "Python программирование"}
    """
    print(state)
    return await fill(state, selector, value)


@tool("evaluate_handler")
@log_tool_call("evaluate_handler")
async def evaluate_handler(state: State, script: str) -> str:
    """
    Выполняет JavaScript код на текущей странице.
    Полезно для извлечения данных или выполнения сложных операций.

    Параметры:
        - state (State): Состояние сессии
        - script (str): JavaScript код для выполнения.

    Возвращает:
        dict: Результат выполнения скрипта.
    Пример: {"script": "document.title"}
    """
    print(state)
    return await evaluate(state, script)


# Закомментированный инструмент для получения текстового содержимого
# @tool("get_text_handler")
# @log_tool_call("get_text_handler")
# async def get_text_handler(
#     name: str, arguments: dict | None
# ) -> str:
#     """
#     Получает текстовое содержимое всех видимых элементов страницы.
#     Фильтрует дубликаты и элементы с большим количеством дочерних элементов.
#
#     Параметры:
#         - (нет обязательных параметров)
#
#     Возвращает: Список уникальных текстовых элементов страницы.
#     Пример: {} или {"dummy": "value"} если аргументы требуются формально
#     """
#     return await GetTextContentToolHandler().handle(name, arguments)


@tool("get_html_handler")
@log_tool_call("get_html_handler")
async def get_html_handler(state: State, selector: str) -> str:
    """
    Получает HTML содержимое конкретного элемента по CSS-селектору.

    Параметры:
        - state (State): Состояние сессии
        - selector (str): CSS-селектор элемента.

    Возвращает:
        dict: HTML содержимое выбранного элемента.
    Пример: {"selector": "div.content"}
    """
    print(state)
    return await get_html_content(state, selector)


@tool("get_html_part_handler")
@log_tool_call("get_html_part_handler")
async def get_html_part_handler(part: Literal["header", "body", "footer"], state: State) -> str:
    """
    Извлекает HTML-содержимое определенной структурной части веб-страницы.

    Этот инструмент предназначен для получения одной из основных структурных частей HTML-документа:
    header (верхний колонтитул), body (основное содержимое) или footer (нижний колонтитул).

    Параметры:
        - part (Literal["header", "body", "footer"]): Часть страницы для извлечения
        - state (State): Состояние сессии

    Возвращает:
        dict: HTML-содержимое запрошенной части страницы или сообщение об ошибке.
    """
    print(state)
    return await get_html_part(state, part)


mcp_tools = [
    new_session_handler,
    navigate_handler,
    click_handler,
    fill_handler,
    evaluate_handler,
    get_html_handler,
    get_html_part_handler,
]
