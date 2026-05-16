import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    enable_sms = entry.options.get(
        CONF_ENABLE_LATEST_MESSAGE,
        entry.data.get(CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE),
    )
    if not enable_sms:
        return

    async_add_entities([FiberhomeCPENewSMSBinarySensor(coordinator, entry)], True)


class FiberhomeCPENewSMSBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)

        data = self.coordinator.data or {}
        model = data.get("ModelName", "Fiberhome 5G CPE")
        serial = data.get("SerialNumber") or entry.unique_id or entry.entry_id

        self._attr_name = "Fiberhome New SMS"
        self._attr_unique_id = f"fiberhome_cpe_{serial}_sms_has_unread"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial)},
            "name": model,
            "manufacturer": "Fiberhome",
            "model": model,
        }
        self._attr_icon = "mdi:message-alert"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.get("sms_has_unread"))
