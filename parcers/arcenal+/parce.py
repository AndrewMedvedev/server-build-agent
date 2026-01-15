import asyncio
import json
import pathlib

from constants import MIN_SUM, PC_CATEGORY_LINKS
from playwright.async_api import Page, async_playwright


async def parce_links(link: str, page: Page) -> list[str]:
    await page.goto(f"https://arsplus.ru{link}")
    pagination = (await page.locator("div.bx-pagination-container li").count()) - 1
    product_links = []
    for i in range(1, pagination):
        await page.goto(f"https://arsplus.ru{link}?PAGEN_2={i}")
        div = page.locator('//a[@class="product-item-image-wrapper"]')
        count = div.count()
        for index in range(await count):
            result = await div.nth(index).get_attribute("href")
            product_links.append(result)
    return product_links


async def take_data_from_links(
    links: list[str], page: Page, index: int, min_sum: int
) -> list[str]:
    data: list[str] = []
    for link in links:
        try:
            await page.goto(f"https://arsplus.ru{link}")
            price = await page.locator('//div[@class="dk-cat-el__price-val"]').inner_text()
            price_int = int(price.replace("\xa0", "").replace("₽", "").replace(" ", ""))
            if price_int > min_sum:
                div = page.locator('//div[@class="dk-cat-el__box"]')
                chatacters = await div.inner_text()
                data.append(chatacters)
        except:
            ...
    pathlib.Path(f"{index}.md").write_text(  # noqa: ASYNC240
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data


async def parce(category_links: list[str]):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15",  # noqa: E501
            java_script_enabled=True,
            ignore_https_errors=True,
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () =&gt; undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () =&gt; [1, 2, 3, 4, 5]
            });
        """)
        page = await context.new_page()
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(50000)
        for index, link in enumerate(category_links):
            links = await parce_links(link, page)
            data_from_links = await take_data_from_links(links, page, index, MIN_SUM[index])


asyncio.run(parce(PC_CATEGORY_LINKS))
