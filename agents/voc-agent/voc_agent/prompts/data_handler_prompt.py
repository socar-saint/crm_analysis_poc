# ruff: noqa: E501

"""데이터 적재용 프롬프트."""

from langfuse import Langfuse

langfuse = Langfuse()
prompt = langfuse.get_prompt("data_handler/system", label="latest")
