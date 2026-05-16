# FiberHome-CPE-HA

[English version](README_en.md)

`FiberHome-CPE-HA` 是一个用于 Home Assistant 的自定义集成，用来接入烽火 5G CPE 设备，并把设备状态、网络信号、流量统计以及最新短信同步为 Home Assistant 传感器。

## 功能特性

- 自动登录 CPE 并获取设备基础信息
- 暴露温度、CPU、内存、运行时间等系统状态传感器
- 暴露 RSRP、RSSI、SINR、RSRQ、BAND、PCI 等信号传感器
- 暴露今日和本月上传下载流量传感器
- 可选启用 `Latest Message` 传感器
- 发现新短信后读取最新短信内容并自动标记为已读

## 配置项

在 Home Assistant 添加集成时，需要填写以下内容：

- 用户名
- 密码
- 刷新间隔
- 是否启用 `Latest Message`

其中刷新间隔默认 `60` 秒，可配置范围为 `1` 到 `21600` 秒。

## 安装方式

### 通过 HACS 安装（推荐）

1. 在 Home Assistant 中打开 `HACS`
2. 点击右上角的菜单并选择 `Custom repositories`
3. 添加仓库地址：`https://github.com/neon9809/FiberHome-CPE-HA`
4. 选择类别：`integration`
5. 添加后进入 `HACS -> Integrations`
6. 搜索 `Fiberhome CPE` 并安装

### 手动安装

1. 将 `custom_components/fiberhome_cpe` 目录复制到 Home Assistant 配置目录下的 `custom_components` 目录中
2. 最终路径应为 `config/custom_components/fiberhome_cpe/`
3. 重启 Home Assistant
4. 进入“设置 -> 设备与服务 -> 添加集成”
5. 搜索 `Fiberhome CPE`

## 数据来源

本项目参考了仓库中的 `obtainData.py`，使用相同的会话获取、AES 加解密和接口请求方式访问 CPE。

短信读取逻辑参考：

- [fiberhome-cpe-sms](https://gitee.com/upchr/fiberhome-cpe-sms)
- [fiberhome-cpe](https://github.com/kukume/fiberhome-cpe)

## Credit

- 项目主页: [neon9809](https://github.com/neon9809)
- 提示词目标总结:
  - 参考 `obtainData.py` 的方法开发一个 Home Assistant 自定义插件
  - 配置后自动从 CPE 获取数据并写入 Home Assistant 传感器
  - 设计一个 `Latest Message` 传感器，读取最新一条短信
  - 传感器内容需要包含发件人和短信内容
  - 获取后自动将该短信标记为已读
  - `config_flow` 中支持用户名、密码、刷新间隔和是否启用短信传感器
  - 刷新间隔默认 `60` 秒，允许范围 `1` 到 `21600` 秒

我自豪地声明：本项目由 Trae Agent 与 Gemini 3.1 Pro 模型完成。
