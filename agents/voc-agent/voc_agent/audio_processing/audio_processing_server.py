"""Audio processing server."""

from a2a.types import AgentSkill

from ..settings import settings
from ..utils import create_agent_a2a_server
from .audio_processing_agent import audio_processing_agent

AUDIO_PROCESSING_SKILL = AgentSkill(
    id="audio_processing_agent",
    name="Audio Processing Agent",
    description=(
        "Run the end-to-end audio workflow: download audio from S3, convert formats, "
        "perform diarization, run STT, and mask sensitive information"
    ),
    tags=["speakers", "dialog", "separation", "stt", "masking"],
    examples=[
        "Process this call recording for transcripts with speaker labels and PII masking.",
        "Download the audio from S3 and return diarized, masked transcripts.",
    ],
)

app = create_agent_a2a_server(
    agent=audio_processing_agent,
    name="Audio Processing Agent",
    description=("Handle downloading S3 audio, format conversion, diarization, STT, and PII masking"),
    skills=[
        AUDIO_PROCESSING_SKILL,
    ],
    host=settings.audio_processing_host,
    port=settings.audio_processing_port,
    public_host=settings.audio_processing_public_host,
).build()
