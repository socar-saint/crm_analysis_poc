# ruff: noqa: E501

"""오케스트레이션 프롬프트."""

from langfuse import Langfuse

# https://langfuse.data.socar.me/project/cmgkfrz3b0008zf07imvujftv/prompts?pageIndex=0&pageSize=50&folder=audio_processing
langfuse = Langfuse()
prompt = langfuse.get_prompt("audio_processing/system", label="latest")
