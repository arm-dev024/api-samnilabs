#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
from datetime import datetime

from app.bot.pipeline import PipelineConfig, run_pipeline
from app.config import settings


async def run_bot(webrtc_connection):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")

    config = PipelineConfig(
        system_prompt=(
            f"You are a friendly and concise Barber Shop assistant. "
            f"To create an appointment, ask for the user's name, date, time, and phone. "
            f"Notes are optional; if not provided, pass an empty string to the function. "
            f"Once you have the details, use 'create_appointment'. "
            f"Current date and time: {current_datetime}."
            f"After successfully creating the appointment, thank the user and say goodbye."
        ),
        model=settings.openai_model,
        voice_id=settings.deepgram_voice_id,
        label="bot",
    )

    await run_pipeline(webrtc_connection, config)
