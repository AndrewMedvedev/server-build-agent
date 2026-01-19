from typing import Literal

from asyncio import run

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from utils import clean_html


async def get_html_part(part: Literal["header", "body", "footer"], page: Page | None) -> dict:
    if page is None:
        print("w vk keve")
        return {"get_html_part": "No active session. Please create a new session first."}
    html_content = await page.content()
    print(page.content())
    soup = BeautifulSoup(html_content, "html.parser")
    print(soup)
    find_part = soup.find(part)
    print(find_part)
    if find_part:
        clean = clean_html(str(find_part))
        print({"get_html_part": f"HTML content of element with {part}: {clean}", "page": page})
        return {"get_html_part": f"HTML content of element with {part}: {clean}", "page": page}
    print({"get_html_part": f"Not find {part}", "page": page})
    return {"get_html_part": f"Not find {part}", "page": page}


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

    result = await get_html_part("body", page)
    print(result)


result = run(main())
