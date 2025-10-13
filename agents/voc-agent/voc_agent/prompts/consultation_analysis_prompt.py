"""Prompt template for the consultation analysis agent."""

from langfuse import Langfuse

# https://langfuse.data.socar.me/project/cmgkfrz3b0008zf07imvujftv/prompts/consultation_analysis%2Fsystem
langfuse = Langfuse()
prompt = langfuse.get_prompt("consultation_analysis/system", label="latest")
