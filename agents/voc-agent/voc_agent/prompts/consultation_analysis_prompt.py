"""Prompt template for the consultation analysis agent."""

from langfuse import Langfuse

langfuse = Langfuse()
prompt = langfuse.get_prompt("consultation_analysis/system", label="latest")
