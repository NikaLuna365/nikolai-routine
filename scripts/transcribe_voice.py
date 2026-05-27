#!/usr/bin/env python3
"""Voice-message transcription — STUB (disabled in the current version).

Voice notes are intentionally not transcribed yet (cost). This stub reserves
the interface for the weekly Routine to enable later, for high-priority
monitored chats only.

# TODO: implement Whisper API integration for voice message transcription
# Will be used by weekly Routine for high-priority monitored chats only
# Env: OPENAI_API_KEY
# Cost estimate: ~$0.006/min
"""
from __future__ import annotations


def transcribe(audio_path: str) -> str:
    raise NotImplementedError("Voice transcription disabled in current version")


if __name__ == "__main__":
    raise NotImplementedError("Voice transcription disabled in current version")
