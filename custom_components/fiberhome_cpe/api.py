from __future__ import annotations

import json
import logging
from typing import Any

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


class FiberhomeCPEClient:
    """烽火 5G CPE fh_api 客户端。"""

    def __init__(self, host: str, username: str, password: str):
        normalized_host = host.strip().rstrip("/")
        if normalized_host.startswith(("http://", "https://")):
            self.base_url = normalized_host
            self.host = normalized_host.split("://", maxsplit=1)[1]
        else:
            self.host = normalized_host
            self.base_url = f"http://{normalized_host}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
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

    def _get_session_id(self) -> str:
        """获取 api sessionid。"""
        resp = self.session.get(
            f"{self.base_url}/api/tmp/FHNCAPIS?ajaxmethod=get_refresh_sessionid",
            timeout=30,
        )
        if resp.status_code in (401, 403):
            self._logged_in = False
        resp.raise_for_status()
        return resp.json().get("sessionid", "")

    def _request_get(self, path: str) -> str:
        """发送 GET 请求。"""
        resp = self.session.get(f"{self.base_url}{path}", timeout=30)
        if resp.status_code in (401, 403):
            self._logged_in = False
        resp.raise_for_status()
        return resp.text.strip()

    def _request_post(self, data_obj: Any, path: str, ajax_method: str) -> str:
        """发送 fh_api 加密 POST 请求。"""
        session_id = self._get_session_id()
        if not session_id:
            raise ValueError("Failed to get sessionid")

        body = {
            "dataObj": data_obj,
            "ajaxmethod": ajax_method,
            "sessionid": session_id,
        }
        body_json = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        encrypted = self._encrypt(body_json, session_id)

        resp = self.session.post(
            f"{self.base_url}{path}",
            data=encrypted,
            timeout=30,
        )
        if resp.status_code in (401, 403):
            self._logged_in = False
        resp.raise_for_status()

        text = resp.text.strip()
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

    def login(self) -> tuple[bool, str]:
        """登录 CPE。"""
        try:
            result = self._request_post(
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

    def logout(self) -> bool:
        """登出当前会话。"""
        try:
            self._request_post(None, "/api/sign/DO_WEB_LOGOUT", "DO_WEB_LOGOUT")
        except Exception:
            return False
        self._logged_in = False
        return True

    def is_logged_in(self) -> bool:
        """检查会话是否仍有效。"""
        try:
            return self._request_get("/api/tmp/IS_LOGGED_IN").find("403") == -1
        except Exception:
            return False

    def heartbeat(self) -> bool:
        """发送心跳。"""
        try:
            result = self._request_get("/api/tmp/heartbeat")
            return result in {"1", "true"}
        except Exception:
            return False

    def ensure_login(self) -> bool:
        """必要时重新登录。"""
        if self._logged_in:
            return True

        success, message = self.login()
        if not success:
            _LOGGER.error("Login failed during ensure_login: %s", message)
        return success

    def get_device_data(self, request_nodes: dict[str, str]) -> dict[str, Any] | None:
        """读取一组设备 XML 节点。"""
        if not self.ensure_login():
            return None

        try:
            result = self._request_post(
                request_nodes,
                "/api/tmp/FHAPIS",
                "get_value_by_xmlnode",
            )
        except requests.exceptions.HTTPError as err:
            if err.response.status_code in (401, 403):
                _LOGGER.debug("Session expired (403). Relogging in...")
                self._logged_in = False
                if self.ensure_login():
                    try:
                        result = self._request_post(
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

    def get_device_details(self) -> dict[str, Any]:
        """获取设备基础与系统信息。"""
        return self.get_device_data(
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
        ) or {}

    def get_sim_info(self) -> dict[str, Any]:
        """获取 SIM 卡信息。"""
        return self.get_device_data(
            {
                "SIMStatus": "X_FH_MobileNetwork.SIM.1.SIMStatus",
                "IMEI": "X_FH_MobileNetwork.SIM.1.IMEI",
                "IMSI": "X_FH_MobileNetwork.SIM.1.IMSI",
                "NetworkMode": "X_FH_MobileNetwork.SIM.1.NetworkMode",
                "CarrierName": "X_FH_MobileNetwork.SIM.1.CarrierName",
            }
        ) or {}

    def get_signal_info(self) -> dict[str, Any]:
        """获取信号信息。"""
        return self.get_device_data(
            {
                "RSRP": "X_FH_MobileNetwork.RadioSignalParameter.RSRP",
                "RSSI": "X_FH_MobileNetwork.RadioSignalParameter.RSSI",
                "SINR": "X_FH_MobileNetwork.RadioSignalParameter.SINR",
                "RSRQ": "X_FH_MobileNetwork.RadioSignalParameter.RSRQ",
                "BAND": "X_FH_MobileNetwork.RadioSignalParameter.BAND",
                "PCI": "X_FH_MobileNetwork.RadioSignalParameter.PCI",
                "SSB_RSRP": "X_FH_MobileNetwork.RadioSignalParameter.SSB_RSRP",
            }
        ) or {}

    def get_traffic_stats(self) -> dict[str, Any]:
        """获取流量统计。"""
        return self.get_device_data(
            {
                "TodayTotalTxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalTxBytes",
                "TodayTotalRxBytes": "X_FH_MobileNetwork.TrafficStats.TodayTotalRxBytes",
                "MonthTxBytes": "X_FH_MobileNetwork.TrafficStats.MonthTxBytes",
                "MonthRxBytes": "X_FH_MobileNetwork.TrafficStats.MonthRxBytes",
            }
        ) or {}

    def get_new_sms_flag(self) -> bool:
        """检查是否有新短信。"""
        if not self.ensure_login():
            return False

        try:
            result = self._request_get("/api/tmp/FHAPIS?ajaxmethod=get_header_info")
            data = json.loads(result)
            return str(data.get("new_sms_flag", "false")).lower() == "true"
        except Exception as err:
            _LOGGER.debug("get_new_sms_flag failed: %s", err)
            self.last_error = str(err)
            return False

    def get_unread_sms(self) -> list[dict[str, str]]:
        """获取未读收件短信。"""
        if not self.ensure_login():
            return []

        try:
            result = self._request_post(None, "/api/tmp/FHAPIS", "get_sms_data")
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

    def mark_sms_read(self, sms_id: str) -> bool:
        """标记短信已读。"""
        if not self.ensure_login():
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
            self._request_post(data, "/api/tmp/FHAPIS", "set_value_by_xmlnode")
            return True
        except Exception as err:
            _LOGGER.error("Failed to mark SMS as read: %s", err)
            self.last_error = str(err)
            return False

    def close(self):
        """登出并关闭底层会话。"""
        self.logout()
        self.session.close()
