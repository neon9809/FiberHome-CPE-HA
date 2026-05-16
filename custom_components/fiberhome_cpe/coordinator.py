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
        self.latest_sms = None
        
        super().__init__(
            hass,
            _LOGGER,
            name="Fiberhome CPE",
            update_interval=timedelta(seconds=refresh_interval),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            details = await self.hass.async_add_executor_job(self.client.get_device_details)
            sim_info = await self.hass.async_add_executor_job(self.client.get_sim_info)
            signal_info = await self.hass.async_add_executor_job(self.client.get_signal_info)
            traffic_stats = await self.hass.async_add_executor_job(self.client.get_traffic_stats)

            data = {}
            data.update(details or {})
            data.update(sim_info or {})
            data.update(signal_info or {})
            data.update(traffic_stats or {})

            if not data:
                raise UpdateFailed("Error fetching device data")

            # Calculate Memory Usage
            if data.get('MemoryTotal') and data.get('MemoryFree'):
                try:
                    total = float(data['MemoryTotal'])
                    free = float(data['MemoryFree'])
                    data['MemoryUsage'] = round((total - free) / total * 100, 2)
                except ValueError:
                    data['MemoryUsage'] = None
                    
            if self.enable_sms:
                # Check for new SMS
                has_new_sms = await self.hass.async_add_executor_job(self.client.get_new_sms_flag)
                if has_new_sms:
                    sms_list = await self.hass.async_add_executor_job(self.client.get_unread_sms)
                    if sms_list:
                        # Sort to get the latest one, assuming ID or time can determine it
                        # The last in the list or highest ID is usually the latest
                        for sms in sms_list:
                            self.latest_sms = sms
                            _LOGGER.info("New SMS received from %s", sms.get('phone'))
                            # Mark as read
                            await self.hass.async_add_executor_job(self.client.mark_sms_read, sms.get('id'))

            data['latest_sms'] = self.latest_sms
            return data

        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")
