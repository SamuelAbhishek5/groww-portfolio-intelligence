import json
import logging
from typing import Optional
from backend.ai.chatbot_prompt import SYSTEM_PROMPT_CHAT
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.llm_client import BaseLLMClient, GeminiLLMClient
logger = logging.getLogger(__name__)

class PortfolioChatbot:
    """A chatbot that answers user questions about a financial portfolio based on provided data."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self.llm_client = llm_client or GeminiLLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def chat(self, 
             user_query: str, 
             portfolio_json: dict, 
             risk_metrics: dict, 
             health_metrics: dict, 
             benchmark_metrics: dict, 
             opportunity_result: dict, 
             timeout: int = 30,
             system_prompt: str = SYSTEM_PROMPT_CHAT) -> dict:
        try:
            prompt = self.prompt_builder.build_prompt(
                portfolio_json=portfolio_json,
                risk_metrics=risk_metrics,
                health_metrics=health_metrics,
                benchmark_metrics=benchmark_metrics,
                opportunity_result=opportunity_result,
            )
            full_prompt = (
                f"--- PORTFOLIO REPORT DATA ---\n"
                f"{prompt}\n\n"
                f"--- USER QUESTION ---\n"
                f"{user_query}"
            )
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            return {"answer": "I'm sorry, I encountered an error while preparing your request."}

        try:
            raw_response = self.llm_client.generate(
                prompt=full_prompt, 
                system_prompt=system_prompt, 
                timeout=timeout
                )
            return self._parse_json_response(raw_response)
            
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            return {"answer": "I'm sorry, I encountered an error while processing your request."}

    def _parse_json_response(self, raw_response: str) -> dict:
        """
        Safely parses the JSON output from the LLM, stripping accidental markdown formatting if present.
        """
        cleaned_response = raw_response.strip()
        
        # Strip markdown formatting just in case the LLM ignores the strict instruction
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
            
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
            
        try:
            return json.loads(cleaned_response.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw response: {raw_response}")
            return {"answer": "I generated a response, but it was not in the expected format."}