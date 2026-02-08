#!/usr/bin/env python3

import os
import time
from typing import Optional, List, Dict
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class ModelClient:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        top_p: float = 0.9
    ):
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model = model or os.getenv("MODEL_NAME", "gpt-4o")
        self.temperature = temperature if temperature is not None else float(os.getenv("TEMPERATURE", "0.0"))
        self.max_tokens = max_tokens or int(os.getenv("MAX_TOKENS", "4096"))
        self.timeout = timeout or int(os.getenv("TIMEOUT", "100"))
        self.top_p = top_p
        
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
    
    def call(
        self,
        user_text: str,
        system_prompt: Optional[str] = None,
        retry: int = 4,
        backoff: float = 1.5,
        **kwargs
    ) -> str:
        attempt = 0
        
        while True:
            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_text})
                
                params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "timeout": self.timeout,
                    "top_p": self.top_p
                }
                params.update(kwargs)
                
                resp = self.client.chat.completions.create(**params)
                content = resp.choices[0].message.content
                return content.strip() if content else ""
                
            except Exception as e:
                attempt += 1
                if attempt > retry:
                    raise Exception(f"API failed after {retry} retries: {e}")
                time.sleep(backoff ** attempt)
    
    def create_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout
        }
        params.update(kwargs)
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()
