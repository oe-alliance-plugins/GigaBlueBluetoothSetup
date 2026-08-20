from __future__ import print_function
from __future__ import absolute_import

from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox

from Components.config import config, ConfigSelection, ConfigSubsection, ConfigYesNo, ConfigText, ConfigSelectionNumber, ConfigNumber

from Tools.Notifications import AddNotification, AddNotificationWithCallback, AddPopup

from enigma import addInputDevice, removeInputDevice, eTimer, eServiceReference
from enigma import eDVBVolumecontrol

from glob import glob
import fcntl
import os
import struct
import time
from . import gbbt
from .bt_types import isAudioProfile
from . import bt_types
from .bt_task import BluetoothTask

from .OTAUpdate import GbRcuOtaUpdate

BT_AUDIO_DELAY_PROC = "/proc/stb/audio/btaudio_delay_pcm"
BT_AUDIO_ONOFF_PROC = "/proc/stb/audio/btaudio"

# Linux 4.1 accepts the legacy input_keymap_entry layout through this ioctl:
# two native unsigned integers containing HID scancode and Linux keycode.
EVIOCSKEYCODE = 0x40084504

# Per-device HID keymaps.  Do not make these mappings global: GigaBlue has
# several BLE remote generations and other keyboards, mice and remotes must
# keep the kernel's standard HID mapping.
BT_HID_KEYMAPS = {
	("0508", "0110", "0000"): (
		(0x000C0030, 116),  # POWER -> KEY_POWER
		(0x000C0232, 377),  # TV/RADIO -> KEY_TV
		(0x000C0131, 361),  # HISTORY -> KEY_ARCHIVE
		(0x000C0067, 375),  # PIP -> KEY_SCREEN
		(0x000C0061, 370),  # SUBT -> KEY_SUBTITLE
		(0x000C00E2, 113),  # MUTE -> KEY_MUTE
		(0x000C0233, 388),  # TEXT -> KEY_TEXT
		(0x000C0122, 395),  # PLAYLIST -> KEY_LIST
		(0x000C0086, 128),  # STOP -> KEY_STOP
		(0x000C0258, 362),  # TIMER -> KEY_PROGRAM
		(0x000C00B4, 168),  # REWIND -> KEY_REWIND
		(0x000C00B3, 208),  # FAST FORWARD -> KEY_FASTFORWARD
		(0x000C00CD, 164),  # PLAY/PAUSE -> KEY_PLAYPAUSE
		(0x000C00B2, 167),  # RECORD -> KEY_RECORD
		(0x000C0068, 398),  # RED -> KEY_RED
		(0x000C0069, 399),  # GREEN -> KEY_GREEN
		(0x000C006A, 400),  # YELLOW -> KEY_YELLOW
		(0x000C006B, 401),  # BLUE -> KEY_BLUE
		(0x000C0072, 150),  # YouTube -> KEY_WWW
		(0x000C026A, 364),  # FAVORIT -> KEY_FAVORITES
		(0x000C0070, 358),  # INFO -> KEY_INFO
		(0x000C0065, 139),  # MENU -> KEY_MENU
		(0x000C0052, 103),  # UP -> KEY_UP
		(0x000C0051, 108),  # DOWN -> KEY_DOWN
		(0x000C0050, 105),  # LEFT -> KEY_LEFT
		(0x000C004F, 106),  # RIGHT -> KEY_RIGHT
		(0x000C0041, 352),  # OK -> KEY_OK
		(0x000C006D, 392),  # AUDIO -> KEY_AUDIO
		(0x000C0256, 393),  # VIDEO -> KEY_VIDEO
		(0x000C00E9, 115),  # VOL+ -> KEY_VOLUMEUP
		(0x000C00EA, 114),  # VOL- -> KEY_VOLUMEDOWN
		(0x000C0224, 174),  # EXIT -> KEY_EXIT
		(0x000C004B, 402),  # CH+ -> KEY_CHANNELUP
		(0x000C004E, 403),  # CH- -> KEY_CHANNELDOWN
		(0x000C006E, 365),  # EPG -> KEY_EPG
		(0x000C0228, 412),  # bottom < -> KEY_PREVIOUS
		(0x000C0229, 407),  # bottom > -> KEY_NEXT
	),
	("0508", "0110", "0002"): (
		(0x000C0030, 116),  # POWER -> KEY_POWER
		(0x000C0232, 377),  # TV/RADIO -> KEY_TV
		(0x000C001E, 2),    # 1 -> KEY_1
		(0x000C001F, 3),    # 2 -> KEY_2
		(0x000C0020, 4),    # 3 -> KEY_3
		(0x000C0021, 5),    # 4 -> KEY_4
		(0x000C0022, 6),    # 5 -> KEY_5
		(0x000C0023, 7),    # 6 -> KEY_6
		(0x000C0024, 8),    # 7 -> KEY_7
		(0x000C0025, 9),    # 8 -> KEY_8
		(0x000C0026, 10),   # 9 -> KEY_9
		(0x000C0228, 412),  # bottom < -> KEY_PREVIOUS
		(0x000C0027, 11),   # 0 -> KEY_0
		(0x000C0229, 407),  # bottom > -> KEY_NEXT
		(0x000C0068, 398),  # RED -> KEY_RED
		(0x000C0069, 399),  # GREEN -> KEY_GREEN
		(0x000C006A, 400),  # YELLOW -> KEY_YELLOW
		(0x000C006B, 401),  # BLUE -> KEY_BLUE
		(0x000C026A, 364),  # FAV -> KEY_FAVORITES
		(0x000C0070, 358),  # INFO -> KEY_INFO
		(0x000C0065, 139),  # MENU -> KEY_MENU
		(0x000C0052, 103),  # UP -> KEY_UP
		(0x000C0051, 108),  # DOWN -> KEY_DOWN
		(0x000C0050, 105),  # LEFT -> KEY_LEFT
		(0x000C004F, 106),  # RIGHT -> KEY_RIGHT
		(0x000C0041, 352),  # OK -> KEY_OK
		(0x000C006D, 392),  # AUDIO -> KEY_AUDIO
		(0x000C0256, 393),  # VIDEO -> KEY_VIDEO
		(0x000C0224, 174),  # EXIT -> KEY_EXIT
		(0x000C00E9, 115),  # VOL+ -> KEY_VOLUMEUP
		(0x000C00EA, 114),  # VOL- -> KEY_VOLUMEDOWN
		(0x000C006E, 365),  # EPG -> KEY_EPG
		(0x000C0122, 226),  # HISTORY -> KEY_MEDIA
		(0x000C004B, 402),  # CH+ -> KEY_CHANNELUP
		(0x000C004E, 403),  # CH- -> KEY_CHANNELDOWN
		(0x000C00B4, 168),  # REWIND -> KEY_REWIND
		(0x000C0086, 128),  # STOP -> KEY_STOP
		(0x000C00CD, 164),  # PLAY/PAUSE -> KEY_PLAYPAUSE
		(0x000C00B3, 208),  # FAST FORWARD -> KEY_FASTFORWARD
		(0x000C0067, 375),  # PIP -> KEY_SCREEN
		(0x000C00B2, 167),  # RECORD -> KEY_RECORD
		(0x000C0233, 388),  # TEXT -> KEY_TEXT
		(0x000C0258, 359),  # TIMER -> KEY_TIME
		(0x000C0061, 370),  # SUBT -> KEY_SUBTITLE
		(0x000C00E2, 113),  # MUTE -> KEY_MUTE
	),
}

config.plugins.bluetoothsetup = ConfigSubsection()
config.plugins.bluetoothsetup.enable = ConfigYesNo(default=False)
config.plugins.bluetoothsetup.audiodelay = ConfigSelectionNumber(-1000, 1000, 5, default=-500)
config.plugins.bluetoothsetup.showMessageBox = ConfigYesNo(default=True)
config.plugins.bluetoothsetup.showBatteryLow = ConfigYesNo(default=True)
config.plugins.bluetoothsetup.lastAudioConnEnable = ConfigYesNo(default=True)
config.plugins.bluetoothsetup.lastAudioConn = ConfigText(default="")
config.plugins.bluetoothsetup.autoRestartScan = ConfigYesNo(default=True)
config.plugins.bluetoothsetup.scanTime = ConfigSelectionNumber(8, 60, 1, default=30)
config.plugins.bluetoothsetup.gbrcuSkipFwVer = ConfigNumber(default=0)
config.plugins.bluetoothsetup.voiceCheckDb = ConfigSelectionNumber(-40, -20, 1, default=-33)
config.plugins.bluetoothsetup.voiceCallbackName = ConfigSelection(default="Unknown", choices=[("Unknown", "Unknown")])

pybluetooth_instance = None


def showBluetoothStatus(text):
	try:
		from Screens.Toast import Toast
		if Toast.instance is not None:
			Toast.instance.showToast(text, Toast.TYPE_INFO, 5)
			return
	except (ImportError, AttributeError):
		pass
	AddPopup(
		text=text,
		type=MessageBox.TYPE_INFO,
		timeout=5,
		id="bt_event_connected",
	)


class VoiceEventHandler:
	def __init__(self):
		self.voiceHandlers = []
		self.textHandlers = []
		# self.voiceHandlers.append(self.startPlayVoiceTimer)

		self.showVoiceMsgTimer = eTimer()
		self.showVoiceMsgTimer.callback.append(self.showVoiceMsg)

		self.closeVoiceMsgTimer = eTimer()
		self.closeVoiceMsgTimer.callback.append(self.closeVoiceMsg)

		self.noVoiceMsgTimer = eTimer()
		self.noVoiceMsgTimer.callback.append(self.handleNoVoiceEventCB)

		self.voiceMsg = None

		self.isMuted = False

		self.playVoiceTimer = eTimer()
		self.playVoiceTimer.callback.append(self.playVoiceFile)

		self.playVoiceMsg = None
		self.closePlayVoiceMsgTimer = eTimer()
		self.closePlayVoiceMsgTimer.callback.append(self.closePlayVoiceMsg)

		self.lastServiceRef = None

	def setMute(self):
		volumeControlHandle = eDVBVolumecontrol.getInstance()
		if volumeControlHandle.isMuted():
			self.isMuted = True
		else:
			self.isMuted = False
			volumeControlHandle.volumeMute()

	def unsetMute(self):
		volumeControlHandle = eDVBVolumecontrol.getInstance()
		if volumeControlHandle.isMuted():
			if not self.isMuted:
				volumeControlHandle.volumeUnMute()

		self.isMuted = False

	def showVoiceMsg(self):
		self.setMute()
		if self.voiceMsg is None:
			text = _("Put your voice close to the remote control...")
			self.voiceMsg = self.session.open(MessageBox, text, type=MessageBox.TYPE_INFO, enable_input=False)

	def closeVoiceMsg(self):
		self.unsetMute()
		if self.voiceMsg:
			self.voiceMsg.close()
			self.voiceMsg = None

	def handleVoiceEvent(self, value):
		if value and (self.voiceMsg is None):
			self.showVoiceMsgTimer.start(True, 100)

		elif not value and self.voiceMsg:
			self.closeVoiceMsgTimer.start(True, 100)

	def handleNoVoiceEvent(self):
		self.noVoiceMsgTimer.start(True, 500)

	def handleNoVoiceEventCB(self):
		if self.session.dialog_stack and not self.session.in_exec:
			self.handleNoVoiceEvent()
		else:
			text = _("There is no voice input.")
			self.session.open(MessageBox, text, type=MessageBox.TYPE_INFO, timeout=5)

	# BT_EVENT_NEW_VOICE occurred.
	def voiceEventCallback(self):
		name = config.plugins.bluetoothsetup.voiceCallbackName.value
		for callback in self.findCallbackByName(name):
			try:
				callback(bt_types.BT_VOICE_PATH)
			except Exception:
				pass

	def updateCallbackNameList(self):
		voiceCallbackNameList = [("Unknown", "Unknown")]
		for x in self.voiceHandlers:
			callbackItem = (x[2], x[2])
			if callbackItem not in voiceCallbackNameList:
				voiceCallbackNameList.append(callbackItem)
		config.plugins.bluetoothsetup.voiceCallbackName = ConfigSelection(default="Unknown", choices=voiceCallbackNameList)

	def findCallbackByName(self, name):
		callback_list = []
		for x in self.voiceHandlers:
			if x[2] == name:
				callback_list.append(x[0])
		return callback_list

	def findCallbackByHandler(self, handler):
		for x in self.voiceHandlers:
			if x[0] == handler:
				return x
		return None

	# add Speech to Text handler
	def addVoiceHandler(self, handler):
		self.addVoiceHandlerWithName(handler)

	# add Speech to Text handler
	def addVoiceHandlerWithName(self, handler, priority=100, name="Unknown"):
		if handler not in self.findCallbackByName(name):
			self.voiceHandlers.append((handler, priority, name))
			self.voiceHandlers = sorted(self.voiceHandlers, key=lambda h: h[1])
			self.updateCallbackNameList()

	def removeVoiceHandler(self, handler):
		callback = self.findCallbackByHandler(handler)
		if callback is not None:
			self.voiceHandlers.remove(callback)

	# Called by VoiceHandlers
	def textEventCallback(self, text):
		for x in self.textHandlers:
			x(text)

	def addTextHandler(self, handler):
		if handler not in self.textHandlers:
			self.textHandlers.append(handler)

	def removeTextHandler(self, handler):
		if handler in self.textHandlers:
			self.textHandlers.remove(handler)

	def startPlayVoiceTimer(self, value):
		self.playVoiceTimer.start(True, 200)

	def playVoiceFile(self):
		if self.session.dialog_stack and not self.session.in_exec:
			self.startPlayVoiceTimer(None)
			return

		if self.session:
			self.lastServiceRef = self.session.nav.getCurrentlyPlayingServiceReference()
			self.voiceSref = eServiceReference('4097:0:0:0:0:0:0:0:0:0:%s' % bt_types.BT_VOICE_PATH)
			self.session.nav.stopService()
			self.session.nav.playService(self.voiceSref)

			if self.playVoiceMsg is None:
				text = _("Playing Voice data...")
				self.session.openWithCallback(self.closePlayVoiceMsg, MessageBox, text, type=MessageBox.TYPE_INFO, timeout=10)

	def closePlayVoiceMsg(self, value):
		if self.lastServiceRef:
			self.session.nav.playService(self.lastServiceRef)
			self.lastServiceRef = None


class BTVolumeControl:
	def __init__(self):
		self.initVolumeTimer = eTimer()
		self.initVolumeTimer.callback.append(self.InitVolume)
		self.initVolumeTimer.start(500, True)

	def InitVolume(self):
		if hasattr(config, "volumeControl"):
			vol = config.volumeControl.volume.value
			self.setVolume(vol)
		else:
			try:
				vol = config.audio.volume.value
				self.setVolume(vol)
			except Exception:
				self.initVolumeTimer.start(100, True)

	def setVolume(self, vol):
		self.gbbt.setVolume(int(vol))


class BTAutoAudioConnect:
	def __init__(self):
		self.requestAudioTimer = eTimer()
		self.requestAudioTimer.callback.append(self.doStartAudioConnectCB)

		self.btaudioActivated = False
		self.btaudioActivatedInstandby = False

		self.autoAudioMac = None
		self.autoAudioRetryDefault = 5
		self.autoAudioRetry = self.autoAudioRetryDefault

	def enable(self):
		# start Last Audio Connect

		isEnable = config.plugins.bluetoothsetup.enable.value
		bd_addr = config.plugins.bluetoothsetup.lastAudioConn.value

		if isEnable and bd_addr:
			pairedDevices = self.getPairedDevice()
			if pairedDevices:
				for (k, v) in pairedDevices.items():
					# print("bd_addr %s" % v['bd_addr'])
					if v['bd_addr'] == bd_addr:
						self.doStartAudioConnectTimer(bd_addr)
						return

		# bdaddr is not int pairind list

		config.plugins.bluetoothsetup.lastAudioConn.value = ""

	def disable(self):
		# save Last Audio Connect

		bd_addr = self.getLastAudioConnect()
		if bd_addr:
			self.updateLastAudioConnect(bd_addr)

	def doStartAudioConnectTimer(self, bd_addr):
		if not bd_addr:
			return

		self.requestAudioTimer.stop()
		self.autoAudioMac = bd_addr
		if self.isAudioDeviceConnected():
			# NetApp may finish its own reconnect before the Python event loop
			# sees NETAPP_CB_CONNECT.  Activate the PCM path here as well so a
			# fast reconnect cannot leave an already-connected speaker silent.
			self.updateLastAudioConnect(bd_addr)
			self.activateBTAudioOut(True)
			return

		# print("[BT] auto audio connect start, %s" % self.autoAudioMac)
		self.requestAudioTimer.start(500, True)

	def doStartAudioConnectCB(self):
		# print("[BT] request audio connect, %s" % self.autoAudioMac)
		self.requestAudioTimer.stop()
		if self.autoAudioMac:
			if self.isAudioDeviceConnected():
				# Avoid opening the same A2DP profile a second time when the
				# native auto-reconnect wins the 500 ms timer race.
				self.updateLastAudioConnect(self.autoAudioMac)
				self.activateBTAudioOut(True)
			else:
				self.requestConnect(self.autoAudioMac)

	def autoAudioReset(self):
		self.autoAudioMac = None
		self.autoAudioRetry = self.autoAudioRetryDefault

	def retryAudioConnectTimer(self, bd_addr):
		if (bd_addr is not None) and (self.autoAudioMac == bd_addr):
			if self.autoAudioRetry > 0:
				self.autoAudioRetry -= 1
				self.requestAudioTimer.stop()
				# print("[BT] retry audio connect, %s" % self.autoAudioMac)
				self.requestAudioTimer.start(500, True)
			else:
				self.autoAudioReset()

	def getLastAudioConnect(self):
		audio_connected = self.getAudioDeviceConnected()
		if audio_connected:
			return audio_connected['bd_addr']

		return None

	def updateLastAudioConnect(self, bd_addr):
		if bd_addr is None:
			return

		self.autoAudioReset()

		# print("[BT] update Last Audio Connect, %s" % bd_addr)
		if config.plugins.bluetoothsetup.lastAudioConn.value != bd_addr:
			config.plugins.bluetoothsetup.lastAudioConn.value = bd_addr
			config.plugins.bluetoothsetup.lastAudioConn.save()

	def activateBTAudioOut(self, enable):
		if enable and self.btaudioActivated:
			# print("[BT] already btaudio activated!")
			return

		if not enable and not self.btaudioActivated:
			# print("[BT] already btaudio inactivated!")
			return

		self.btaudioActivated = enable
		self.setBTAudioDelay(True)

		time.sleep(0.05)

		try:
			global BT_AUDIO_ONOFF_PROC
			fd = open(BT_AUDIO_ONOFF_PROC, 'w')
			data = enable and "on" or "off"
			fd.write(data)
			fd.close()
			if enable is True:
				self.gbbt.playAudioDevice(config.plugins.bluetoothsetup.lastAudioConn.value)
			else:
				self.gbbt.stopAudioDevice()

		except Exception:
			print("[BT] set %s failed!" % BT_AUDIO_ONOFF_PROC)

	def setBTAudioDelay(self, updateNow=True):
		global BT_AUDIO_DELAY_PROC
		if self.btaudioActivated:
			data = int(config.plugins.bluetoothsetup.audiodelay.value) * 90
			if data < 0:
				data = hex(int('0xffffffff', 16) + data - 1).strip('0x')
			elif data > 0:
				data = hex(data).strip('0x')
			else:
				data = '0'
		else:
			data = '0'

		if self.btaudioActivated or updateNow:
			try:
				fd = open(BT_AUDIO_DELAY_PROC, 'w')
				fd.write(data)
				fd.close()
			except OSError:
				print("[BT] set %s failed!" % BT_AUDIO_DELAY_PROC)

	def isAudioDeviceConnected(self):
		return bool(self.getAudioDeviceConnected())

	def getAudioDeviceConnected(self):
		audio_connected = None
		paired_devices = self.getPairedDevice()
		if paired_devices:
			for (k, v) in paired_devices.items():
				if (isAudioProfile(v['profile'])) and v['isConnected']:
					audio_connected = {}
					audio_connected['name'] = v['name']
					audio_connected['bd_addr'] = v['bd_addr']
					audio_connected['profile'] = v['profile']
					break

		return audio_connected


class BTInStandby:
	def __init__(self):
		config.misc.standbyCounter.addNotifier(self.standbyBegin, initial_call=False)
		self.enable_on_standby = False
		self.resume_audio_after_standby = False

	def standbyBegin(self, configElement):
		self.enable_on_standby = config.plugins.bluetoothsetup.enable.value

		if self.enable_on_standby:
			from Screens.Standby import inStandby
			if self.standbyEnd not in inStandby.onClose:
				inStandby.onClose.append(self.standbyEnd)

			# Keep the persistent HID link alive in standby. Only stop feeding
			# PCM to a connected speaker; the daemon and Bluetooth profiles
			# remain active and the RCU can wake immediately.
			self.resume_audio_after_standby = self.btaudioActivated
			if self.resume_audio_after_standby:
				self.activateBTAudioOut(False)

	def standbyEnd(self):
		if self.enable_on_standby:
			self.enable()
			if self.resume_audio_after_standby:
				BTAutoAudioConnect.enable(self)
			self.resume_audio_after_standby = False


class BTBatteryLevel:
	def __init__(self):
		self.batteryLevelTimer = eTimer()
		self.batteryLevelTimer.callback.append(self.updateBatteryLevel)
		self.batteryUpdateInterval = 60 * 60 * 12 * 1000  # every 12 hours
		self.batteryCheckRetryTime = 15 * 1000  # maximum time to waiting voice stop
		self.lastMsgMday = -1
		self.batteryLevel = 0

	def startBatteryTimer(self):
		self.lastMsgMday = -1
		self.batteryLevelTimer.start(100, True)

	def updateBatteryLevel(self):
		if self.gbbt.getStatus() == self.BT_STATUS_ENABLED:
			# Do not check the battery during voice recording.
			if self.gbbt.isVoiceRecording():
				self.batteryLevelTimer.start(self.batteryCheckRetryTime, True)
			else:
				self.gbbt.updateBatteryLevel()
				self.batteryLevelTimer.start(self.batteryUpdateInterval, True)

	def disableBatteryLevel(self):
		self.batteryLevelTimer.stop()

	def getMday(self):
		return time.localtime().tm_mday

	def showLowBatteryMessage(self):
		mDay = self.getMday()
		if self.lastMsgMday != mDay:
			self.lastMsgMday = mDay
			AddNotification(MessageBox, _("Battery is low. Suggest to prepare replacement batteries for using properly %s.") % bt_types.BT_GB_RCU_NAME, type=MessageBox.TYPE_INFO)


class BTOTAProcess:
	OTA_COMPLETE = 34
	OTA_APP_VERSION = 2
	OTA_FILE_APP_VERSION = 7

	def __init__(self):
		self.pluginOtaEventHandler = []
		self.gbbt.OTA_addEventCallback(self.OTAEventCallback)

		self.startOTATimer = eTimer()
		self.startOTATimer.callback.append(self.startOTAUpdate)

		self.handleOtaDoneTimer = eTimer()
		self.handleOtaDoneTimer.callback.append(self.handleOtaDoneTimerCB)

		self.firmwareCheckTimer = eTimer()
		self.firmwareCheckTimer.callback.append(self.checkFWVersion)
		self.FWCheckRetryTime = 15 * 1000  # maximum time to waiting voice stop
		self.bd_addr = None
		self.rcuAppVersion = None

	def OTAEventCallback(self, evType, value):
		print("[OTAEventCallback] evType : %s, value : %s" % (str(evType), str(value)))

		if evType == BTOTAProcess.OTA_COMPLETE:
			self.handleOtaDoneTimer.start(0, True)

		elif evType == BTOTAProcess.OTA_APP_VERSION:
			self.rcuAppVersion = value

		elif evType == BTOTAProcess.OTA_FILE_APP_VERSION:
			self.firmwareFileVersion = value

			# check app version
			if self.firmwareFileVersion > self.rcuAppVersion:
				if config.plugins.bluetoothsetup.gbrcuSkipFwVer.value != self.firmwareFileVersion:
					self.showFWUpdateNoti()
		else:
			try:
				for handler in self.pluginOtaEventHandler:
					handler(evType, value)
			except Exception as e:
				print("[BT] exception error : %s" % str(e))

	def OTAInit(self):
		self.gbbt.OTAInit()

	def OTADeInit(self):
		self.gbbt.OTADeInit()

	def OTAStart(self):
		self.otaMode = True
		self.gbbt.OTAStart()

	def OTAStop(self):
		self.gbbt.OTAStop()
		self.otaMode = False

	def handleOtaDoneTimerCB(self):
		self.OTAStop()

	def startFWCheckTimer(self, bd_addr):
		self.bd_addr = bd_addr
		self.firmwareCheckTimer.start(0, True)

	def checkFWVersion(self):
		if self.gbbt.getStatus() == self.BT_STATUS_ENABLED:
			# Do not check the battery during voice recording.
			if self.gbbt.isVoiceRecording():
				self.firmwareCheckTimer.start(self.FWCheckRetryTime, True)
			else:
				self.gbbt.OTACheckFWVersion(self.bd_addr, bt_types.BT_FIRMWARE_FILEPATH)

	def stopFWCheckTimer(self):
		self.firmwareCheckTimer.stop()

	def showFWUpdateNoti(self):
		_title = _("New firmware detected for GB-BLE-RCU.\n\n")
		_title += _("While the update is progress, RCU can not be used and other bluetooth device must be disconnected.\n\n")
		_title += _("Current FW version : %d\nNew FW version : %d") % (self.rcuAppVersion, self.firmwareFileVersion)
		choiceList = ((_("Upgrade now"), "update"), (_("Remind Me later"), "no"), (_("Skip this version"), "skip"))
		AddNotificationWithCallback(self.showFWUpdateAnswer, ChoiceBox, _title, choiceList)

	def showFWUpdateAnswer(self, answer):
		if answer:
			if answer[1] == 'update':
				config.plugins.bluetoothsetup.gbrcuSkipFwVer.value = 0
				config.plugins.bluetoothsetup.gbrcuSkipFwVer.save()
				if not self.isGbBleRcuConnected():
					text = _('GB-BLE-RCU is disconnected. Please connect and select again.')
					AddNotification(MessageBox, _(text), type=MessageBox.TYPE_INFO)
				elif self.session and self.bd_addr:
					self.startOTATimer.start(0, True)

			elif answer[1] == 'skip':
				config.plugins.bluetoothsetup.gbrcuSkipFwVer.value = self.firmwareFileVersion
				config.plugins.bluetoothsetup.gbrcuSkipFwVer.save()
				text = _('If you want to update this firmware version, follow belows.\n\n')
				text += _('1. Move to Bluetooth Setup Options.\n(press MENU key in BluetoothSetup)\n')
				text += _('2. Change "Skip firmware update of GB-BLE-RCU" option to "no"\n')
				text += _('3. Reconnect the GB-BLE-RCU.\n\n')
				AddNotification(MessageBox, _(text), type=MessageBox.TYPE_INFO)

	def startOTAUpdate(self):
		self.session.open(GbRcuOtaUpdate, self.bd_addr, self, self.batteryLevel, self.rcuAppVersion, self.firmwareFileVersion)

	def isGbBleRcuConnected(self):
		connected = False
		paired_devices = self.getPairedDevice()
		if paired_devices:
			for (k, v) in paired_devices.items():
				if v['name'] == bt_types.BT_GB_RCU_NAME:
					if v['isConnected']:
						connected = True

					break

		return connected


class BTHotplugEvent:
	def __init__(self):
		self.btEnableTimer = eTimer()
		self.btEnableTimer.callback.append(self.enableTimerCB)

		self.btDisableTimer = eTimer()
		self.btDisableTimer.callback.append(self.disableTimerCB)

		self.showBtDongleMsgTimer = eTimer()
		self.showBtDongleMsgTimer.callback.append(self.showBtDongleMsg)

	def startEnableTimer(self, _enable):
		from Screens.Standby import inStandby
		if inStandby:
			print("[BTHotplugEvent] now in standby, skip BT hotplug event.")
			return

		print("[BTHotplugEvent] startEnableTimer! ", _enable)

		self.btEnableTimer.stop()
		self.btDisableTimer.stop()

		if _enable:
			self.btEnableTimer.start(500, True)
		else:
			self.btDisableTimer.start(500, True)

	def enableTimerCB(self):
		print("[BTHotplugEvent] Enable")

		if config.plugins.bluetoothsetup.enable.value:
			self.onOffChanged(True)
			time.sleep(0.1)

		if self.pluginEventHandler:
			for handler in self.pluginEventHandler:
				handler(bt_types.BT_EVENT_BT_CONNECTED, None)

	def disableTimerCB(self):
		print("[BTHotplugEvent] Disable")

		if self.isEnabled():
			if self.isGbBleRcuConnected():
				self.showBtDongleMsgTimer.start(100, True)

		self.onOffChanged(False)
		time.sleep(0.1)

		if self.pluginEventHandler:
			for handler in self.pluginEventHandler:
				handler(bt_types.BT_EVENT_BT_DISCONNECTED, None)

	def showBtDongleMsg(self):
		if self.session.dialog_stack and not self.session.in_exec:
			self.showBtDongleMsgTimer.start(500, True)
		else:
			text = _("The BT dongle has been removed. It takes 10 seconds from when the BT dongle is removed until the remote control operates in IR mode.")
			self.session.open(MessageBox, text, type=MessageBox.TYPE_INFO, timeout=20)

	def handleInsertEvent(self):
		self.startEnableTimer(True)

	def handleRemoveEvent(self):
		self.startEnableTimer(False)

	def checkBTUSB(self):
		return self.gbbt.checkBTUSB()


class PyBluetoothInterface(VoiceEventHandler, BTVolumeControl, BTAutoAudioConnect, BTInStandby, BTBatteryLevel, BTOTAProcess, BTHotplugEvent, BluetoothTask):
	BT_STATUS_DISABLED = 0
	BT_STATUS_ENABLED = 1

	def __init__(self):
		self.gbbt = gbbt.Gb_PyBluetooth()

		VoiceEventHandler.__init__(self)
		BTVolumeControl.__init__(self)
		BTAutoAudioConnect.__init__(self)
		BTInStandby.__init__(self)
		BTBatteryLevel.__init__(self)
		BTOTAProcess.__init__(self)
		BTHotplugEvent.__init__(self)
		BluetoothTask.__init__(self)

		self.gbbt.addEventCallback(self.eventCallback)
		self.gbbt.addBleEventCallback(self.bleEventCallback)
		self.status = self.BT_STATUS_DISABLED
		self.pluginEventHandler = []
		self.pluginBleEventHandler = []
		self.pluginStatusHandler = []
		self.session = None
		self.inputDeviceTimer = eTimer()
		self.inputDeviceTimer.callback.append(self.updateInputDevices)
		self.inputDeviceNodes = set()
		self.managedInputDevices = set()

		self.otaMode = False

		BluetoothTask.addTask1(self, BluetoothTask.TASK_CHECK_STATUS, self.check_status, None, None, None)

	def disconnectAll(self):
		self.deviceList = []
		pairedDevices = self.gbbt.getPairedDevice()

		if pairedDevices:
			for (k, v) in pairedDevices.items():
				if v['isConnected']:
					self.gbbt.requestDisconnect(v['bd_addr'])
					if (isAudioProfile(v['profile'])):
						self.activateBTAudioOut(False)

	def registerHidInputDevices(self):
		# The legacy bthid driver creates evdev nodes but does not emit the
		# netlink hotplug event consumed by Components.InputHotplug. Detect new
		# evdev nodes explicitly so keyboards, mice and third-party remotes are
		# usable immediately without restarting Enigma2.
		self.updateInputDevices()

	def applyHidKeymap(self, device, event):
		idPath = "/sys/class/input/%s/device/id" % event
		try:
			with open("%s/vendor" % idPath, "r") as source:
				vendor = source.read().strip().lower()
			with open("%s/product" % idPath, "r") as source:
				product = source.read().strip().lower()
			with open("%s/version" % idPath, "r") as source:
				version = source.read().strip().lower()
		except OSError as error:
			print("[BT] unable to read HID identity for %s: %s" % (device, error))
			return

		identity = (vendor, product, version)
		keymapIdentity = identity
		keymap = BT_HID_KEYMAPS.get(identity)
		if not keymap and identity == ("0000", "0000", "0111"):
			# The older Broadcom BSA path creates the first GigaBlue RCU
			# input node before its PnP data has reached bthid.  The saved
			# NetApp record already contains 0508:0110, but the kernel node
			# consequently exposes the generic 0000:0000:0111 identity.
			# Restrict this fallback to the exact legacy RCU name so generic
			# keyboards and mice with an incomplete PnP identity keep their
			# normal kernel mappings.
			pairedDevices = self.gbbt.getPairedDevice()
			legacyRcus = [
				value for value in pairedDevices.values()
				if value.get("name", "").strip().upper() == "GIGABLUE RCU"
			]
			if len(legacyRcus) == 1:
				keymapIdentity = ("0508", "0110", "0000")
				keymap = BT_HID_KEYMAPS.get(keymapIdentity)
		if not keymap:
			return

		fd = None
		applied = 0
		failed = []
		try:
			fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
			for scanCode, keyCode in keymap:
				try:
					fcntl.ioctl(fd, EVIOCSKEYCODE, struct.pack("II", scanCode, keyCode))
					applied += 1
				except OSError:
					failed.append(scanCode)
		except OSError as error:
			print("[BT] unable to open %s for HID keymap %s:%s:%s: %s" % (
				device, vendor, product, version, error
			))
			return
		finally:
			if fd is not None:
				os.close(fd)

		if failed:
			print("[BT] applied %d/%d HID keys %s:%s:%s via %s:%s:%s to %s; unsupported scans: %s" % (
				applied, len(keymap), vendor, product, version,
				keymapIdentity[0], keymapIdentity[1], keymapIdentity[2], device,
				",".join("0x%08X" % scanCode for scanCode in failed)
			))
		else:
			print("[BT] applied %d-key HID map %s:%s:%s via %s:%s:%s to %s" % (
				applied, vendor, product, version,
				keymapIdentity[0], keymapIdentity[1], keymapIdentity[2], device
			))

	def updateInputDevices(self):
		# Stale character nodes can remain in /dev/input after a bthid close.
		# sysfs contains only devices that are currently registered with the
		# input core, so use it as the source of truth.
		current = {
			"/dev/input/%s" % entry.rsplit("/", 1)[-1]
			for entry in glob("/sys/class/input/event*")
		}

		for device in sorted(self.inputDeviceNodes - current):
			if device in self.managedInputDevices:
				# Do not synchronously destroy an Enigma2 input driver here.
				# A disconnect can be initiated by the POWER key while
				# eRCInputEventDriver::keyPressed() is still dispatching that
				# same event. Removing it from this callback path leaves a
				# queued socket-notifier activation pointing at freed memory.
				#
				# Keep the inactive entry until a new kernel device appears.
				# The add path below then replaces it outside the key callback.
				pass

		for device in sorted(current - self.inputDeviceNodes):
			event = device.rsplit("/", 1)[-1]
			isBluetoothInput = False
			try:
				with open("/sys/class/input/%s/device/name" % event, "r") as source:
					isBluetoothInput = source.read().strip() == "Broadcom-NetApp"
			except OSError:
				pass
			if isBluetoothInput:
				self.applyHidKeymap(device, event)
				# A previous bthid instance can leave Enigma2 with an entry
				# whose open() failed. addInputDevice() ignores duplicate
				# filenames, so replace that stale entry before registering
				# the current kernel device.
				removeInputDevice(device)
				self.managedInputDevices.add(device)
			addInputDevice(device)

		self.inputDeviceNodes = current

	def setScanTime(self, scanDuration):
		scanDuration = int(scanDuration)
		if (scanDuration <= 0) or (scanDuration > 30):
			# print("[BT] invalid scanDuration")
			return

		self.gbbt.setScanTime(scanDuration)

	def eventCallback(self, evType, data):
		# print("[eventCallback] evType : %s" % str(evType))

		if self.otaMode:
			return

		'''
		print("[eventCallback] evType : %s" % str(evType))
		print("[eventCallback] data : %s" % str(data))
		print("[eventCallback] event : %s" % (getEventDesc(evType)))
		'''

		bd_addr = data.get("bd_addr", None)
		name = data.get("name", bd_addr)

		try:
			if evType == bt_types.BT_EVENT_REQUEST_AUDIO_CONNECT:
				self.doStartAudioConnectTimer(bd_addr)
			elif evType == bt_types.BT_EVENT_CONNECT_TIMEOUT:
				if isAudioProfile(data['profile']):
					self.retryAudioConnectTimer(bd_addr)
			elif evType == bt_types.BT_EVENT_BT_CONNECTED:
				self.handleInsertEvent()
			elif evType == bt_types.BT_EVENT_BT_DISCONNECTED:
				self.handleRemoveEvent()

			elif evType in (bt_types.BT_EVENT_BT_VOICE_START, bt_types.BT_EVENT_BT_VOICE_STOP):
				self.handleVoiceEvent(evType == bt_types.BT_EVENT_BT_VOICE_START)

			elif evType == bt_types.BT_EVENT_NEW_VOICE:
				self.voiceEventCallback()
			elif evType == bt_types.BT_EVENT_BT_NO_VOICE:
				self.handleNoVoiceEvent()
			else:
				if evType == bt_types.BT_EVENT_CONNECTED:
					if bt_types.isHidDevice(data):
						self.registerHidInputDevices()
					if (isAudioProfile(data['profile'])) and data['connected']:
						self.updateLastAudioConnect(bd_addr)
						self.activateBTAudioOut(True)

				if evType == bt_types.BT_EVENT_DISCONNECTED:
					if (isAudioProfile(data['profile'])) and not data['connected']:
						self.activateBTAudioOut(False)
						if (
							config.plugins.bluetoothsetup.enable.value
							and config.plugins.bluetoothsetup.lastAudioConn.value == bd_addr
						):
							# The sink may disappear briefly because it was
							# powered off or moved out of range.  Explicit UI
							# disconnects clear lastAudioConn before this event,
							# so only unexpected link losses are retried.
							self.doStartAudioConnectTimer(bd_addr)

				if self.pluginEventHandler:
					for handler in self.pluginEventHandler:
						handler(evType, data)

				elif evType in (bt_types.BT_EVENT_CONNECTED, bt_types.BT_EVENT_DISCONNECTED):
					if config.plugins.bluetoothsetup.showMessageBox.value:
						from Screens.Standby import inStandby
						if self.session and not inStandby:
							if evType == bt_types.BT_EVENT_CONNECTED:
								text = _("%s is connected.") % name
							elif evType == bt_types.BT_EVENT_DISCONNECTED:
								text = _("%s is disconnected.") % name
							showBluetoothStatus(text)

		except Exception as e:
			print("[BT] exception error : %s" % str(e))

	def bleEventCallback(self, evType, data):
		if self.otaMode:
			return

		'''
		print("[bleEventCallback] evType : %s" % str(evType))
		print("[bleEventCallback] data : %s" % str(data))
		print("[bleEventCallback] event : %s" % (getEventDesc(evType)))
		'''

		bd_addr = data.get("bd_addr", None)
		name = data.get("name", bd_addr)  # noqa F841
		value = data.get("value", None)

		try:
			if evType == bt_types.BT_EVENT_CONNECTED:
				if bt_types.isHidDevice(data):
					self.registerHidInputDevices()
				if data.get("profile") == bt_types.BT_PROFILE_GB_RC:
					self.startBatteryTimer()

			elif evType == bt_types.BT_EVENT_DISCONNECTED:
				if data.get("profile") == bt_types.BT_PROFILE_GB_RC:
					self.batteryLevelTimer.stop()

			elif evType == bt_types.BT_EVENT_CONNECT_TIMEOUT:
				pass
			elif evType == bt_types.BT_EVENT_READ_BATTERY_LEVEL:
				if value:
					# print("[bleEventCallback] get battery level : %d (%s)" % (value, bd_addr)

					self.batteryLevel = value
					isBatteryLow = (
						data.get("profile") == bt_types.BT_PROFILE_GB_RC
						and self.batteryLevel < bt_types.BT_BATTERY_LEVEL_LOW
					)
					if isBatteryLow:
						if config.plugins.bluetoothsetup.showBatteryLow.value:
							self.showLowBatteryMessage()
					else:
						self.startFWCheckTimer(bd_addr)

			if self.pluginBleEventHandler:
				for handler in self.pluginBleEventHandler:
					handler(evType, data)

		except Exception as e:
			print("[bleEventCallback] exception error : %s" % str(e))

	def onOffChanged(self, value=True):
		if value and (not self.isEnabled()):
			self.enable()
		elif (not value) and self.isEnabled():
			self.disconnectAll()
			time.sleep(0.1)
			self.disable()

	def enable(self):
		self.gbbt.enable()
		self.updateStatus()
		BTAutoAudioConnect.enable(self)
		# Force one idempotent registration pass. A saved HOGP device can
		# create its event node between Enigma2's input initialization and
		# this plugin being enabled.
		self.inputDeviceNodes = set()
		self.updateInputDevices()
		self.inputDeviceTimer.start(500, False)

	def disable(self, update=True):
		self.inputDeviceTimer.stop()
		# gbbt.disable() removes the kernel HID device. Do not call
		# removeInputDevice() synchronously here: disable may be entered from
		# the POWER-key handler and deleting that handler's input driver causes
		# eRCInputEventDriver::keyPressed() to use freed memory. A subsequent
		# reconnect safely replaces the stale filename in updateInputDevices().
		self.inputDeviceNodes = set()
		BTAutoAudioConnect.disable(self)
		self.gbbt.disable()
		if update:
			self.updateStatus()

		self.disableBatteryLevel()
		self.stopFWCheckTimer()

	def detach(self):
		"""Detach Enigma2 without stopping the persistent Bluetooth service."""
		self.inputDeviceTimer.stop()
		self.requestAudioTimer.stop()
		self.disableBatteryLevel()
		self.stopFWCheckTimer()
		self.inputDeviceNodes = set()
		BTAutoAudioConnect.disable(self)
		self.gbbt.deinit()

	def isEnabled(self):
		return self.status == self.BT_STATUS_ENABLED

	def updateStatus(self):
		self.status = self.gbbt.getStatus()
		# print("[BT] current status : %s" % str(self.status))

		for handler in self.pluginStatusHandler:
			handler(self.status)

	def startScan(self, isBle=False):
		return self.gbbt.startScan(False, isBle)

	def abortScan(self):
		self.gbbt.abortScan()

	def resetScan(self):
		self.gbbt.resetScan()

	def getSystemInfo(self):
		return self.gbbt.getSystemInfo()

	def getDiscDevice(self):
		return self.gbbt.getDiscDevice()

	def getPairedDevice(self):
		return self.gbbt.getPairedDevice()

	def requestPairing(self, mac):
		return self.gbbt.requestPairing(mac)

	def cancelPairing(self, mac):
		return self.gbbt.cancelPairing(mac)

	def removePairing(self, mac, profile):
		if isAudioProfile(profile):
			self.updateLastAudioConnect("")
		return self.gbbt.removePairing(mac)

	def removePairedList(self, mac):
		return self.gbbt.removePairedList(mac)

	def requestSendPincode(self, mac, pincode):
		return self.gbbt.requestSendPincode(mac, pincode)

	def requestConnect(self, mac):
		return self.gbbt.requestConnect(mac)

	def requestDisconnect(self, mac, profile):
		if isAudioProfile(profile):
			self.updateLastAudioConnect("")
		return self.gbbt.requestDisconnect(mac)

	def requestBLEConnect(self, mac):
		return self.gbbt.requestBLEConnect(mac)

	def requestBLEDisconnect(self, mac):
		return self.gbbt.requestBLEDisconnect(mac)

	def setDisCoverable(self, value):
		self.gbbt.setDisCoverable(value)

	def setSession(self, session):
		self.session = session

	def resetSearchedDevices(self):
		self.gbbt.resetSearchedDevices()

	def cleanupBleClient(self):
		self.gbbt.cleanupBleClient()

	def setVoiceCheckDB(self, value):
		int_value = int(value)
		print("[setVoiceCheckDB] value : %d" % int_value)
		self.gbbt.setVoiceCheckDB(int_value)

	def check_status(self):
		return self.gbbt.CheckStatus()

	def onCheckStatusFinished(self):
		pass

	def isMaxBLEPairedDevice(self):
		return self.gbbt.isMaxBLEPairedDevice()


pybluetooth_instance = PyBluetoothInterface()


def BluetoothOnOffChanged(configElement):
	global pybluetooth_instance
	pybluetooth_instance.onOffChanged(configElement.value)


config.plugins.bluetoothsetup.enable.addNotifier(BluetoothOnOffChanged)


def BluetoothAudioDelayChanged(configElement):
	global pybluetooth_instance
	pybluetooth_instance.setBTAudioDelay(False)


config.plugins.bluetoothsetup.audiodelay.addNotifier(BluetoothAudioDelayChanged)


def BluetoothVoiceCheckValChanged(configElement):
	global pybluetooth_instance
	pybluetooth_instance.setVoiceCheckDB(configElement.value)


config.plugins.bluetoothsetup.voiceCheckDb.addNotifier(BluetoothVoiceCheckValChanged)
