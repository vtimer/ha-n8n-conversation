"""Config flow for n8n Conversation integration."""
import logging
from typing import Any, Dict

import voluptuous as vol
import aiohttp

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import DOMAIN, CONF_WEBHOOK_URL, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_WEBHOOK_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
    }
)

async def validate_webhook_url(webhook_url: str, hass) -> bool:
    """Validate the webhook URL can be reached (basic check)."""
    session = async_get_clientsession(hass)
    try:
        # A simple GET might not be enough for all n8n webhooks if they only accept POST.
        # Consider a more robust check if needed, e.g., sending a known test payload via POST.
        async with session.get(webhook_url, timeout=10) as response:
            _LOGGER.debug(f"Webhook validation GET response status: {response.status}")
            # For now, not failing on status code as n8n behavior for GET can vary.
            # The primary goal is to catch DNS or connection errors.
            return True
    except aiohttp.ClientConnectorError:
        _LOGGER.warning(f"Connection error for webhook URL: {webhook_url}")
        return False
    except Exception as e:
        _LOGGER.warning(f"Error validating webhook URL {webhook_url}: {e}")
        return False # Catch any other exception as a validation failure


class N8nConversationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for n8n Conversation."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            webhook_url = user_input[CONF_WEBHOOK_URL]

            if not webhook_url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            # Basic validation, more robust check might be needed for production
            # elif not await validate_webhook_url(webhook_url, self.hass):
            #     errors["base"] = "cannot_connect"
            else:
                # Optional: Check if already configured
                # For simplicity, we allow multiple instances with potentially same URL.
                # If uniqueness is desired:
                # await self.async_set_unique_id(webhook_url) # If webhook_url should be unique
                # self._abort_if_unique_id_configured()
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
            description_placeholders=None,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return N8nConversationOptionsFlowHandler(config_entry)


class N8nConversationOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for n8n conversation."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.current_webhook_url = config_entry.data.get(CONF_WEBHOOK_URL, "")

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Manage the options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            webhook_url = user_input[CONF_WEBHOOK_URL]
            if not webhook_url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            # elif not await validate_webhook_url(webhook_url, self.hass):
            #     errors["base"] = "cannot_connect"
            else:
                # Update the config entry
                # Check if data actually changed to prevent unnecessary reloads
                if self.current_webhook_url != webhook_url:
                    return self.async_create_entry(title="", data={CONF_WEBHOOK_URL: webhook_url})
                return self.async_create_entry(title="", data={}) # No changes


        options_schema = vol.Schema(
            {
                vol.Required(CONF_WEBHOOK_URL, default=self.current_webhook_url): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.URL)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )