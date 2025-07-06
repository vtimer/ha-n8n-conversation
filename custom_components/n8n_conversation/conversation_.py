"""Conversation agent for n8n Conversation integration."""
import logging
from typing import Literal

import aiohttp
from asyncio import TimeoutError as AsyncTimeoutError # Differentiate from built-in TimeoutError

from homeassistant.components.conversation import (
    ConversationInput,
    ConversationResult,
    AbstractConversationAgent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
# from homeassistant.helpers import intent # Only if crafting complex intent responses

from .const import CONF_WEBHOOK_URL

_LOGGER = logging.getLogger(__name__)

class N8nAgent(AbstractConversationAgent):
    """n8n Conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return "*" # Supports all languages, relies on STT/TTS and n8n to handle it

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process a sentence."""
        webhook_url = self.entry.data.get(CONF_WEBHOOK_URL)
        if not webhook_url:
            _LOGGER.error("n8n webhook URL is not configured for agent %s.", self.entry.entry_id)
            # Create a minimal error response
            return ConversationResult(
                response=self.async_create_error_response(
                    code="agent_configuration_error",
                    message="n8n webhook URL is not configured."
                ),
                conversation_id=user_input.conversation_id,
            )

        if user_input.text is None or not user_input.text.strip():
            _LOGGER.debug("Received empty or whitespace-only text input.")
            return ConversationResult(
                response=self.async_create_speech_response(
                    message="I didn't receive any text, please try again.",
                ),
                conversation_id=user_input.conversation_id,
            )

        _LOGGER.debug(
            "Processing text: '%s' for language: %s with webhook: %s (Agent: %s, ConvID: %s)",
            user_input.text,
            user_input.language,
            webhook_url,
            self.entry.entry_id,
            user_input.conversation_id
        )

        session = async_get_clientsession(self.hass)
        payload = {
            "text": user_input.text,
            "language": user_input.language,
            "conversation_id": user_input.conversation_id,
            "device_id": user_input.device_id,
            "context": user_input.context.as_dict() if user_input.context else {},
        }
        error_message = "Sorry, I couldn't process your request with n8n." # Default error

        try:
            async with session.post(webhook_url, json=payload, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "n8n webhook returned HTTP %s: %s. Payload: %s",
                        response.status, error_text, payload
                    )
                    error_message = f"The n8n service returned an error: {response.status}."
                    return ConversationResult(
                        response=self.async_create_speech_response(message=error_message),
                        conversation_id=user_input.conversation_id,
                    )

                n8n_response_data = await response.json()
                _LOGGER.debug("Received response from n8n: %s", n8n_response_data)

                response_text = n8n_response_data.get("response_text")

                if not response_text:
                    _LOGGER.error("n8n response did not contain 'response_text'. Full response: %s", n8n_response_data)
                    error_message = "The response from n8n was not in the expected format."
                    return ConversationResult(
                        response=self.async_create_speech_response(message=error_message),
                        conversation_id=user_input.conversation_id,
                    )

                return ConversationResult(
                    response=self.async_create_speech_response(message=response_text),
                    conversation_id=user_input.conversation_id,
                )

        except aiohttp.ClientConnectorError:
            _LOGGER.error("Failed to connect to n8n webhook: %s", webhook_url)
            error_message = "Sorry, I couldn't connect to the n8n service."
        except aiohttp.ClientResponseError as e: # Should be caught by status check above, but as a fallback
            _LOGGER.error("n8n webhook request failed with ClientResponseError %s: %s", e.status, e.message)
            error_message = f"The n8n service request failed: {e.status}."
        except AsyncTimeoutError: # Specific timeout error
            _LOGGER.error("Timeout while calling n8n webhook: %s", webhook_url)
            error_message = "Sorry, the request to n8n timed out."
        except Exception as e:
            _LOGGER.exception("An unexpected error occurred while processing n8n conversation: %s", e)
            # error_message is already set to a generic one.

        # Fallback error response
        return ConversationResult(
            response=self.async_create_speech_response(message=error_message),
            conversation_id=user_input.conversation_id,
        )
