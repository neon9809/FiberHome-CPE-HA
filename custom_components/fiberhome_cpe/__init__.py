from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_ENABLE_LATEST_MESSAGE,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_ENABLE_LATEST_MESSAGE,
)
from .api import FiberhomeCPEClient
from .coordinator import FiberhomeCPECoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fiberhome CPE from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    validated_clients = domain_data.setdefault("validated_clients", {})

    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    username = entry.options.get(CONF_USERNAME, entry.data.get(CONF_USERNAME))
    password = entry.options.get(CONF_PASSWORD, entry.data.get(CONF_PASSWORD))
    
    refresh_interval = entry.options.get(
        CONF_REFRESH_INTERVAL, 
        entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
    )
    enable_sms = entry.options.get(
        CONF_ENABLE_LATEST_MESSAGE,
        entry.data.get(CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE)
    )

    client = validated_clients.pop(entry.unique_id, None)
    if client is None:
        client = FiberhomeCPEClient(host, username, password)
    
    coordinator = FiberhomeCPECoordinator(
        hass=hass,
        client=client,
        refresh_interval=refresh_interval,
        enable_sms=enable_sms,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        message = str(err).lower()
        if "password" in message or "auth" in message:
            raise ConfigEntryAuthFailed from err
        raise ConfigEntryNotReady from err

    domain_data[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.client.close)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
