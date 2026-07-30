"""Python-version-independent adapter for the reconstructed GigaBlue BT core."""

from __future__ import absolute_import, print_function

import ctypes
import os
import socket
import time


BT_STATUS_DISABLED = 0
BT_STATUS_ENABLED = 1

BT_PROFILE_GB_RC = 1
BT_PROFILE_HID_UNKNOWN = 2
BT_PROFILE_KEYBOARD = 3
BT_PROFILE_MOUSE = 4
BT_PROFILE_HEADPHONE = 6
BT_PROFILE_SPEAKER = 7
BT_PROFILE_GATT_UNKNOWN = 8
BT_PROFILE_GATT_HID = 9

BT_EVENT_DEVICE_ADDED = 0
BT_EVENT_SCAN_END = 1
BT_EVENT_CONNECTED = 2
BT_EVENT_DISCONNECTED = 3
BT_EVENT_PAIRING_SUCCESS = 4
BT_EVENT_PAIRING_FAIL = 5
BT_EVENT_PAIRING_TIMEOUT = 6
BT_EVENT_PAIRING_WRONG_PIN = 7
BT_EVENT_PAIRING_PASSCODE_REQUIRED = 8
BT_EVENT_CONNECT_TIMEOUT = 9
BT_EVENT_REQUEST_AUDIO_CONNECT = 10
BT_EVENT_READ_BATTERY_LEVEL = 11
BT_EVENT_LINK_DOWN = 12
BT_EVENT_NEW_VOICE = 13
BT_EVENT_BT_CONNECTED = 14
BT_EVENT_BT_DISCONNECTED = 15
BT_EVENT_BT_VOICE_START = 16
BT_EVENT_BT_VOICE_STOP = 17
BT_EVENT_BT_NO_VOICE = 18
BT_EVENT_CHECK_STATUS_END = 19

BT_REQUEST_NONE = 0
BT_REQUEST_STARTSCAN = 1
BT_REQUEST_ABORTSCAN = 2
BT_REQUEST_RESETSCAN = 3
BT_REQUEST_PAIRING = 4
BT_REQUEST_CANCELPAIRING = 5
BT_REQUEST_REMOVEPAIRING = 6
BT_REQUEST_CONNECT = 7
BT_REQUEST_DISCONNECT = 8

_GBBT_ABI_VERSION = 1
_GBBT_MAX_DEVICES = 64
_GBBT_SERVICE_SOCKET = "/var/run/gbbt/gbbt.sock"


class _Device(ctypes.Structure):
	_fields_ = [
		("bd_addr", ctypes.c_char * 18),
		("name", ctypes.c_char * 249),
		("profile", ctypes.c_int32),
		("connected", ctypes.c_int32),
		("class_of_device", ctypes.c_char * 16),
		("rssi", ctypes.c_int32),
		("service_mask", ctypes.c_uint32),
	]


class _Event(ctypes.Structure):
	_fields_ = [
		("type", ctypes.c_int32),
		("is_ble", ctypes.c_int32),
		("reason", ctypes.c_int32),
		("rssi", ctypes.c_int32),
		("value", ctypes.c_int32),
		("device", _Device),
		("text", ctypes.c_char * 256),
	]


def _decode(value):
	return bytes(value).split(b"\0", 1)[0].decode("utf-8", "replace")


def _encode(value):
	if value is None:
		return None
	if isinstance(value, bytes):
		return value
	return str(value).encode("utf-8")


def _decode_service_field(value):
	result = []
	index = 0
	while index < len(value):
		if value[index] == "%" and index + 2 < len(value):
			try:
				result.append(chr(int(value[index + 1:index + 3], 16)))
				index += 3
				continue
			except ValueError:
				pass
		result.append(value[index])
		index += 1
	return "".join(result)


def _library_candidates():
	override = os.environ.get("GBBT_CORE_LIBRARY")
	if override:
		yield override

	package_dir = os.path.dirname(os.path.abspath(__file__))
	yield os.path.join(package_dir, "libgbbtcore.so")
	yield "/usr/lib/libgbbtcore.so.1"
	yield "/usr/lib/libgbbtcore.so"
	yield "/usr/local/lib/libgbbtcore.so.1"
	yield "/usr/local/lib/libgbbtcore.so"


def _load_library():
	errors = []
	for candidate in _library_candidates():
		if not os.path.exists(candidate):
			continue
		try:
			return ctypes.CDLL(candidate, mode=ctypes.RTLD_GLOBAL)
		except OSError as error:
			errors.append("%s: %s" % (candidate, error))

	detail = "; ".join(errors) if errors else "no candidate exists"
	raise ImportError("Unable to load libgbbtcore.so (%s)" % detail)


def _configure_library(library):
	library.gbbt_abi_version.argtypes = []
	library.gbbt_abi_version.restype = ctypes.c_uint32
	library.gbbt_version.argtypes = []
	library.gbbt_version.restype = ctypes.c_char_p
	library.gbbt_last_error.argtypes = []
	library.gbbt_last_error.restype = ctypes.c_char_p

	library.gbbt_init.argtypes = [ctypes.c_char_p]
	library.gbbt_init.restype = ctypes.c_int
	library.gbbt_deinit.argtypes = []
	library.gbbt_deinit.restype = ctypes.c_int
	library.gbbt_enable.argtypes = []
	library.gbbt_enable.restype = ctypes.c_int
	library.gbbt_disable.argtypes = []
	library.gbbt_disable.restype = ctypes.c_int
	library.gbbt_get_status.argtypes = []
	library.gbbt_get_status.restype = ctypes.c_int
	library.gbbt_check_btusb.argtypes = []
	library.gbbt_check_btusb.restype = ctypes.c_int

	library.gbbt_start_scan.argtypes = [ctypes.c_int]
	library.gbbt_start_scan.restype = ctypes.c_int
	library.gbbt_abort_scan.argtypes = []
	library.gbbt_abort_scan.restype = ctypes.c_int
	library.gbbt_reset_scan.argtypes = []
	library.gbbt_reset_scan.restype = ctypes.c_int
	library.gbbt_get_discovered.argtypes = [ctypes.POINTER(_Device), ctypes.c_size_t]
	library.gbbt_get_discovered.restype = ctypes.c_int
	library.gbbt_get_paired.argtypes = [ctypes.POINTER(_Device), ctypes.c_size_t]
	library.gbbt_get_paired.restype = ctypes.c_int

	for name in (
		"gbbt_pair",
		"gbbt_cancel_pairing",
		"gbbt_connect",
		"gbbt_disconnect",
		"gbbt_remove_pairing",
		"gbbt_audio_start",
	):
		function = getattr(library, name)
		function.argtypes = [ctypes.c_char_p]
		function.restype = ctypes.c_int

	library.gbbt_send_pincode.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
	library.gbbt_send_pincode.restype = ctypes.c_int
	library.gbbt_set_discoverable.argtypes = [ctypes.c_int]
	library.gbbt_set_discoverable.restype = ctypes.c_int
	library.gbbt_read_battery_level.argtypes = []
	library.gbbt_read_battery_level.restype = ctypes.c_int
	library.gbbt_check_status.argtypes = []
	library.gbbt_check_status.restype = ctypes.c_int
	library.gbbt_is_max_ble_paired_device.argtypes = []
	library.gbbt_is_max_ble_paired_device.restype = ctypes.c_int
	library.gbbt_audio_stop.argtypes = []
	library.gbbt_audio_stop.restype = ctypes.c_int
	library.gbbt_set_volume.argtypes = [ctypes.c_int]
	library.gbbt_set_volume.restype = ctypes.c_int
	library.gbbt_poll_event.argtypes = [ctypes.POINTER(_Event)]
	library.gbbt_poll_event.restype = ctypes.c_int


def _device_data(device, paired=False):
	data = {
		"bd_addr": _decode(device.bd_addr),
		"name": _decode(device.name),
		"profile": int(device.profile),
		"classOfDevice": _decode(device.class_of_device),
		"serviceMask": int(device.service_mask),
	}
	if paired:
		data["isConnected"] = int(device.connected)
	else:
		data["connected"] = int(device.connected)
	return data


class Gb_PyBluetooth:
	"""Compatibility class matching the public API of the former SWIG module."""

	def __init__(self):
		service_socket = os.environ.get("GBBT_SERVICE_SOCKET", _GBBT_SERVICE_SOCKET)
		self._service_socket = service_socket if os.path.exists(service_socket) else None
		self._service_unavailable = False
		self._service_retry_after = 0.0
		self._library = None
		if self._service_socket:
			info = self._service_call("INFO")
			if not info or not info[0].startswith("INFO|"):
				raise ImportError("Unable to query gbbt-service")
			info_fields = info[0].split("|", 2)
			abi_version = int(info_fields[1])
		else:
			self._library = _load_library()
			_configure_library(self._library)
			abi_version = int(self._library.gbbt_abi_version())
		if abi_version != _GBBT_ABI_VERSION:
			raise ImportError(
				"Unsupported libgbbtcore ABI %d (expected %d)"
				% (abi_version, _GBBT_ABI_VERSION)
			)

		self.bt_status = BT_STATUS_DISABLED
		self.event_callback_ = None
		self.ble_event_callback_ = None
		self.ota_event_callback_ = None
		self.scan_time = 30
		self.voice_check_db = -33
		self._event_timer = None
		self._connected_addresses = set()
		if self._service_socket:
			self._service_bool("INIT /home/root")
		else:
			self._library.gbbt_init(_encode("/home/root"))
		self._btusb_present = self.checkBTUSB()
		self._create_event_timer()

	def _service_call(self, command, timeout=30.0):
		if not self._service_socket:
			return []
		if self._service_unavailable and time.monotonic() < self._service_retry_after:
			raise OSError("gbbt-service is temporarily unavailable")
		connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		connection.settimeout(timeout)
		try:
			connection.connect(self._service_socket)
			connection.sendall((command + "\n").encode("utf-8"))
			connection.shutdown(socket.SHUT_WR)
			chunks = []
			while True:
				chunk = connection.recv(4096)
				if not chunk:
					break
				chunks.append(chunk)
		except OSError as error:
			if not self._service_unavailable:
				print("[GBBT] service unavailable during %s: %s" % (command, error))
			self._service_unavailable = True
			self._service_retry_after = time.monotonic() + 2.0
			raise
		finally:
			connection.close()
		if self._service_unavailable:
			print("[GBBT] service connection restored")
		self._service_unavailable = False
		self._service_retry_after = 0.0
		return b"".join(chunks).decode("utf-8", "replace").splitlines()

	def _service_bool(self, command):
		try:
			lines = self._service_call(command)
		except OSError:
			return False
		return bool(lines and lines[0].split("|", 2)[:2] == ["OK", "1"])

	def _service_value(self, command, default=0):
		try:
			lines = self._service_call(command)
			if lines and lines[0].startswith("VALUE|"):
				return int(lines[0].split("|", 1)[1])
		except (OSError, ValueError):
			pass
		return default

	def _create_event_timer(self):
		try:
			from enigma import eTimer

			self._event_timer = eTimer()
			self._event_timer.callback.append(self.pollEvents)
			self._event_timer.start(100, False)
		except (ImportError, AttributeError):
			# Standalone tests call pollEvents() explicitly.
			self._event_timer = None

	def _last_error(self):
		if self._service_socket:
			try:
				lines = self._service_call("LAST_ERROR")
				if lines and lines[0].startswith("TEXT|"):
					return _decode_service_field(lines[0].split("|", 1)[1])
			except OSError:
				pass
			return ""
		value = self._library.gbbt_last_error()
		return value.decode("utf-8", "replace") if value else ""

	def _call_address(self, function_name, bd_addr):
		if self._service_socket:
			commands = {
				"gbbt_pair": "PAIR",
				"gbbt_cancel_pairing": "CANCEL_PAIRING",
				"gbbt_connect": "CONNECT",
				"gbbt_disconnect": "DISCONNECT",
				"gbbt_remove_pairing": "REMOVE_PAIRING",
				"gbbt_audio_start": "AUDIO_START",
			}
			return self._service_bool("%s %s" % (commands[function_name], bd_addr))
		return bool(getattr(self._library, function_name)(_encode(bd_addr)))

	def _read_devices(self, function_name, paired):
		if self._service_socket:
			command = "GET_PAIRED" if paired else "GET_DISCOVERED"
			try:
				lines = self._service_call(command)
			except OSError:
				return {}
			result = {}
			for line in lines:
				if not line.startswith("DEVICE|"):
					continue
				fields = line.split("|")
				if len(fields) < 8:
					continue
				device = {
					"bd_addr": _decode_service_field(fields[1]),
					"name": _decode_service_field(fields[2]),
					"profile": int(fields[3]),
					"classOfDevice": _decode_service_field(fields[5]),
					"serviceMask": int(fields[7]),
				}
				device["isConnected" if paired else "connected"] = int(fields[4])
				result[str(len(result))] = device
			return result
		devices = (_Device * _GBBT_MAX_DEVICES)()
		count = int(
			getattr(self._library, function_name)(devices, _GBBT_MAX_DEVICES)
		)
		if count <= 0:
			return {}
		return {
			str(index): _device_data(devices[index], paired=paired)
			for index in range(count)
		}

	def _event_data(self, event):
		data = _device_data(event.device)
		data["isConnected"] = int(event.device.connected)
		data["reason"] = int(event.reason)
		data["rssi"] = int(event.rssi)
		data["value"] = int(event.value)
		text = _decode(event.text)
		if text:
			data["text"] = text
		return data

	def _poll_hotplug(self):
		present = self.checkBTUSB()
		if present == self._btusb_present:
			return

		self._btusb_present = present
		if self.event_callback_ is not None:
			event_type = BT_EVENT_BT_CONNECTED if present else BT_EVENT_BT_DISCONNECTED
			try:
				self.event_callback_(
					event_type,
					{
						"bd_addr": "",
						"name": "",
						"profile": 0,
						"classOfDevice": "",
						"connected": int(present),
						"isConnected": int(present),
						"reason": 0,
						"rssi": 0,
						"value": 0,
					},
				)
			except Exception as error:
				print("[GBBT] hotplug callback failed: %s" % error)

	def pollEvents(self):
		if (
			self._service_socket
			and self._service_unavailable
			and time.monotonic() < self._service_retry_after
		):
			return
		self._poll_hotplug()
		if self._service_socket:
			self._poll_service_events()
			return
		for unused in range(128):
			event = _Event()
			if not self._library.gbbt_poll_event(ctypes.byref(event)):
				break

			event_type = int(event.type)
			event_data = self._event_data(event)
			address = event_data.get("bd_addr", "").lower()
			if address:
				if event_type == BT_EVENT_CONNECTED:
					self._connected_addresses.add(address)
				elif event_type == BT_EVENT_DISCONNECTED:
					self._connected_addresses.discard(address)

			callback = self.ble_event_callback_ if event.is_ble else self.event_callback_
			if callback is None:
				continue
			try:
				callback(event_type, event_data)
			except Exception as error:
				print("[GBBT] event callback failed: %s" % error)

	def _poll_service_events(self):
		for unused in range(128):
			try:
				lines = self._service_call("POLL_EVENT", timeout=2.0)
			except OSError:
				return
			if not lines or lines[0] == "NONE":
				return
			fields = lines[0].split("|")
			if len(fields) < 14 or fields[0] != "EVENT":
				return

			event_type = int(fields[1])
			is_ble = int(fields[2])
			event_data = {
				"bd_addr": _decode_service_field(fields[6]),
				"name": _decode_service_field(fields[7]),
				"profile": int(fields[8]),
				"connected": int(fields[9]),
				"isConnected": int(fields[9]),
				"classOfDevice": _decode_service_field(fields[10]),
				"serviceMask": int(fields[12]),
				"reason": int(fields[3]),
				"rssi": int(fields[4]),
				"value": int(fields[5]),
			}
			text = _decode_service_field(fields[13])
			if text:
				event_data["text"] = text

			address = event_data["bd_addr"].lower()
			if address:
				if event_type == BT_EVENT_CONNECTED:
					self._connected_addresses.add(address)
				elif event_type == BT_EVENT_DISCONNECTED:
					self._connected_addresses.discard(address)

			callback = self.ble_event_callback_ if is_ble else self.event_callback_
			if callback is not None:
				try:
					callback(event_type, event_data)
				except Exception as error:
					print("[GBBT] event callback failed: %s" % error)

	def init(self):
		if self._service_socket:
			return self._service_bool("INIT /home/root")
		return bool(self._library.gbbt_init(_encode("/home/root")))

	def deinit(self):
		self.bt_status = BT_STATUS_DISABLED
		if self._service_socket:
			return True
		return bool(self._library.gbbt_deinit())

	def enable(self):
		result = self._service_bool("ENABLE") if self._service_socket else bool(self._library.gbbt_enable())
		self.bt_status = BT_STATUS_ENABLED if result else BT_STATUS_DISABLED
		if not result:
			print("[GBBT] enable failed: %s" % self._last_error())
		return result

	def disable(self):
		result = self._service_bool("DISABLE") if self._service_socket else bool(self._library.gbbt_disable())
		self.bt_status = BT_STATUS_DISABLED
		return result

	def checkBTUSB(self):
		if self._service_socket:
			present = self._service_value("CHECK_BTUSB", default=None)
			if present is None:
				# A dead control service is not a USB hotplug event.
				return os.path.exists("/dev/btusb0")
			return bool(present)
		return bool(self._library.gbbt_check_btusb())

	def getStatus(self):
		if self._service_socket:
			self.bt_status = self._service_value("STATUS")
		else:
			self.bt_status = int(self._library.gbbt_get_status())
		return self.bt_status

	def startScan(self, scan_flag=False, isBle=False):
		del scan_flag
		if self._service_socket:
			return self._service_bool("SCAN %d" % int(bool(isBle)))
		return bool(self._library.gbbt_start_scan(bool(isBle)))

	def StartScanTestMode(self):
		return self.startScan(False, False)

	def abortScan(self):
		if self._service_socket:
			return self._service_bool("ABORT_SCAN")
		return bool(self._library.gbbt_abort_scan())

	def resetScan(self):
		if self._service_socket:
			return self._service_bool("RESET_SCAN")
		return bool(self._library.gbbt_reset_scan())

	def addEventCallback(self, callback):
		self.event_callback_ = callback
		return True

	def removeEventCallback(self):
		self.event_callback_ = None
		return True

	def addBleEventCallback(self, callback):
		self.ble_event_callback_ = callback
		return True

	def removeBleEventCallback(self):
		self.ble_event_callback_ = None
		return True

	def getSystemInfo(self):
		if self._service_socket:
			lines = self._service_call("INFO")
			fields = lines[0].split("|", 2)
			return {
				"abi": int(fields[1]),
				"version": _decode_service_field(fields[2]),
			}
		return {
			"abi": int(self._library.gbbt_abi_version()),
			"version": _decode(self._library.gbbt_version()),
		}

	def getDiscDevice(self):
		return self._read_devices("gbbt_get_discovered", paired=False)

	def getPairedDevice(self):
		devices = self._read_devices("gbbt_get_paired", paired=True)
		for device in devices.values():
			if device.get("bd_addr", "").lower() in self._connected_addresses:
				device["isConnected"] = 1
		return devices

	def requestPairing(self, mac):
		return self._call_address("gbbt_pair", mac)

	def cancelPairing(self, mac):
		return self._call_address("gbbt_cancel_pairing", mac)

	def removePairing(self, mac):
		return self._call_address("gbbt_remove_pairing", mac)

	def removePairedList(self, mac):
		return self.removePairing(mac)

	def requestSendPincode(self, mac, pincode):
		if self._service_socket:
			return self._service_bool("SEND_PIN %s %s" % (mac, pincode))
		return bool(self._library.gbbt_send_pincode(_encode(mac), _encode(pincode)))

	def requestConnect(self, mac):
		return self._call_address("gbbt_connect", mac)

	def requestDisconnect(self, mac):
		return self._call_address("gbbt_disconnect", mac)

	def requestBLEConnect(self, mac):
		return self.requestConnect(mac)

	def requestBLEDisconnect(self, mac):
		return self.requestDisconnect(mac)

	def setDisCoverable(self, value):
		if self._service_socket:
			return self._service_bool("DISCOVERABLE %d" % int(bool(value)))
		return bool(self._library.gbbt_set_discoverable(bool(value)))

	def playAudioDevice(self, mac):
		return self._call_address("gbbt_audio_start", mac)

	def stopAudioDevice(self):
		if self._service_socket:
			return self._service_bool("AUDIO_STOP")
		return bool(self._library.gbbt_audio_stop())

	def setScanTime(self, duration):
		duration = int(duration)
		if 0 < duration <= 60:
			self.scan_time = duration
			return True
		return False

	def setVolume(self, volume):
		if self._service_socket:
			return self._service_bool("VOLUME %d" % int(volume))
		return bool(self._library.gbbt_set_volume(int(volume)))

	def resetSearchedDevices(self):
		return self.resetScan()

	def setVoiceCheckDB(self, value):
		self.voice_check_db = int(value)
		return True

	def isVoiceRecording(self):
		return False

	def cleanupBleClient(self):
		return True

	def readBatteryLevel(self):
		if self._service_socket:
			return self._service_bool("BATTERY")
		return bool(self._library.gbbt_read_battery_level())

	def updateBatteryLevel(self):
		return self.readBatteryLevel()

	def OTA_addEventCallback(self, callback):
		self.ota_event_callback_ = callback
		return True

	def OTA_removeEventCallback(self):
		self.ota_event_callback_ = None
		return True

	def OTAInit(self):
		return False

	def OTADeInit(self):
		return True

	def OTAStart(self):
		return False

	def OTAStop(self):
		return True

	def OTACheckFWVersion(self, mac=None, firmware_path=None):
		del mac, firmware_path
		return False

	def CheckStatus(self):
		if self._service_socket:
			return self._service_value("CHECK_STATUS")
		return int(self._library.gbbt_check_status())

	def isMaxBLEPairedDevice(self):
		if self._service_socket:
			return bool(self._service_value("MAX_BLE"))
		return bool(self._library.gbbt_is_max_ble_paired_device())
