import re

import regex
from bs4 import BeautifulSoup, Comment
from bs4.element import NavigableString
from nltk.corpus import stopwords

sw = stopwords.words("russian")


def clean_text(text: str) -> str:
    if not text:
        return ""

    # ВАЖНО: сохраняем ВСЕ цены перед очисткой
    # Паттерн для ВСЕХ возможных форматов цен:
    # 1. С символом валюты: 419 700 ₽, 419,700₽, $99.99, 99,99€, 100.50£
    # 2. С текстом валюты: 419 700 руб, 99.99 USD, 100 евро
    # 3. Просто числа с разделителями: 419,700, 1.299,99, 100 500
    # 4. С диапазонами: 100-200 ₽, 99.99-149.99$
    price_patterns = [
        # С символом валюты (любой символ валюты)
        r"(\d{1,3}(?:[ ,.\u00A0]?\d{3})*(?:[.,]\d{1,2})?\s*[₽$€£¥₴₸₾֏؋৳៛﷼₹₨₪₩₭₮₦₱₲₺₼₽₿฿₡₫₤₥₧₨₫₭₮₯₰₱₲₳₵₶₷₸₹₺₻₼₽₾₿]+)",
        # С текстом валюты (рубль, dollar, euro и т.д.)
        r"(\d{1,3}(?:[ ,.\u00A0]?\d{3})*(?:[.,]\d{1,2})?\s*(?:руб|рубль|рублей|RUB|USD|EUR|GBP|UAH|KZT|BYN|тенге|доллар|евро|фунт|гривна|гривен|belarus))",
        # Просто числа с разделителями (возможно, это цены)
        r"(\b\d{1,3}(?:[ ,.\u00A0]\d{3})+(?:[.,]\d{1,2})?\b)",
        # Диапазоны цен
        r"(\d{1,3}(?:[ ,.\u00A0]?\d{3})*(?:[.,]\d{1,2})?\s*[-–]\s*\d{1,3}(?:[ ,.\u00A0]?\d{3})*(?:[.,]\d{1,2})?\s*[₽$€£]?)",
    ]

    # Сохраняем ВСЕ найденные цены с их позициями
    price_matches = []
    for pattern in price_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            price_matches.append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
            })

    # Сортируем по позиции
    price_matches.sort(key=lambda x: x["start"])  # noqa: FURB118

    # Создаем список цен
    saved_prices = [match["text"] for match in price_matches]

    # Разделяем текст на русские и английские части
    text_lower = text.lower()

    # Удаляем markdown-картинки ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text_lower = re.sub(r"!\[.*?\]\(.*?\)", "", text_lower)

    # Удаляем markdown-ссылки [текст](url)
    text = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text)
    text_lower = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text_lower)

    # Удаляем пустые [](), [](url), [](#xxx)
    text = re.sub(r"\[\]\([^)]*\)", "", text)
    text_lower = re.sub(r"\[\]\([^)]*\)", "", text_lower)
    text = re.sub(r"\[\]\s*", "", text)
    text_lower = re.sub(r"\[\]\s*", "", text_lower)

    # Удаляем HTML-теги
    text = re.sub(r"<[^>]+>", "", text)
    text_lower = re.sub(r"<[^>]+>", "", text_lower)

    # Удаляем mustache-переменные {{…}}
    text = re.sub(r"{{[^{}]+}}", "", text)
    text_lower = re.sub(r"{{[^{}]+}}", "", text_lower)

    # Удаляем жирный/курсив/зачёркивание markdown
    text = re.sub(r"[\*\_~]{1,3}", "", text)
    text_lower = re.sub(r"[\*\_~]{1,3}", "", text_lower)

    # Полное удаление emoji (НО сохраняем символы валют!)
    emoji_pattern = regex.compile(
        r"[\U0001F000-\U0001FFFF]"
        r"|[\U00002600-\U000027BF]"
        r"|[\U00002B50-\U00002BFF]"
        r"|[\U0001F600-\U0001F64F]"
        r"|[\U0001F300-\U0001F5FF]"
        r"|[\U0001F680-\U0001F6FF]"
        r"|[\U0001F900-\U0001F9FF]"
        r"|[\U0001FA00-\U0001FA6F]"
        r"|[\U00002702-\U000027B0]"
        r"|[\U000024C2-\U0001F251]"
        r"|[\U000E0020-\U000E007F]"
    )
    text = regex.sub(emoji_pattern, "", text)
    text_lower = regex.sub(emoji_pattern, "", text_lower)

    # Удаляем email
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "", text)
    text_lower = re.sub(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", "", text_lower)

    # Удаление всех URL (http, https, www, bare domain)
    url_pattern = r"""
        (?:
            https?:\/\/[^\s]+
            |
            www\.[^\s]+
            |
            \b[\w.-]+\.(?:ru|com|net|org|io|ai|info|biz|su|co|me|by|ua|kz|pro)\b[^\s]*
        )
    """
    text = re.sub(url_pattern, "", text, flags=re.VERBOSE | re.IGNORECASE)
    text_lower = re.sub(url_pattern, "", text_lower, flags=re.VERBOSE | re.IGNORECASE)

    # Удаляем UTM-метки и query params ?utm= ... &ref=
    text = re.sub(r"\?(utm|ref|yclid|fbclid)[^ \n]+", "", text, flags=re.IGNORECASE)
    text_lower = re.sub(r"\?(utm|ref|yclid|fbclid)[^ \n]+", "", text_lower, flags=re.IGNORECASE)

    # Удаляем телефонные номера (но только те, которые явно являются телефонами)
    # Более точный паттерн для телефонов
    phone_pattern = r"""
        \b(?:тел\.?|телефон|phone|моб\.?|mobile)\s*[:.]?\s*(?:\+7|8|7|\+?3)?[\s\-()]*(?:\(\d{2,5}\)|\d{2,5})[\s\-()]*\d{2,5}[\s\-]?\d{2,5}[\s\-]?\d{2,5}\b
        |
        \b(?:\+?[78]\s*[-.(]?\s*\d{3}\s*[-.)]?\s*\d{3}\s*[-.]?\s*\d{2}\s*[-.]?\s*\d{2})\b
    """
    text = re.sub(phone_pattern, "", text, flags=re.VERBOSE | re.IGNORECASE)
    text_lower = re.sub(phone_pattern, "", text_lower, flags=re.VERBOSE | re.IGNORECASE)

    # Удаляем #tag-мусор
    text = re.sub(r"#\w+(-\d+)?", "", text)
    text_lower = re.sub(r"#\w+(-\d+)?", "", text_lower)

    # Удаляем скриптовые врезки типа () , ( ) , [] , {}
    text = re.sub(r"\(\s*\)", "", text)
    text_lower = re.sub(r"\(\s*\)", "", text_lower)
    text = re.sub(r"\[\s*\]", "", text)
    text_lower = re.sub(r"\[\s*\]", "", text_lower)
    text = re.sub(r"\{\s*\}", "", text)
    text_lower = re.sub(r"\{\s*\}", "", text_lower)

    # Удаление мусорных символов (НО сохраняем символы валют!)
    # Создаем список символов для удаления, исключая символы валют
    garbage_chars = "×✔★▪▫•◦‣⁃⦾⦿◉○◌◍◎●◐◑◒◓◔◕◖◗◘◙◚◛◜◝◞◟◠◡◢◣◤◥◦◧◨◩◪◫◬◭◮◯"
    for char in garbage_chars:
        text = text.replace(char, "")
        text_lower = text_lower.replace(char, "")

    # Удаляем фразы типа "загрузка карты..."
    text = re.sub(r"загрузка карты\.\.\.", "", text, flags=re.IGNORECASE)
    text_lower = re.sub(r"загрузка карты\.\.\.", "", text_lower, flags=re.IGNORECASE)

    # Удаление маркеров списков
    text = re.sub(r"^\s*[\*\•\-\–\+]\s+", "", text, flags=re.MULTILINE)
    text_lower = re.sub(r"^\s*[\*\•\-\–\+]\s+", "", text_lower, flags=re.MULTILINE)

    # Теперь обрабатываем слова
    words = text.split()
    words_lower = text_lower.split()

    processed_words = []
    for i, word in enumerate(words):
        lower_word = words_lower[i] if i < len(words_lower) else word.lower()

        # ВАЖНО: проверяем, является ли слово ценой
        is_price = False

        # Проверяем все сохраненные цены
        for price in saved_prices:
            # Если это слово является частью цены
            if price in word or word in price:
                is_price = True
                processed_words.append(word)
                break

        # Если это не цена, обрабатываем как обычно
        if not is_price:
            # Проверяем, является ли слово русским (содержит кириллические символы)
            if re.search(r"[а-яёА-ЯЁ]", word):
                # Обрабатываем только русские слова
                punctuations = "@#!?+&amp;*[]-%.:/();$=&gt;&lt;|{}^" + "'`" + "_"
                cleaned_word = word
                for p in punctuations:
                    cleaned_word = cleaned_word.replace(p, "")

                cleaned_lower = cleaned_word.lower()

                # Удаляем стоп-слово только если оно русское и в нижнем регистре есть в стоп-словах
                if cleaned_lower not in sw:
                    processed_words.append(cleaned_word)
            # Английские и другие не-русские слова оставляем как есть
            # Проверяем, не выглядит ли как цена
            elif any(char in word for char in "₽$€£¥") or re.search(r"\d+[.,]\d{2}", word):
                # Выглядит как цена, оставляем
                processed_words.append(word)
            else:
                # Обычное слово
                processed_words.append(word)

    text = " ".join(processed_words)

    # ВОССТАНАВЛИВАЕМ УДАЛЕННЫЕ ЦЕНЫ
    # Проверяем, какие цены из сохраненных отсутствуют в результате
    for price in saved_prices:
        # Ищем цену в результате (частично, так как могли быть изменены пробелы)
        price_clean = re.sub(r"\s+", " ", price.strip())
        result_clean = re.sub(r"\s+", " ", text)

        if price_clean not in result_clean:
            # Пытаемся найти похожую цену
            price_num = re.sub(r"[^\d.,]", "", price)
            found = False

            # Ищем числа в результате
            for match in re.finditer(r"\d{1,3}(?:[ ,.]?\d{3})*(?:[.,]\d{1,2})?", result_clean):
                result_num = re.sub(r"[^\d.,]", "", match.group())
                if price_num == result_num:
                    found = True
                    break

            # Если не нашли, добавляем цену обратно
            if not found:
                # Добавляем в конец текста или в соответствующее место
                lines = text.splitlines()
                added = False

                # Ищем строку с "коротко о товаре"
                for i, line in enumerate(lines):
                    if "коротко о товаре" in line.lower():
                        lines[i] = line.rstrip() + " " + price
                        added = True
                        break

                # Если не нашли подходящее место, добавляем в начало
                if not added:
                    lines.insert(0, price)

                text = "\n".join(lines)

    # Удаляем любые повторяющиеся пунктуации !!!, ???, ... (но не в ценах!)
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        # Разделяем строку на части, возможно содержащие цены
        parts = []
        current = ""
        i = 0
        while i < len(line):
            # Проверяем, начинается ли с символа числа или валюты
            if line[i].isdigit() or line[i] in "₽$€£¥":
                # Нашли начало возможной цены
                j = i
                while j < len(line) and (line[j].isdigit() or line[j] in "₽$€£¥ ,."):
                    j += 1
                price_part = line[i:j]
                if current:
                    parts.append(current)
                    current = ""
                parts.append(price_part)
                i = j
            else:
                current += line[i]
                i += 1

        if current:
            parts.append(current)

        # Обрабатываем каждую часть
        processed_parts = []
        for part in parts:
            # Если часть похожа на цену, не обрабатываем
            if any(char in part for char in "₽$€£¥") or re.search(r"\d+[.,]\d{2}", part):
                processed_parts.append(part)
            else:
                # Удаляем повторяющуюся пунктуацию
                cleaned_part = re.sub(r"([!?.,:;]){2,}", r"\1", part)
                processed_parts.append(cleaned_part)

        cleaned_lines.append("".join(processed_parts))

    text = "\n".join(cleaned_lines)

    # Удаляем «голые» скобки после очистки (но не в ценах!)
    text = re.sub(r"(?<!\d)[()\[\]{}](?!\d)", "", text)

    # Сжимаем пробелы и переносы (но не в ценах!)
    # Сохраняем неразрывные пробелы в ценах (\u00A0)
    text = re.sub(r"([^\d₽$€£¥])\s{2,}([^\d₽$€£¥])", r"\1 \2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Убираем пробелы перед пунктуацией (но не в ценах!)
    text = re.sub(r"([^\d₽$€£¥])\s+([.,!?:;])", r"\1\2", text)

    # Удаляем лишние пустые строки
    text = text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    return text


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # 1. Полностью удаляем мусорные теги
    for tag in soup.find_all([
        "script",
        "style",
        "meta",
        "link",
        "noscript",
        "table",
        "tr",
        "td",
        "th",
    ]):
        tag.decompose()

    # 2. Удаляем HTML-комментарии
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # 3. Проходим по всем тегам
    for tag in soup.find_all(True):
        # Разрешённые атрибуты
        allowed_attrs = {}

        if "id" in tag.attrs:
            allowed_attrs["id"] = tag.attrs["id"]

        if "class" in tag.attrs:
            allowed_attrs["class"] = tag.attrs["class"]

        # сохраняем ссылки
        if tag.name == "a" and "href" in tag.attrs:
            allowed_attrs["href"] = tag.attrs["href"]

        if tag.name in {"img", "source", "video", "audio"} and "src" in tag.attrs:
            allowed_attrs["src"] = tag.attrs["src"]

        tag.attrs = allowed_attrs

        # 4. Удаляем весь текст, включая пробелы и переносы
        for child in list(tag.contents):
            if isinstance(child, NavigableString):
                child.extract()

    text = str(soup)
    return re.sub(r"\s+", "", text)
