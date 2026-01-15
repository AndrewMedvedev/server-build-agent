from typing import Literal

import asyncio
import json
from collections.abc import Callable

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from depends import text_splitter
from schemas import State
from utils import clean_html


def update_page_after_click(func: Callable):
    async def wrapper(state: State, str_: str):
        if state.get("browser") is None or state.get("page") is None:
            state["click"] = "No active session. Please create a new session first."
            return "No active session. Please create a new session first."

        page = state["page"]

        # Ждем новую страницу после клика
        new_page_future = asyncio.ensure_future(page.context.wait_for_event("page", timeout=3000))  # type: ignore  # noqa: PGH003

        result = await func(state, str_)

        try:
            new_page = await new_page_future
            await new_page.wait_for_load_state()
            state["page"] = new_page
            state["url"] = new_page.url
        except TimeoutError:
            # Если новая страница не открылась, остаемся на текущей
            pass
        except Exception:  # noqa: BLE001, S110
            pass

        return result

    return wrapper


async def new_session(
    state: State,
    url: str,
) -> str:
    playw = await async_playwright().start()
    browser = await playw.chromium.launch(headless=False)
    page = await browser.new_page()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    await page.goto(url)
    state["browser"] = browser
    state["page"] = page
    return "success"


async def navigate(
    state: State,
) -> str:
    if state["browser"] is None or state["page"] is None:
        state["navigate"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first"
    page = state["page"]
    url = state["url"]
    if not url.startswith("http://") and not url.startswith("https://"):  # type: ignore  # noqa: PGH003
        url = "https://" + url  # type: ignore  # noqa: PGH003
    await page.goto(url)
    text_content = await get_text_content(state)
    result = text_splitter.split_text(json.dumps(text_content))
    state["navigate"] = f"Navigated to {url}\npage_text_content[:200]:\n\n{result[:200]}"
    return f"Navigated to {url}\npage_text_content[:200]:\n\n{result[:200]}"


@update_page_after_click
async def click(state: State, selector: str) -> str:
    if state["browser"] is None or state["page"] is None:
        state["click"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."

    page = state["page"]

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
        state["click"] = f"Clicked {result}"
        return f"Clicked {result}"  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        return f"Failed to click {selector}: {e!s}"


async def fill(state: State, selector: str, value: str) -> str:
    if state["browser"] is None or state["page"] is None:
        state["fill"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
    await page.locator(selector).fill(value)
    return ""


async def evaluate(
    state: State,
    script: str,
) -> str:
    if state["browser"] is None or state["page"] is None:
        state["evaluate"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
    result = await page.evaluate(script)
    state["evaluate"] = f"Evaluated script, result: {result}"
    return f"Evaluated script, result: {result}"


@update_page_after_click
async def click_text(state: State, text: str) -> str:
    if state["browser"] is None or state["page"] is None:
        state["click_text"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
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
        state["click_text"] = f"Failed to click element with text '{text}': {e}"
        return f"Failed to click element with text '{text}': {e}"
    return f"Clicked element with text '{text}'"


async def get_text_content(
    state: State,
) -> str:
    if state["browser"] is None or state["page"] is None:
        state["get_text_content"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
    text_contents = await page.evaluate("""() => {
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
    state["get_text_content"] = f"Text content of all elements: {text_contents}"
    return f"Text content of all elements: {text_contents}"


async def get_html_content(state: State, selector: str) -> str:
    if state["browser"] is None or state["page"] is None:
        state["get_html_content"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
    locator = page.locator(selector)
    count = await locator.count()
    html_blocks = [await locator.nth(i).inner_html() for i in range(count)]
    clean = clean_html("\n".join(html_blocks))
    result = text_splitter.split_text(clean)
    state["get_html_content"] = f"HTML content of element with selector {selector}: {result}"
    return f"HTML content of element with selector {selector}: {result}"


async def get_html_part(
    state: State,
    part: Literal["header", "body", "footer"],
) -> str:
    if state["browser"] is None or state["page"] is None:
        state["get_html_part"] = "No active session. Please create a new session first."
        return "No active session. Please create a new session first."
    page = state["page"]
    html_content = await page.content()
    soup = BeautifulSoup(html_content, "html.parser")

    find_part = soup.find(part)
    if find_part:
        clean = clean_html(str(find_part))
        state["get_html_part"] = f"HTML content of element with {part}: {clean}"
        return f"HTML content of element with {part}: {clean}"
    state["get_html_part"] = f"Not find {part}"
    return f"Not find {part}"
