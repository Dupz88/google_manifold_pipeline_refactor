"""
title: Google GenAI Manifold Pipeline
author: Marc Lopez (refactor by justinh-rahb)
date: 2024-06-06
version: 1.1
license: MIT
description: A pipeline for generating text using Google's GenAI models in Open-WebUI.
requirements: google-generativeai
environment_variables: GOOGLE_API_KEY
"""

from typing import List, Union, Iterator
import os

from pydantic import BaseModel

import google.generativeai as genai
from google.generativeai.types import GenerationConfig


class Pipeline:
    """Google GenAI pipeline"""

    class Valves(BaseModel):
        """Options to change from the WebUI"""

        GOOGLE_API_KEY: str = ""

    def __init__(self):
        self.type = "manifold"
        self.id = "google_genai"
        self.name = "Google: "

        self.valves = self.Valves(**{"GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", "")})
        self.pipelines = []

        genai.configure(api_key=self.valves.GOOGLE_API_KEY)
        self.update_pipelines()

    async def on_startup(self) -> None:
        """This function is called when the server is started."""

        print(f"on_startup:{__name__}")

    async def on_shutdown(self) -> None:
        """This function is called when the server is stopped."""

        print(f"on_shutdown:{__name__}")

    async def on_valves_updated(self) -> None:
        """This function is called when the valves are updated."""

        print(f"on_valves_updated:{__name__}")
        genai.configure(api_key=self.valves.GOOGLE_API_KEY)
        self.update_pipelines()

    def update_pipelines(self) -> None:
        """Update the available models from Google GenAI"""

        # Predefined list of models
        predefined_models = [
            {"id": "chat-bison-001", "name": "PaLM 2 Chat (Legacy)"},
            {"id": "text-bison-001", "name": "PaLM 2 (Legacy)"},
            {"id": "embedding-gecko-001", "name": "Embedding Gecko"},
            {"id": "gemini-1.0-pro", "name": "Gemini 1.0 Pro"},
            {"id": "gemini-1.0-pro-001", "name": "Gemini 1.0 Pro 001 (Tuning)"},
            {"id": "gemini-1.0-pro-latest", "name": "Gemini 1.0 Pro Latest"},
            {"id": "gemini-1.0-pro-vision-latest", "name": "Gemini 1.0 Pro Vision"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-flash-001", "name": "Gemini 1.5 Flash 001"},
            {"id": "gemini-1.5-flash-latest", "name": "Gemini 1.5 Flash Latest"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-pro-001", "name": "Gemini 1.5 Pro 001"},
            {"id": "gemini-1.5-pro-latest", "name": "Gemini 1.5 Pro Latest"},
            {"id": "gemini-pro", "name": "Gemini 1.0 Pro"},
            {"id": "gemini-pro-vision", "name": "Gemini 1.0 Pro Vision"},
            {"id": "embedding-001", "name": "Embedding 001"},
            {"id": "text-embedding-004", "name": "Text Embedding 004"},
            {"id": "aqa", "name": "Attributed Question Answering"},
        ]

        if self.valves.GOOGLE_API_KEY:
            self.pipelines = predefined_models
        else:
            self.pipelines = []

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Iterator]:
        if not self.valves.GOOGLE_API_KEY:
            return "Error: GOOGLE_API_KEY is not set"

        try:
            genai.configure(api_key=self.valves.GOOGLE_API_KEY)

            if model_id.startswith("google_genai."):
                model_id = model_id[12:]
            model_id = model_id.lstrip(".")

            if not model_id.startswith("gemini-"):
                return f"Error: Invalid model name format: {model_id}"

            print(f"Pipe function called for model: {model_id}")
            print(f"Stream mode: {body.get('stream', False)}")

            system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), None)
            
            contents = []
            for message in messages:
                if message["role"] != "system":
                    if isinstance(message.get("content"), list):
                        parts = []
                        for content in message["content"]:
                            if content["type"] == "text":
                                parts.append({"text": content["text"]})
                            elif content["type"] == "image_url":
                                image_url = content["image_url"]["url"]
                                if image_url.startswith("data:image"):
                                    image_data = image_url.split(",")[1]
                                    parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_data}})
                                else:
                                    parts.append({"image_url": image_url})
                        contents.append({"role": message["role"], "parts": parts})
                    else:
                        contents.append({
                            "role": "user" if message["role"] == "user" else "model",
                            "parts": [{"text": message["content"]}]
                        })

            if system_message:
                contents.insert(0, {"role": "user", "parts": [{"text": f"System: {system_message}"}]})

            model = genai.GenerativeModel(model_name=model_id)

            generation_config = GenerationConfig(
                temperature=body.get("temperature", 0.7),
                top_p=body.get("top_p", 0.9),
                top_k=body.get("top_k", 40),
                max_output_tokens=body.get("max_tokens", 8192),
                stop_sequences=body.get("stop", []),
            )

            safety_settings = body.get("safety_settings")

            response = model.generate_content(
                contents,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=body.get("stream", False),
            )

            if body.get("stream", False):
                return self.stream_response(response)
            else:
                return response.text

        except Exception as e:
            print(f"Error generating content: {e}")
            return f"An error occurred: {str(e)}"

    def stream_response(self, response):
        for chunk in response:
            if chunk.text:
                yield chunk.text
