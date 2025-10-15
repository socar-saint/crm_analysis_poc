"""오케스트레이션 프롬프트."""

from langfuse import Langfuse

langfuse = Langfuse()
prompt = langfuse.get_prompt("orchestrator/system", label="latest")
