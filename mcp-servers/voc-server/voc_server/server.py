"""Server."""

import asyncio
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .audiofile_tools import opus2wav
from .pi_masking import mask_pii
from .transcribe_tools import azure_gpt_transcribe

logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

mcp = FastMCP("STT Server", host="localhost", port=9000)


@mcp.tool(description="Masking private information contained in context")
def mask_pii_tool(text: str) -> str:
    """Masking private information contained in context."""
    logging.info("[mask_pii] len(text)=%d", len(text))
    s = mask_pii(text)
    logging.info("[mask_pii] masked_len=%d", len(s))
    return s


@mcp.tool(description="Convert .opus/.ogg to 16kHz 2ch PCM16 .wav")
def opus2wav_tool(input_path: str, out_dir: str, sr: int, ch: int) -> Any:
    """Convert .opus/.ogg to 16kHz 2ch PCM16 .wav."""
    logging.info("[opus2wav] input file: %s", input_path)
    s = opus2wav(input_path, out_dir, sr, ch)
    logging.info("[opus2wav] output file: %s", out_dir)
    return s


@mcp.tool(description="Transcribe audio file using gpt-4o-transcribe via Azure")
def gpt_transcribe_tool(file_path: str, language: str, timestamps: bool) -> Any:
    """Transcribe audio file using gpt-4o-transcribe via Azure."""

    logging.info("[azure_gpt_transcribe] audio file: %s", file_path)
    s = azure_gpt_transcribe(file_path, language, timestamps)
    return s


async def shutdown(signal: asyncio.Event, loop: asyncio.AbstractEventLoop) -> None:
    """Cleanup tasks tied to the server's shutdown."""
    print("\nShutdown event received...")

    # Get all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    # Cancel all tasks
    for task in tasks:
        task.cancel()

    print(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)

    # Stop the loop
    loop.stop()
    print("Shutdown complete!")


# Main entry point with graceful shutdown handling
if __name__ == "__main__":
    try:
        # The MCP masks private information uses asyncio.run() internally
        mcp.run(transport="sse")
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
        # The asyncio event loop has already been stopped by the KeyboardInterrupt
        print("Server has been shut down")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        print("Thank you for using the private information masking MCP Server!")
