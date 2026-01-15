import asyncio
import json
import pathlib

from links import PC_CATEGORY_LINKS
from playwright.async_api import Page, async_playwright


async def parce_links(link: str, page: Page) -> list[str | None]:
    product_links = []
    await page.goto(f"https://www.ittelo.ru{link}")
    flag = True
    while flag:
        button_show_more = await page.locator("//a[@class='catalog-list__show-more']").count()
        if button_show_more > 0:
            await page.locator("//a[@class='catalog-list__show-more']").click()
        else:
            flag = False
    await page.wait_for_selector("//div[@class='catalog_block_item']", timeout=15000)
    links = page.locator("//div[@data-href]")
    count = await links.count()

    for i in range(count):
        result = await links.nth(i).get_attribute("data-href")
        product_links.append(result)
    return product_links


async def take_data_from_links(links: list[str | None], page: Page, index: int) -> list[str]:
    data: list[str] = []
    for link in links:
        try:
            await page.goto(f"https://www.ittelo.ru{link}")
            price = await page.locator('//span[@class="full-price"]').inner_text()
            price_int = int(price.replace("\xa0", "").replace("₽", "").replace(" ", ""))
            if price_int > 15000:  # noqa: PLR2004
                div = page.locator('//div[@class="row"]')
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
            data_from_links = await take_data_from_links(links, page, index)


asyncio.run(parce(PC_CATEGORY_LINKS))
