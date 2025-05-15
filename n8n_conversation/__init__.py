"""The n8n Conversation integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent # Ensure intent is imported if used directly, though not in this agent

from .const import DOMAIN, CONF_WEBHOOK_URL
from .conversation import N8nAgent

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up n8n Conversation from a config entry."""
    webhook_url = entry.data.get(CONF_WEBHOOK_URL)

    if not webhook_url:
        _LOGGER.error("Webhook URL not found in config entry for n8n_conversation")
        return False

    # Ensure the domain data structure exists
    hass.data.setdefault(DOMAIN, {})

    agent = N8nAgent(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = agent

    # Register the conversation agent
    # This uses the modern way to register agents.
    try:
        hass.components.conversation.async_set_agent(entry, agent)
        _LOGGER.info("n8n conversation agent set using async_set_agent for entry %s", entry.entry_id)
    except AttributeError:
        _LOGGER.error(
            "Failed to set conversation agent. 'async_set_agent' not available. "
            "Please ensure Home Assistant core is recent enough (2024.2+ recommended)."
        )
        # Clean up if registration fails
        del hass.data[DOMAIN][entry.entry_id]
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]
        return False


    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading n8n_conversation entry: %s", entry.entry_id)
    try:
        hass.components.conversation.async_set_agent(entry, None) # Unregister
        _LOGGER.info("n8n conversation agent unset using async_set_agent for entry %s", entry.entry_id)
    except AttributeError:
        _LOGGER.warning(
            "Could not unset conversation agent via 'async_set_agent' during unload. "
            "Manual cleanup might be incomplete if HA version is older."
        )


    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]
        if not hass.data[DOMAIN]: # If no more entries, remove the domain from hass.data
            del hass.data[DOMAIN]
        _LOGGER.debug("Removed agent from hass.data for entry %s", entry.entry_id)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("n8n_conversation options updated, reloading entry: %s", entry.entry_id)
    # This will tell HA to re-setup the integration with the new config.
    # The old agent will be cleaned up by async_unload_entry and a new one created by async_setup_entry.
    await hass.config_entries.async_reload(entry.entry_id)