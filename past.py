from typing import ClassVar, Literal

import asyncio
import uuid
from collections.abc import Callable

from bs4 import BeautifulSoup
from mcp.types import TextContent
from playwright.async_api import Page, async_playwright

from depends import text_splitter
from utils import clean_html


def update_page_after_click(func: Callable):
    async def wrapper(self, name: str, arguments: dict | None):
        if not self._sessions:
            return [
                TextContent(
                    type="text", text="No active session. Please create a new session first."
                )
            ]
        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]

        new_page_future = asyncio.ensure_future(page.context.wait_for_event("page", timeout=3000))

        result = await func(self, name, arguments)
        try:
            new_page = await new_page_future
            await new_page.wait_for_load_state()
            self._sessions[session_id]["page"] = new_page
        except:  # noqa: E722
            ...
        return result

    return wrapper


class ToolHandler:
    _sessions: ClassVar[dict] = {}


class NewSessionToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,
    ) -> str:
        _playwright = await async_playwright().start()
        browser = await _playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {"browser": browser, "page": page}
        if arguments:
            url = arguments.get("url")
            if url:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                await page.goto(url)
        return "success"


class NavigateToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            await NewSessionToolHandler().handle({})
        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]
        if arguments:
            url = arguments.get("url")
            if not url.startswith("http://") and not url.startswith("https://"):  # type: ignore  # noqa: PGH003
                url = "https://" + url  # type: ignore  # noqa: PGH003
            await page.goto(url)
        text_content = await GetTextContentToolHandler().handle({})
        result = text_splitter.split_text(text_content)
        return f"Navigated to {url}\npage_text_content[:200]:\n\n{result[:200]}"


class ClickToolHandler(ToolHandler):
    @update_page_after_click
    async def handle(self, arguments: dict | None) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session"

        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]

        if not arguments:
            return "No arguments provided"

        selector = arguments.get("selector")
        if not selector:
            return "No selector provided"

        try:
            await page.wait_for_selector(selector, state="visible", timeout=10000)
            element = page.locator(selector)
            await element.scroll_into_view_if_needed()
            await element.click(
                timeout=5000,
                force=True,
                no_wait_after=True,
            )
            result = text_splitter.split_text(selector)
            return f"Clicked {result}"  # noqa: TRY300
        except Exception as e:  # noqa: BLE001
            return f"Failed to click {selector}: {e!s}"


class FillToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."

        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]
        if arguments:
            selector = arguments.get("selector")
            value = arguments.get("value")
            await page.locator(selector).fill(value)
        return f"Filled element with selector {selector} with value {value}"


class EvaluateToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."
        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]
        if arguments:
            script = arguments.get("script")
            result = await page.evaluate(script)
        return f"Evaluated script, result: {result}"


class ClickTextToolHandler(ToolHandler):
    @update_page_after_click
    async def handle(self, arguments: dict | None) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."

        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]

        if arguments:
            text = arguments.get("text")
            locator = page.locator(f"text={text}").first

            try:
                await locator.wait_for(state="visible", timeout=10000)

                await locator.scroll_into_view_if_needed()

                retries = 3
                for attempt in range(retries):
                    try:
                        await locator.click(timeout=5000)
                        break
                    except Exception as e:
                        if attempt < retries - 1:
                            await asyncio.sleep(0.5)
                        else:
                            raise e

            except Exception as e:  # noqa: BLE001
                return f"Failed to click element with text '{text}': {e}"

        return f"Clicked element with text '{text}'"


class GetTextContentToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,  # noqa: ARG002
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."

        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]

        async def get_unique_texts_js(page):
            return await page.evaluate("""() => {
            var elements = Array.from(document.querySelectorAll('*'));
            var uniqueTexts = new Set();

            for (var element of elements) {
                if (element.offsetWidth > 0 || element.offsetHeight > 0) {
                    var childrenCount = element.querySelectorAll('*').length;
                    if (childrenCount <= 3) {
                        var innerText = element.innerText ? element.innerText.trim() : '';
                        if (innerText && innerText.length <= 1000) {
                            uniqueTexts.add(innerText);
                        }
                        var value = element.getAttribute('value');
                        if (value) {
                            uniqueTexts.add(value);
                        }
                    }
                }
            }
            //console.log( Array.from(uniqueTexts));
            return Array.from(uniqueTexts);
        }
        """)

        text_contents = await get_unique_texts_js(page)
        return f"Text content of all elements: {text_contents}"


class GetHtmlContentToolHandler(ToolHandler):
    async def handle(
        self,
        arguments: dict | None,
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."

        session_id = list(self._sessions.keys())[-1]
        page = self._sessions[session_id]["page"]
        if arguments:
            selector = arguments.get("selector")
            locator = page.locator(selector)
            count = await locator.count()
            html_blocks = [await locator.nth(i).inner_html() for i in range(count)]
            clean = clean_html("\n".join(html_blocks))
            result = text_splitter.split_text(clean)

        return f"HTML content of element with selector {selector}: {result}"


class GetHtmlPartToolHandler(ToolHandler):
    async def handle(
        self,
        part: Literal["header", "body", "footer"],
    ) -> str:
        print(self._sessions)
        if not self._sessions:
            return "No active session. Please create a new session first."
        session_id = list(self._sessions.keys())[-1]
        page: Page = self._sessions[session_id]["page"]
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "html.parser")

        find_part = soup.find(part)
        if find_part:
            clean = clean_html(str(find_part))
            return f"HTML content of element with {part}: {clean}"
        return f"Not find {part}"


from typing import Literal

import logging
import time
from collections.abc import Callable
from functools import wraps

from langchain.tools import tool

logger = logging.getLogger(__name__)
RESULT_PREVIEW_CHARS = 1000


def log_tool_call(tool_name: str | None = None):
    """Декоратор для логирования вызовов инструментов"""

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


@tool("new_session_handler")
@log_tool_call("new_session_handler")
async def new_session_handler(arguments: dict | None) -> str:
    """
    Создает новую сессию браузера для автоматизации веб-страниц.
    Запускает браузер Chrome и открывает новую страницу.

    Параметры:
        - url (dict): URL для первоначальной навигации.
          Если не указан, откроется пустая страница.
          Если URL не начинается с http:// или https://, автоматически добавляется https://

    Возвращает: Успешное сообщение о создании сессии.
    Пример: {"url": "google.com"}
    """
    return await NewSessionToolHandler().handle(arguments)


@tool("navigate_handler")
@log_tool_call("navigate_handler")
async def navigate_handler(arguments: dict | None) -> str:
    """
    Переходит по указанному URL в текущей активной сессии браузера.
    Если нет активной сессии, создает новую.

    Параметры:
        - url (dict): URL для навигации.
          Если URL не начинается с http:// или https://, автоматически добавляется https://

    Возвращает: Сообщение о навигации и первые 200 символов текстового содержимого страницы.
    Пример: {"url": "https://example.com"}
    """
    return await NavigateToolHandler().handle(arguments)


@tool("click_handler")
@log_tool_call("click_handler")
async def click_handler(arguments: dict | None) -> str:
    """
    Кликает на элемент страницы по CSS-селектору.
    Ожидает открытия новых страниц после клика и автоматически переключается на них.

    Параметры:
        - selector (dict): CSS-селектор элемента для клика.
          Примеры: "#submit-button", ".menu-item", "input[type='submit']"

    Возвращает: Подтверждение клика с указанием селектора.
    Пример: {"selector": "button.submit"}
    """
    return await ClickToolHandler().handle(arguments)  # type: ignore  # noqa: E261, PGH003, RUF100


# @tool("click_text_handler")
# @log_tool_call("click_text_handler")
# async def click_text_handler(name: str, arguments: dict | None) -> list[TextContent]:
#     """
#     Кликает на элемент по текстовому содержимому.
#     Ищет элемент, содержащий указанный текст, и кликает на первый найденный.
#     Ожидает открытия новых страниц после клика.

#     Параметры:
#         - text (str, обязательно): Текст элемента для клика.

#     Возвращает: Подтверждение клика с указанием текста.
#     Пример: {"text": "Войти"}
#     """
#     return await ClickTextToolHandler().handle(name, arguments)


@tool("fill_handler")
@log_tool_call("fill_handler")
async def fill_handler(arguments: dict | None) -> str:
    """
    Заполняет поле ввода (input, textarea) указанным значением.

    Параметры:
        - arguments (dict)
            - selector (str, обязательно): CSS-селектор поля ввода.
            - value (str, обязательно): Значение для ввода в поле.

    Возвращает: Подтверждение заполнения с указанием селектора и значения.
    Пример: {"selector": "#search-input", "value": "Python программирование"}
    """
    return await FillToolHandler().handle(arguments)


@tool("evaluate_handler")
@log_tool_call("evaluate_handler")
async def evaluate_handler(arguments: dict | None) -> str:
    """
    Выполняет JavaScript код на текущей странице.
    Полезно для извлечения данных или выполнения сложных операций.

    Параметры:
        - script (dict): JavaScript код для выполнения.

    Возвращает: Результат выполнения скрипта.
    Пример: {"script": "document.title"}
    """
    return await EvaluateToolHandler().handle(arguments)


# @tool("get_text_handler")
# @log_tool_call("get_text_handler")
# async def get_text_handler(
#     name: str, arguments: dict | None
# ) -> str:
#     """
#     Получает текстовое содержимое всех видимых элементов страницы.
#     Фильтрует дубликаты и элементы с большим количеством дочерних элементов.

#     Параметры:
#         - (нет обязательных параметров)

#     Возвращает: Список уникальных текстовых элементов страницы.
#     Пример: {} или {"dummy": "value"} если аргументы требуются формально
#     """
#     return await GetTextContentToolHandler().handle(name, arguments)


@tool("get_html_handler")
@log_tool_call("get_html_handler")
async def get_html_handler(arguments: dict | None) -> str:
    """
    Получает HTML содержимое конкретного элемента по CSS-селектору.

    Параметры:
        - selector (dict): CSS-селектор элемента.

    Возвращает: HTML содержимое выбранного элемента.
    Пример: {"selector": "div.content"}
    """
    return await GetHtmlContentToolHandler().handle(arguments)


@tool("get_html_part_handler")
@log_tool_call("get_html_part_handler")
async def get_html_part_handler(part: Literal["header", "body", "footer"]) -> str:
    """
    Извлекает HTML-содержимое определенной структурной части веб-страницы.

    Этот инструмент предназначен для получения одной из основных структурных частей HTML-документа:
    header (верхний колонтитул), body (основное содержимое) или footer (нижний колонтитул).

    Параметры:
        part (str): Часть страницы для извлечения. Допустимые значения: "header", "body", "footer".

    Возвращает:
        str: HTML-содержимое запрошенной части страницы или сообщение об ошибке.
    """
    return await GetHtmlPartToolHandler().handle(part)


mcp_tools = [
    new_session_handler,
    navigate_handler,
    click_handler,
    fill_handler,
    evaluate_handler,
    get_html_handler,
    get_html_part_handler,
]
