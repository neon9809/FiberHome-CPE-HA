import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "Modem5GTemperature": {
        "name": "5G Modem Temperature",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "transform": lambda x: round(float(x) / 1000, 1) if x else None
    },
    "Modem4GTemperature": {
        "name": "4G Modem Temperature",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "transform": lambda x: round(float(x) / 1000, 1) if x else None
    },
    "CPUUsage": {
        "name": "CPU Usage",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:cpu-64-bit",
        "transform": lambda x: round(float(x), 2) if x else None
    },
    "MemoryUsage": {
        "name": "Memory Usage",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE,
        "icon": "mdi:memory",
        "transform": lambda x: x
    },
    "UpTime": {
        "name": "Uptime",
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfTime.SECONDS,
        "icon": "mdi:clock-outline",
        "transform": lambda x: int(x) if x else None
    },
    "RSRP": {
        "name": "RSRP",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "icon": "mdi:signal-cellular-3",
        "transform": lambda x: int(x) if x else None
    },
    "RSSI": {
        "name": "RSSI",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "icon": "mdi:signal-cellular-3",
        "transform": lambda x: int(x) if x else None
    },
    "SINR": {
        "name": "SINR",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dB",
        "icon": "mdi:signal",
        "transform": lambda x: int(x) if x else None
    },
    "RSRQ": {
        "name": "RSRQ",
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": "dB",
        "icon": "mdi:signal",
        "transform": lambda x: int(x) if x else None
    },
    "BAND": {
        "name": "Band",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:radio-tower",
        "transform": lambda x: x
    },
    "PCI": {
        "name": "PCI",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:radio-tower",
        "transform": lambda x: x
    },
    "SSB_RSRP": {
        "name": "SSB RSRP",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "icon": "mdi:signal-cellular-3",
        "transform": lambda x: int(x) if x else None
    },
    "TodayTotalTxBytes": {
        "name": "Today Upload",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:upload",
        "transform": lambda x: int(x) if x else None
    },
    "TodayTotalRxBytes": {
        "name": "Today Download",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:download",
        "transform": lambda x: int(x) if x else None
    },
    "MonthTxBytes": {
        "name": "Month Upload",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:upload-multiple",
        "transform": lambda x: int(x) if x else None
    },
    "MonthRxBytes": {
        "name": "Month Download",
        "device_class": SensorDeviceClass.DATA_SIZE,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfInformation.BYTES,
        "icon": "mdi:download-multiple",
        "transform": lambda x: int(x) if x else None
    },
    "SIMStatus": {
        "name": "SIM Status",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:sim",
        "transform": lambda x: x
    },
    "NetworkMode": {
        "name": "Network Mode",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:network",
        "transform": lambda x: x
    },
    "CarrierName": {
        "name": "Carrier Name",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "icon": "mdi:domain",
        "transform": lambda x: x
    }
}

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Fiberhome CPE sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    
    # Create sensors for each tracked data point
    for key, config in SENSOR_TYPES.items():
        sensors.append(FiberhomeCPESensor(coordinator, key, config))

    # Add the latest message sensor if enabled
    enable_sms = entry.options.get(
        CONF_ENABLE_LATEST_MESSAGE,
        entry.data.get(CONF_ENABLE_LATEST_MESSAGE, DEFAULT_ENABLE_LATEST_MESSAGE)
    )
    if enable_sms:
        sensors.append(FiberhomeCPESMSMessageSensor(coordinator))

    async_add_entities(sensors, True)


class FiberhomeCPESensor(CoordinatorEntity, SensorEntity):
    """Representation of a Fiberhome CPE Sensor."""

    def __init__(self, coordinator, key, config):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._config = config
        
        # Device info
        data = self.coordinator.data or {}
        model = data.get("ModelName", "Fiberhome 5G CPE")
        sw_version = data.get("SoftwareVersion", "Unknown")
        hw_version = data.get("HardwareVersion", "Unknown")
        serial = data.get("SerialNumber", "Unknown")

        self._attr_name = f"Fiberhome {config['name']}"
        self._attr_unique_id = f"fiberhome_cpe_{serial}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial)},
            "name": model,
            "manufacturer": "Fiberhome",
            "model": model,
            "sw_version": sw_version,
            "hw_version": hw_version,
        }
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        val = self.coordinator.data.get(self._key)
        try:
            return self._config["transform"](val)
        except Exception:
            return None


class FiberhomeCPESMSMessageSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Fiberhome CPE Latest Message Sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        data = self.coordinator.data or {}
        model = data.get("ModelName", "Fiberhome 5G CPE")
        serial = data.get("SerialNumber", "Unknown")

        self._attr_name = "Fiberhome Latest Message"
        self._attr_unique_id = f"fiberhome_cpe_{serial}_latest_message"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, serial)},
            "name": model,
            "manufacturer": "Fiberhome",
            "model": model,
        }
        self._attr_icon = "mdi:message-text"

    @property
    def native_value(self):
        """Return the sender of the latest message as the state."""
        if not self.coordinator.data:
            return None
        sms = self.coordinator.data.get("latest_sms")
        if sms:
            return sms.get("phone", "Unknown")
        return "None"

    @property
    def extra_state_attributes(self):
        """Return the content and time of the latest message as attributes."""
        if not self.coordinator.data:
            return {}
        sms = self.coordinator.data.get("latest_sms")
        if sms:
            return {
                "content": sms.get("content", ""),
                "time": sms.get("time", ""),
                "id": sms.get("id", "")
            }
        return {}
