"""Conversation agent for n8n Conversation integration."""
import logging
from typing import Literal

import aiohttp
from asyncio import TimeoutError as AsyncTimeoutError  # Differentiate from built-in TimeoutError

from homeassistant.components.conversation import (
    ConversationInput,
    ConversationResult,
    AbstractConversationAgent,
    ChatLog,
    ConversationEntity,
    intent,
    AssistantContent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_WEBHOOK_URL

_LOGGER = logging.getLogger(__name__)


class N8nConversationEntity(ConversationEntity):
    """Represent a n8n conversation entity."""

    def __init__(self, agent: "N8nAgent") -> None:
        """Initialize the entity."""
        self._agent = agent
        self._attr_name = "n8n Conversation"
        self._attr_unique_id = f"n8n_conversation_{agent.entry.entry_id}"

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        """Call the API."""
        result = await self._agent.async_process(user_input)

        # Add the response to the chat log
        if result.response.speech:
            chat_log.async_add_assistant_content_without_tools(
                AssistantContent(
                    agent_id=user_input.agent_id,
                    content=result.response.speech.get("plain", {}).get("speech", ""),
                )
            )

        return result


class N8nAgent(AbstractConversationAgent):
    """n8n Conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.entity = N8nConversationEntity(self)

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return "*"  # Supports all languages, relies on STT/TTS and n8n to handle it

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Process a sentence."""
        webhook_url = self.entry.data.get(CONF_WEBHOOK_URL)
        if not webhook_url:
            _LOGGER.error("n8n webhook URL is not configured for agent %s.", self.entry.entry_id)
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech("n8n webhook URL is not configured.")
            return ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
                continue_conversation=False,
            )

        if user_input.text is None or not user_input.text.strip():
            _LOGGER.debug("Received empty or whitespace-only text input.")
            response = intent.IntentResponse(language=user_input.language)
            response.async_set_speech("I didn't receive any text, please try again.")
            return ConversationResult(
                response=response,
                conversation_id=user_input.conversation_id,
                continue_conversation=False,
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
        error_message = "Sorry, I couldn't process your request with n8n."  # Default error

        try:
            async with session.post(webhook_url, json=payload, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "n8n webhook returned HTTP %s: %s. Payload: %s",
                        response.status, error_text, payload
                    )
                    error_message = f"The n8n service returned an error: {response.status}."
                    response = intent.IntentResponse(language=user_input.language)
                    response.async_set_speech(error_message)
                    return ConversationResult(
                        response=response,
                        conversation_id=user_input.conversation_id,
                        continue_conversation=False,
                    )

                n8n_response_data = await response.json()
                _LOGGER.debug("Received response from n8n: %s", n8n_response_data)

                response_text = n8n_response_data.get("response_text")

                if not response_text:
                    _LOGGER.error("n8n response did not contain 'response_text'. Full response: %s", n8n_response_data)
                    error_message = "The response from n8n was not in the expected format."
                    response = intent.IntentResponse(language=user_input.language)
                    response.async_set_speech(error_message)
                    return ConversationResult(
                        response=response,
                        conversation_id=user_input.conversation_id,
                        continue_conversation=False,
                    )

                response = intent.IntentResponse(language=user_input.language)
                response.async_set_speech(response_text)
                return ConversationResult(
                    response=response,
                    conversation_id=user_input.conversation_id,
                    continue_conversation=n8n_response_data.get("continue_conversation", False),
                )

        except aiohttp.ClientConnectorError:
            _LOGGER.error("Failed to connect to n8n webhook: %s", webhook_url)
            error_message = "Sorry, I couldn't connect to the n8n service."
        except aiohttp.ClientResponseError as e:  # Should be caught by status check above, but as a fallback
            _LOGGER.error("n8n webhook request failed with ClientResponseError %s: %s", e.status, e.message)
            error_message = f"The n8n service request failed: {e.status}."
        except AsyncTimeoutError:  # Specific timeout error
            _LOGGER.error("Timeout while calling n8n webhook: %s", webhook_url)
            error_message = "Sorry, the request to n8n timed out."
        except Exception as e:
            _LOGGER.exception("An unexpected error occurred while processing n8n conversation: %s", e)
            # error_message is already set to a generic one.

        # Fallback error response
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(error_message)
        return ConversationResult(
            response=response,
            conversation_id=user_input.conversation_id,
            continue_conversation=False,
        )
