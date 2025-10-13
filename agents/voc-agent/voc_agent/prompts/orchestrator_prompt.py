"""오케스트레이션 프롬프트."""

from langfuse import Langfuse

# https://langfuse.data.socar.me/project/cmgkfrz3b0008zf07imvujftv/prompts/orchestrator%2Fsystem
langfuse = Langfuse()
prompt = langfuse.get_prompt("orchestrator/system", label="latest")
