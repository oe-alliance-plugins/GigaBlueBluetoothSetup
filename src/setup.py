from setuptools import setup
import setup_translate

pkg = 'SystemPlugins.BluetoothSetup'
setup(name='enigma2-plugin-systemplugins-bluetoothsetup',
       version='3.0',
       description='GigaBlue bluetooth plugin',
       package_dir={pkg: 'GigaBlueBluetoothSetup'},
       packages=[pkg],
       package_data={pkg: ['images/*.png', '*.png', '*.xml', 'locale/*/LC_MESSAGES/*.mo', 'plugin.png', 'bt_audio.png', 'bt_keyboard.png', 'bt_misc.png', 'bt_rc.png', 'keymap.xml', 'ble_local_keys', 'libgbbtcore.so']},
       cmdclass=setup_translate.cmdclass,  # for translation
      )
