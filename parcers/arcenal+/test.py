import json
import pathlib

from ...depends import yandex_gpt
from ...prompts import PROMPT_MAT_PLATA
from ...utils import clean_text

file = pathlib.Path("/Users/medvedevandre/projects/parce/parcers/arcenal+").read_text(
    encoding="utf-8"
)

result = json.loads(file)

lst = []
for i in result:
    data = clean_text(i)
    lst.append(data)

request = PROMPT_MAT_PLATA.format(data=lst)
count_request = yandex_gpt.get_num_tokens(request)
# gpt = yandex_gpt.invoke(PROMPT_MAT_PLATA.format(data=lst))
# count_answer = yandex_gpt.get_num_tokens(gpt.content)
# print(count_request)
# print(count_answer)
# print(gpt)

# pathlib.Path("result.md").write_text(
#     json.dumps(gpt.content, ensure_ascii=False, indent=2), encoding="utf-8"
# )
