DOMAIN = "fiberhome_cpe"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_ENABLE_LATEST_MESSAGE = "enable_latest_message"

DEFAULT_HOST = "192.168.8.1"
DEFAULT_REFRESH_INTERVAL = 60
DEFAULT_ENABLE_LATEST_MESSAGE = False

MIN_REFRESH_INTERVAL = 1
MAX_REFRESH_INTERVAL = 21600

REQUEST_NODES = {
    "Modem5GTemperature": "X_FH_MobileNetwork.Temperature.Modem5GTemperature",
    "Modem4GTemperature": "X_FH_MobileNetwork.Temperature.Modem4GTemperature",
    "CPUUsage": "DeviceInfo.ProcessStatus.CPUUsage",
    "MemoryTotal": "DeviceInfo.MemoryStatus.Total",
    "MemoryFree": "DeviceInfo.MemoryStatus.Free",
    "SerialNumber": "DeviceInfo.SerialNumber",
    "SoftwareVersion": "DeviceInfo.SoftwareVersion",
    "HardwareVersion": "DeviceInfo.HardwareVersion",
    "ModelName": "DeviceInfo.ModelName",
    "UpTime": "DeviceInfo.UpTime",
    "SIMStatus": "X_FH_MobileNetwork.SIM.1.SIMStatus",
    "IMEI": "X_FH_MobileNetwork.SIM.1.IMEI",
    "IMSI": "X_FH_MobileNetwork.SIM.1.IMSI",
    "NetworkMode": "X_FH_MobileNetwork.SIM.1.NetworkMode",
    "CarrierName": "X_FH_MobileNetwork.SIM.1.CarrierName",
    "RSRP": "X_FH_MobileNetwork.RadioSignalParameter.RSRP",
    "RSSI": "X_FH_MobileNetwork.RadioSignalParameter.RSSI",
    "SINR": "X_FH_MobileNetwork.RadioSignalParameter.SINR",
    "RSRQ": "X_FH_MobileNetwork.RadioSignalParameter.RSRQ",
    "BAND": "X_FH_MobileNetwork.RadioSignalParameter.BAND",
    "PCI": "X_FH_MobileNetwork.RadioSignalParameter.PCI",
    "SSB_RSRP": "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSRP",
    "TodayTotalTxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalTxBytes",
    "TodayTotalRxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalRxBytes",
    "MonthTxBytes": "X_FH_MobileNetwork.TrafficStats.MonthTxBytes",
    "MonthRxBytes": "X_FH_MobileNetwork.TrafficStats.MonthRxBytes",
}

VALIDATION_NODES = {
    "SerialNumber": "DeviceInfo.SerialNumber",
    "ModelName": "DeviceInfo.ModelName",
    "SoftwareVersion": "DeviceInfo.SoftwareVersion",
}
