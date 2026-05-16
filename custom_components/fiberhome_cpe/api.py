from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
import async_timeout
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


class FiberhomeCPEClient:
    """烽火 5G CPE fh_api 客户端。"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ):
        normalized_host = host.strip().rstrip("/")
        if normalized_host.startswith(("http://", "https://")):
            self.base_url = normalized_host
            self.host = normalized_host.split("://", maxsplit=1)[1]
        else:
            self.host = normalized_host
            self.base_url = f"http://{normalized_host}"
        self.username = username
        self.password = password
        self.session = session
        self.iv = bytes([i + 112 for i in range(16)])
        self._logged_in = False
        self.last_error: str | None = None

    def _encrypt(self, plaintext: str, session_id: str) -> str:
        """使用 sessionid 前 16 字节作为 AES key。"""
        key = session_id[:16].encode()
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv))
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return encrypted.hex()

    def _decrypt(self, ciphertext_hex: str, session_id: str) -> str:
        """解密 fh_api 响应。"""
        key = session_id[:16].encode()
        cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv))
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(bytes.fromhex(ciphertext_hex)) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
        return decrypted.decode("utf-8")

    async def _get_session_id(self) -> str:
        url = f"{self.base_url}/api/tmp/FHNCAPIS?ajaxmethod=get_refresh_sessionid"
        async with async_timeout.timeout(30):
            async with self.session.get(url) as resp:
                if resp.status in (401, 403):
                    self._logged_in = False
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                if isinstance(data, dict):
                    return str(data.get("sessionid", "") or "")
        return ""

    async def _request_get(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        async with async_timeout.timeout(30):
            async with self.session.get(url) as resp:
                if resp.status in (401, 403):
                    self._logged_in = False
                resp.raise_for_status()
                return (await resp.text()).strip()

    async def _request_post(self, data_obj: Any, path: str, ajax_method: str) -> str:
        session_id = await self._get_session_id()
        if not session_id:
            raise ValueError("Failed to get sessionid")

        body = {
            "dataObj": data_obj,
            "ajaxmethod": ajax_method,
            "sessionid": session_id,
        }
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        encrypted = self._encrypt(body_json, session_id)

        url = f"{self.base_url}{path}"
        async with async_timeout.timeout(30):
            async with self.session.post(
                url,
                data=encrypted,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status in (401, 403):
                    self._logged_in = False
                resp.raise_for_status()
                text = (await resp.text()).strip()
        if not text:
            return ""

        if ajax_method == "DO_WEB_LOGIN":
            return text

        try:
            return self._decrypt(text, session_id)
        except Exception:
            return text

    def _parse_login_result(self, raw: str) -> int | None:
        """兼容 JSON 和旧的管道分隔格式。"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict) and "result" in data:
            try:
                return int(data["result"])
            except (TypeError, ValueError):
                return None

        head = raw.split("|", maxsplit=1)[0].strip()
        if head.isdigit():
            return int(head)
        return None

    async def login(self) -> tuple[bool, str]:
        try:
            result = await self._request_post(
                {"username": self.username, "password": self.password},
                "/api/sign/DO_WEB_LOGIN",
                "DO_WEB_LOGIN",
            )
        except Exception as err:
            _LOGGER.error("Login failed: %s", err)
            self._logged_in = False
            self.last_error = str(err)
            return False, str(err)

        status = self._parse_login_result(result)
        messages = {
            0: "登录成功",
            1: "已有用户在其他地方登录",
            2: "连续错误登录次数达到3次，请1分钟后再试",
            3: "管理账号已被禁用",
            4: "用户名或密码错误",
        }
        self._logged_in = status == 0
        if status is None:
            self.last_error = f"解析登录响应失败: {result}"
            return False, self.last_error

        message = messages.get(status, f"未知状态: {status}")
        self.last_error = None if self._logged_in else message
        return self._logged_in, message

    async def logout(self) -> bool:
        try:
            await self._request_post(None, "/api/sign/DO_WEB_LOGOUT", "DO_WEB_LOGOUT")
        except Exception:
            return False
        self._logged_in = False
        return True

    async def is_logged_in(self) -> bool:
        try:
            return (await self._request_get("/api/tmp/IS_LOGGED_IN")).find("403") == -1
        except Exception:
            return False

    async def heartbeat(self) -> bool:
        try:
            result = await self._request_get("/api/tmp/heartbeat")
            return result in {"1", "true"}
        except Exception:
            return False

    async def ensure_login(self) -> bool:
        if self._logged_in:
            return True

        success, message = await self.login()
        if not success:
            _LOGGER.error("Login failed during ensure_login: %s", message)
        return success

    async def get_device_data(
        self, request_nodes: dict[str, str]
    ) -> dict[str, Any] | None:
        if not await self.ensure_login():
            return None

        try:
            result = await self._request_post(
                request_nodes,
                "/api/tmp/FHAPIS",
                "get_value_by_xmlnode",
            )
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                _LOGGER.debug("Session expired (403). Relogging in...")
                self._logged_in = False
                if await self.ensure_login():
                    try:
                        result = await self._request_post(
                            request_nodes,
                            "/api/tmp/FHAPIS",
                            "get_value_by_xmlnode",
                        )
                    except Exception as retry_err:
                        _LOGGER.error("Retry failed: %s", retry_err)
                        self.last_error = str(retry_err)
                        return None
                else:
                    return None
            else:
                _LOGGER.error("HTTP error fetching device data: %s", err)
                self.last_error = str(err)
                return None
        except Exception as err:
            _LOGGER.error("Failed to fetch device data: %s", err)
            self.last_error = str(err)
            return None

        try:
            data = json.loads(result) if result else None
            if data:
                self.last_error = None
            return data
        except Exception as err:
            _LOGGER.error("Failed to parse device data: %s", err)
            self.last_error = str(err)
            return None

    async def get_device_details(self) -> dict[str, Any]:
        return (
            await self.get_device_data(
                {
                    "Modem5GTemperature": "X_FH_MobileNetwork.Temperature.Modem5GTemperature",
                    "Modem4GTemperature": "X_FH_MobileNetwork.Temperature.Modem4GTemperature",
                    "SerialNumber": "DeviceInfo.SerialNumber",
                    "SoftwareVersion": "DeviceInfo.SoftwareVersion",
                    "HardwareVersion": "DeviceInfo.HardwareVersion",
                    "ModelName": "DeviceInfo.ModelName",
                    "CPUUsage": "DeviceInfo.ProcessStatus.CPUUsage",
                    "MemoryTotal": "DeviceInfo.MemoryStatus.Total",
                    "MemoryFree": "DeviceInfo.MemoryStatus.Free",
                    "UpTime": "DeviceInfo.UpTime",
                }
            )
            or {}
        )

    async def get_sim_info(self) -> dict[str, Any]:
        return (
            await self.get_device_data(
                {
                    "SIMStatus": "X_FH_MobileNetwork.SIM.1.SIMStatus",
                    "IMEI": "X_FH_MobileNetwork.SIM.1.IMEI",
                    "IMSI": "X_FH_MobileNetwork.SIM.1.IMSI",
                    "NetworkMode": "X_FH_MobileNetwork.SIM.1.NetworkMode",
                    "CarrierName": "X_FH_MobileNetwork.SIM.1.CarrierName",
                }
            )
            or {}
        )

    async def get_signal_info(self) -> dict[str, Any]:
        return (
            await self.get_device_data(
                {
                    "RSRP": "X_FH_MobileNetwork.RadioSignalParameter.RSRP",
                    "RSSI": "X_FH_MobileNetwork.RadioSignalParameter.RSSI",
                    "SINR": "X_FH_MobileNetwork.RadioSignalParameter.SINR",
                    "RSRQ": "X_FH_MobileNetwork.RadioSignalParameter.RSRQ",
                    "BAND": "X_FH_MobileNetwork.RadioSignalParameter.BAND",
                    "PCI": "X_FH_MobileNetwork.RadioSignalParameter.PCI",
                    "SSB_RSRP": "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSRP",
                }
            )
            or {}
        )

    async def get_traffic_stats(self) -> dict[str, Any]:
        return (
            await self.get_device_data(
                {
                    "TodayTotalTxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalTxBytes",
                    "TodayTotalRxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalRxBytes",
                    "MonthTxBytes": "X_FH_MobileNetwork.TrafficStats.MonthTxBytes",
                    "MonthRxBytes": "X_FH_MobileNetwork.TrafficStats.MonthRxBytes",
                }
            )
            or {}
        )

    async def get_new_sms_flag(self) -> bool:
        if not await self.ensure_login():
            return False

        try:
            result = await self._request_get("/api/tmp/FHAPIS?ajaxmethod=get_header_info")
            data = json.loads(result)
            return str(data.get("new_sms_flag", "false")).lower() == "true"
        except Exception as err:
            _LOGGER.debug("get_new_sms_flag failed: %s", err)
            self.last_error = str(err)
            return False

    async def get_unread_sms(self) -> list[dict[str, str]]:
        if not await self.ensure_login():
            return []

        try:
            result = await self._request_post(None, "/api/tmp/FHAPIS", "get_sms_data")
            data = json.loads(result) if result else {}
        except Exception as err:
            _LOGGER.error("Failed to get unread SMS: %s", err)
            self.last_error = str(err)
            return []

        sms_list: list[dict[str, str]] = []
        for _, session_data in data.items():
            if not isinstance(session_data, dict):
                continue

            phone = session_data.get("session_phone", "")
            for _, msg_data in session_data.items():
                if not isinstance(msg_data, dict):
                    continue
                if "msg_content" not in msg_data:
                    continue
                if msg_data.get("rcvorsend") != "recv" or msg_data.get("isOpened") != "0":
                    continue

                sms_list.append(
                    {
                        "id": msg_data.get("childnode", ""),
                        "phone": phone,
                        "content": msg_data.get("msg_content", ""),
                        "time": msg_data.get("time", ""),
                    }
                )

        return sms_list

    async def mark_sms_read(self, sms_id: str) -> bool:
        if not await self.ensure_login():
            return False

        try:
            data = {
                "url": {
                    f"smsIsopend{sms_id}": (
                        "InternetGatewayDevice.X_FH_MobileNetwork."
                        f"SMS_Recv.SMS_RecvMsg.{sms_id}.isOpened"
                    )
                },
                "value": {f"smsIsopend{sms_id}": "1"},
            }
            await self._request_post(data, "/api/tmp/FHAPIS", "set_value_by_xmlnode")
            return True
        except Exception as err:
            _LOGGER.error("Failed to mark SMS as read: %s", err)
            self.last_error = str(err)
            return False

    async def async_close(self) -> None:
        await self.logout()
        self._logged_in = False

    def update_credentials(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._logged_in = False

    def update_host(self, host: str) -> None:
        normalized_host = host.strip().rstrip("/")
        if normalized_host.startswith(("http://", "https://")):
            self.base_url = normalized_host
            self.host = normalized_host.split("://", maxsplit=1)[1]
        else:
            self.host = normalized_host
            self.base_url = f"http://{normalized_host}"
        self._logged_in = False
