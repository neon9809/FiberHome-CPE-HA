import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FiberhomeCPEClient

_LOGGER = logging.getLogger(__name__)

class FiberhomeCPECoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: FiberhomeCPEClient, refresh_interval: int, enable_sms: bool):
        """Initialize."""
        self.client = client
        self.enable_sms = enable_sms
        self.latest_sms: dict[str, str] | None = None
        
        super().__init__(
            hass,
            _LOGGER,
            name="Fiberhome CPE",
            update_interval=timedelta(seconds=refresh_interval),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            details = await self.client.get_device_details()
            sim_info = await self.client.get_sim_info()
            signal_info = await self.client.get_signal_info()
            traffic_stats = await self.client.get_traffic_stats()

            data = {}
            data.update(details or {})
            data.update(sim_info or {})
            data.update(signal_info or {})
            data.update(traffic_stats or {})

            if not data:
                raise UpdateFailed("Error fetching device data")

            if data.get('MemoryTotal') and data.get('MemoryFree'):
                try:
                    total = float(data['MemoryTotal'])
                    free = float(data['MemoryFree'])
                    data['MemoryUsage'] = round((total - free) / total * 100, 2)
                except ValueError:
                    data['MemoryUsage'] = None
                    
            if self.enable_sms:
                data["sms_new_flag"] = await self.client.get_new_sms_flag()
                sms_list = await self.client.get_unread_sms()
                data["sms_unread_count"] = len(sms_list)
                data["sms_has_unread"] = len(sms_list) > 0
                if sms_list:
                    self.latest_sms = sms_list[-1]
                data["latest_sms"] = self.latest_sms
            else:
                data["sms_unread_count"] = 0
                data["sms_has_unread"] = False
                data["latest_sms"] = None
            return data

        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")
