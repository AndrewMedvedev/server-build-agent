from typing import Literal

import asyncio
from collections.abc import Callable

from bs4 import BeautifulSoup
from playwright.async_api import Page

from depends import text_splitter
from utils import clean_html


def update_page_after_click(func: Callable):
    async def wrapper(page: Page | None, str_: str):
        if page is None:
            return {"click": "No active session. Please create a new session first."}

        new_page_future = asyncio.ensure_future(page.wait_for_event("page", timeout=3000))

        result = await func(page, str_)

        try:
            new_page = await new_page_future
            await new_page.wait_for_load_state()
            page = new_page
        except TimeoutError:
            # Если новая страница не открылась, остаемся на текущей
            pass
        except Exception:  # noqa: BLE001, S110
            pass

        return result

    return wrapper


async def navigate(url: str, page: Page | None, part: Literal["header", "body", "footer"]) -> dict:
    if page is None:
        return {"navigate": "No active session. Please create a new session first"}
    if not url.startswith("http://") and not url.startswith("https://"):  # type: ignore  # noqa: PGH003
        url = "https://" + url  # type: ignore  # noqa: PGH003
    await page.goto(url)
    text_content = await get_html_part(part=part, page=page)
    return {
        "navigate": f"Navigated to {url}\npage_text_content[:200]:\n\n{text_content[:200]}",
        "page": page,
    }


async def click(selector: str, page: Page | None) -> dict:
    if page is None:
        return {"click": "No active session. Please create a new session first."}
    try:
        await page.wait_for_selector(selector, state="visible", timeout=10000)
        await asyncio.sleep(1)
        element = page.locator(selector)
        await element.scroll_into_view_if_needed()
        await element.click(
            timeout=5000,
            force=True,
            no_wait_after=True,
        )
        result = text_splitter.split_text(selector)
        return {"click": f"Clicked {result}", "page": page}  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        return {"click": f"Failed to click {selector}: {e!s}", "page": page}


async def fill(selector: str, value: str, page: Page | None) -> dict:
    if page is None:
        return {"fill": "No active session. Please create a new session first."}
    await page.wait_for_load_state(timeout=10000, state="networkidle")
    await asyncio.sleep(1)
    await page.locator(selector).nth(0).fill(value)
    return {"fill": "success", "page": page}


async def evaluate(script: str, page: Page | None) -> dict:
    if page is None:
        return {"evaluate": "No active session. Please create a new session first."}
    await page.wait_for_load_state(timeout=10000, state="networkidle")
    await asyncio.sleep(1)
    result = await page.evaluate(script)
    return {"evaluate": f"Evaluated script, result: {result}", "page": page}


async def get_html_content(selector: str, page: Page | None) -> dict:

    if page is None:
        return {"get_html_content": "No active session. Please create a new session first."}
    await page.wait_for_load_state(timeout=10000, state="networkidle")
    await asyncio.sleep(1)
    locator = page.locator(selector)
    count = await locator.count()
    html_blocks = [await locator.nth(i).inner_html() for i in range(count)]
    clean = clean_html("\n".join(html_blocks))
    result = text_splitter.split_text(clean)
    return {
        "get_html_content": f"HTML content of element with selector {selector}: {result}",
        "page": page,
    }


async def get_html_part(part: Literal["header", "body", "footer"], page: Page | None) -> dict:
    if page is None:
        return {"get_html_part": "No active session. Please create a new session first."}
    await page.wait_for_load_state(timeout=10000, state="networkidle")
    await asyncio.sleep(1)
    html_content = await page.content()
    soup = BeautifulSoup(html_content, "html.parser")
    find_part = soup.find(part)
    if find_part:
        clean = clean_html(str(find_part))
        return {"get_html_part": f"HTML content of element with {part}: {clean}", "page": page}
    return {"get_html_part": f"Not find {part}", "page": page}
