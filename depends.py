from typing import Final

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TextSplitter,
)
from pydantic import SecretStr

from prompts import (
    PROMPT_OPERATIVKA,
    PROMPT_PROCESSOR,
    PROMPT_RESULT,
    PROMPT_SSD,
    PROMPT_VIDEOCARD,
)
from schemas import ChoiseCPU, ChoiseGPU, ChoiseRAM, ChoiseSSD, ServerAnalysisResponse
from settings import settings

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 50

yandex_gpt = ChatOpenAI(
    api_key=SecretStr(settings.api_key),
    model=f"gpt://{settings.folder_id}/gpt-oss-120b/latest",
    base_url="https://llm.api.cloud.yandex.net/v1",
    max_retries=3,
)

text_splitter: Final[TextSplitter] = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)

parcer_gpu = PydanticOutputParser(pydantic_object=ChoiseGPU)
parcer_cpu = PydanticOutputParser(pydantic_object=ChoiseCPU)
parcer_ram = PydanticOutputParser(pydantic_object=ChoiseRAM)
parcer_ssd = PydanticOutputParser(pydantic_object=ChoiseSSD)
parcer_result = PydanticOutputParser(pydantic_object=ServerAnalysisResponse)


gpu_template = PromptTemplate(
    template=PROMPT_VIDEOCARD,
    partial_variables={"format_instructions": parcer_gpu.get_format_instructions()},
    input_variables=["money", "data"],
)

cpu_template = PromptTemplate(
    template=PROMPT_PROCESSOR,
    partial_variables={"format_instructions": parcer_cpu.get_format_instructions()},
    input_variables=["money", "data", "videocard"],
)

ram_template = PromptTemplate(
    template=PROMPT_OPERATIVKA,
    partial_variables={"format_instructions": parcer_ram.get_format_instructions()},
    input_variables=["money", "data", "videocard", "cpu"],
)

ssd_template = PromptTemplate(
    template=PROMPT_SSD,
    partial_variables={"format_instructions": parcer_ssd.get_format_instructions()},
    input_variables=["money", "data", "gpu", "cpu", "ram"],
)

result_template = PromptTemplate(
    template=PROMPT_RESULT,
    partial_variables={"format_instructions": parcer_result.get_format_instructions()},
    input_variables=["budget", "ssd", "gpu", "cpu", "ram"],
)
