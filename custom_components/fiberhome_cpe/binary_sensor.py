import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE

_LOGGER = logging.getLogger(__name__)


def _to_bool(value):
    return str(value).lower() in {"1", "true", "on", "yes"}


BINARY_SENSOR_TYPES = {
    "AirplanOn": {
        "name": "Airplane Mode",
        "icon": "mdi:airplane",
    },
    "RoamingEnable": {
        "name": "Roaming Enabled",
        "icon": "mdi:earth",
    },
    "RoamingConnectStatus": {
        "name": "Roaming Connected",
        "icon": "mdi:earth-arrow-right",
    },
    "CarrierLockEnable": {
        "name": "Carrier Lock Enabled",
        "icon": "mdi:lock-network",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enabled_default": False,
    },
    "connetStatus": {
        "name": "WAN Connected",
        "icon": "mdi:lan-connect",
    },
    "upStatus": {
        "name": "WAN Link Up",
        "icon": "mdi:lan-check",
        "entity_category": EntityCategory.DIAGNOSTIC,
    },
    "IOTRunning": {
        "name": "IoT Service Running",
        "icon": "mdi:chip",
        "entity_category": EntityCategory.DIAGNOSTIC,
        "enabled_default": False,
    },
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FiberhomeCPEHeaderBinarySensor(coordinator, entry, key, config)
        for key, config in BINARY_SENSOR_TYPES.items()
    ]

    enable_sms = entry.options.get(
        CONF_ENABLE_LATEST_MESSAGE,
        entry.data.get(CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE),
    )
    if enable_sms:
        entities.append(FiberhomeCPENewSMSBinarySensor(coordinator, entry))

    async_add_entities(entities, True)


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


class FiberhomeCPEHeaderBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, config):
        super().__init__(coordinator)
        self._key = key

        data = self.coordinator.data or {}
        model = data.get("ModelName", "Fiberhome 5G CPE")
        serial = data.get("SerialNumber") or entry.unique_id or entry.entry_id

        self._attr_name = f"Fiberhome {config['name']}"
        self._attr_unique_id = f"fiberhome_cpe_{serial}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial)},
            "name": model,
            "manufacturer": "Fiberhome",
            "model": model,
        }
        self._attr_icon = config.get("icon")
        self._attr_entity_category = config.get("entity_category")
        self._attr_entity_registry_enabled_default = config.get("enabled_default", True)

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None
        return _to_bool(self.coordinator.data.get(self._key))
