# set QT_API environment variable
import os 
os.environ["QT_API"] = "pyqt5"
import qtpy

# qt libraries
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *

import time

# app specific libraries
import control.widgets as widgets
import control.camera as camera
import control.camera_ids as camera_spectrometer
import control.core as core
import control.microcontroller as microcontroller
import pyqtgraph.dockarea as dock
from pathlib import Path
import squid.logging

from control._def import *

SINGLE_WINDOW = True # set to False if use separate windows for display and control
DEFAULT_DISPLAY_CROP = 100

MAIN_CAMERA_MODEL = ''

class OctopiGUI(QMainWindow):

	# variables
	fps_software_trigger = 100

	def __init__(self, is_simulation=False, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.log = squid.logging.get_logger(self.__class__.__name__)

		# load objects
		if is_simulation:
			self.camera_spectrometer = camera_spectrometer.Camera_Simulation(sn='05814441')
			self.camera_widefield = camera.Camera_Simulation(rotate_image_angle=ROTATE_IMAGE_ANGLE,flip_image=FLIP_IMAGE)
			self.microcontroller = microcontroller.Microcontroller(existing_serial=microcontroller.SimSerial(),is_simulation=True)
		else:
			self.camera_spectrometer = camera_spectrometer.Camera()
			self.camera_widefield = camera.Camera(rotate_image_angle=ROTATE_IMAGE_ANGLE,flip_image=FLIP_IMAGE)
			self.microcontroller = microcontroller.Microcontroller(version='Teensy')

		# configure the actuators
		self.microcontroller.configure_actuators()
		
		self.streamHandler_spectrum = core.StreamHandler()
		self.objectiveStore = core.ObjectiveStore(parent=self)
		self.configurationManager_spectrum = core.ConfigurationManager(str(Path.home()) + "/configurations_spectrometer_spectrum.xml",channel='Spectrum')
		self.configurationManager_widefield = core.ConfigurationManager(str(Path.home()) + "/configurations_spectrometer_widefield.xml",channel='Widefield')
		self.liveController_spectrum = core.LiveController(self.camera_spectrometer,self.microcontroller,self.configurationManager_spectrum)
		self.imageSaver = core.ImageSaver()
		self.imageDisplay = core.ImageDisplay()

		self.streamHandler_widefield = core.StreamHandler()
		self.liveController_widefield = core.LiveController(self.camera_widefield,self.microcontroller,self.configurationManager_widefield)
		self.imageSaver_widefield = core.ImageSaver()
		self.imageDisplay_widefield = core.ImageDisplay()

		self.spectrumExtractor = core.SpectrumExtractor()
		self.spectrumROIManager = core.SpectrumROIManager(self.camera_spectrometer,self.liveController_spectrum,self.spectrumExtractor)
		
		self.navigationController = core.NavigationController(self.microcontroller, self.objectiveStore, parent=self)
		self.autofocusController = core.AutoFocusController(self.camera_widefield,self.navigationController,self.liveController_widefield)

		self.slidePositionController = core.SlidePositionController(self.navigationController,self.liveController_widefield)
		
		self.cameras = {}
		self.cameras['Widefield'] = self.camera_widefield
		self.cameras['Spectrum'] = self.camera_spectrometer
		self.configurationManagers = {}
		self.configurationManagers['Widefield'] = self.configurationManager_widefield
		self.configurationManagers['Spectrum'] = self.configurationManager_spectrum
		self.liveControllers = {}
		self.liveControllers['Widefield'] = self.liveController_widefield
		self.liveControllers['Spectrum'] = self.liveController_spectrum

		self.multipointController = core.MultiPointController(self.cameras,self.navigationController,self.liveControllers,self.autofocusController,self.configurationManagers)

		# open the camera
		# camera start streaming
		self.camera_spectrometer.open()
		self.camera_spectrometer.set_software_triggered_acquisition()
		self.camera_spectrometer.set_callback(self.streamHandler_spectrum.on_new_frame)
		self.camera_spectrometer.enable_callback()

		self.camera_widefield.open()
		self.camera_widefield.set_software_triggered_acquisition()
		self.camera_widefield.set_callback(self.streamHandler_widefield.on_new_frame)
		self.camera_widefield.enable_callback()

		# load widgets
		self.cameraSettingWidget_spectrum = widgets.CameraSettingsWidget(self.camera_spectrometer,include_gain_exposure_time=False)
		self.liveControlWidget_spectrum = widgets.LiveControlWidget(self.streamHandler_spectrum,self.liveController_spectrum,self.configurationManager_spectrum,show_display_options=False)
		self.recordingControlWidget_spectrum = widgets.RecordingWidget(self.streamHandler_spectrum,self.imageSaver)

		self.cameraSettingWidget_widefield = widgets.CameraSettingsWidget(self.camera_widefield,include_gain_exposure_time=False)
		self.liveControlWidget_widefield = widgets.LiveControlWidget(self.streamHandler_widefield,self.liveController_widefield,self.configurationManager_widefield,show_display_options=False)
		self.recordingControlWidget_widefield = widgets.RecordingWidget(self.streamHandler_widefield,self.imageSaver_widefield)

		self.spectrumROIManagerWidget = widgets.SpectrumROIManagerWidget(self.spectrumExtractor,self.spectrumROIManager, self.camera_spectrometer)
		self.brightfieldWidget = widgets.BrightfieldWidget(self.liveController_spectrum)

		self.navigationWidget = widgets.NavigationWidget(self.navigationController)
		self.autofocusWidget = widgets.AutoFocusWidget(self.autofocusController)
		self.multiPointWidget = widgets.MultiPointWidget(self.multipointController,self.configurationManagers)

		# layout widgets
		layout_spectrum_control = QVBoxLayout()
		layout_spectrum_control.addWidget(self.cameraSettingWidget_spectrum)
		layout_spectrum_control.addWidget(self.liveControlWidget_spectrum)
		layout_spectrum_control.addWidget(self.spectrumROIManagerWidget)
		layout_spectrum_control.addWidget(self.recordingControlWidget_spectrum)

		layout_widefield_control = QVBoxLayout()
		layout_widefield_control.addWidget(self.cameraSettingWidget_widefield)
		layout_widefield_control.addWidget(self.liveControlWidget_widefield)
		layout_widefield_control.addWidget(self.brightfieldWidget)
		layout_widefield_control.addWidget(self.recordingControlWidget_widefield)

		tab_spectrum_control = QWidget()
		tab_spectrum_control.setLayout(layout_spectrum_control)
		tab_widefield_control = QWidget()
		tab_widefield_control.setLayout(layout_widefield_control)

		self.controlTabWidget = QTabWidget()
		self.controlTabWidget.addTab(tab_widefield_control, "Widefield")
		self.controlTabWidget.addTab(tab_spectrum_control, "Spectrum")
		acquisitionTabWidget = QTabWidget()
		acquisitionTabWidget.addTab(self.multiPointWidget, "Multipoint")
		acquisitionTabWidget.addTab(self.recordingControlWidget_spectrum, "Recording - Spectrum")
		acquisitionTabWidget.addTab(self.recordingControlWidget_widefield, "Recording - Widefield")

		layout = QVBoxLayout()
		layout.addWidget(self.controlTabWidget)
		layout.addWidget(self.navigationWidget)
		layout.addWidget(self.autofocusWidget)
		layout.addWidget(acquisitionTabWidget)

		# transfer the layout to the central widget
		self.centralWidget = QWidget()
		self.centralWidget.setLayout(layout)
		# self.setCentralWidget(self.centralWidget)

		# load window
		self.imageDisplayWindow_spectrum = core.ImageDisplayWindow()
		# self.imageDisplayWindow_spectrum.show()
		self.imageDisplayWindow_widefield = core.ImageDisplayWindow()
		# self.imageDisplayWindow_widefield.show()
		# load spectrum display window
		self.spectrumDisplayWindow = widgets.SpectrumDisplayWindow()
		# self.spectrumDisplayWindow.show()

		# dock windows
		dock_imageDisplay_widefield = dock.Dock('Widefield', autoOrientation = False)
		dock_imageDisplay_widefield.showTitleBar()
		dock_imageDisplay_widefield.addWidget(self.imageDisplayWindow_widefield.widget)
		dock_imageDisplay_widefield.setStretch(x=5,y=2)

		dock_imageDisplay_spectrum = dock.Dock('Spectrum', autoOrientation = False)
		dock_imageDisplay_spectrum.showTitleBar()
		dock_imageDisplay_spectrum.addWidget(self.imageDisplayWindow_spectrum.widget)
		dock_imageDisplay_spectrum.setStretch(x=5,y=1)

		dock_spectrumDisplay = dock.Dock('Extracted Spectrum', autoOrientation = False)
		dock_spectrumDisplay.showTitleBar()
		dock_spectrumDisplay.addWidget(self.spectrumDisplayWindow.plotWidget)
		dock_spectrumDisplay.setStretch(x=5,y=1)

		display_dockArea = dock.DockArea()
		display_dockArea.addDock(dock_imageDisplay_widefield)
		display_dockArea.addDock(dock_imageDisplay_spectrum,'right')
		display_dockArea.addDock(dock_spectrumDisplay,'bottom',dock_imageDisplay_spectrum)
		
		if SINGLE_WINDOW:
			dock_controlPanel = dock.Dock('Controls', autoOrientation = False)
			# dock_controlPanel.showTitleBar()
			dock_controlPanel.addWidget(self.centralWidget)
			dock_controlPanel.setStretch(x=1,y=2)
			display_dockArea.addDock(dock_controlPanel,'right')
			self.setCentralWidget(display_dockArea)
		else:
			self.displayWindow = QMainWindow()
			# self.displayWindow.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
			# self.displayWindow.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
			self.displayWindow.setCentralWidget(display_dockArea)
			self.displayWindow.setWindowTitle('Displays')
			self.displayWindow.show()
			# main window
			self.setCentralWidget(self.centralWidget)
	
		# make connections
		self.streamHandler_spectrum.signal_new_frame_received.connect(self.liveController_spectrum.on_new_frame)
		self.streamHandler_spectrum.image_to_display.connect(self.imageDisplay.enqueue)
		self.streamHandler_spectrum.packet_image_to_write.connect(self.imageSaver.enqueue)
		self.imageDisplay.image_to_display.connect(self.imageDisplayWindow_spectrum.display_image) # may connect streamHandler directly to imageDisplayWindow
		self.spectrumROIManager.ROI_coordinates.connect(self.streamHandler_spectrum.set_ROIvisualization)

		self.brightfieldWidget.btn_calc_spot.clicked.connect(self.imageDisplayWindow_widefield.slot_calculate_centroid)
		self.brightfieldWidget.btn_show_circle.clicked.connect(self.imageDisplayWindow_widefield.toggle_circle_display)

		# route the new image (once it has arrived) to the spectrumExtractor
		self.streamHandler_spectrum.image_to_spectrum_extraction.connect(self.spectrumExtractor.extract_and_display_the_spectrum)
		self.spectrumExtractor.packet_spectrum.connect(self.spectrumDisplayWindow.plotWidget.plot)

		self.streamHandler_widefield.signal_new_frame_received.connect(self.liveController_widefield.on_new_frame)
		self.streamHandler_widefield.image_to_display.connect(self.imageDisplay_widefield.enqueue)
		self.streamHandler_widefield.packet_image_to_write.connect(self.imageSaver_widefield.enqueue)
		self.imageDisplay_widefield.image_to_display.connect(self.imageDisplayWindow_widefield.display_image) # may connect streamHandler directly to imageDisplayWindow

		self.navigationController.xPos.connect(self.navigationWidget.label_Xpos.setNum)
		self.navigationController.yPos.connect(self.navigationWidget.label_Ypos.setNum)
		self.navigationController.zPos.connect(self.navigationWidget.label_Zpos.setNum)
		
		self.autofocusController.image_to_display.connect(self.imageDisplayWindow_widefield.display_image)
		
		self.multipointController.image_to_display.connect(self.imageDisplayWindow_widefield.display_image)
		self.multipointController.signal_current_configuration_spectrum.connect(self.liveControlWidget_spectrum.set_microscope_mode)
		self.multipointController.signal_current_configuration_widefield.connect(self.liveControlWidget_widefield.set_microscope_mode)
		self.multipointController.signal_current_channel.connect(self.set_the_current_tab)
		
		self.liveControlWidget_spectrum.signal_newExposureTime.connect(self.cameraSettingWidget_spectrum.set_exposure_time)
		self.liveControlWidget_spectrum.signal_newAnalogGain.connect(self.cameraSettingWidget_spectrum.set_analog_gain)
		self.liveControlWidget_spectrum.update_camera_settings()
		self.liveControlWidget_widefield.signal_newExposureTime.connect(self.cameraSettingWidget_widefield.set_exposure_time)
		self.liveControlWidget_widefield.signal_newAnalogGain.connect(self.cameraSettingWidget_widefield.set_analog_gain)
		self.liveControlWidget_widefield.update_camera_settings()
		self.liveControlWidgets = {}
		self.liveControlWidgets['Widefield'] = self.liveControlWidget_widefield
		self.liveControlWidgets['Spectrum'] = self.liveControlWidget_spectrum

		self.controlTabWidget.currentChanged.connect(self.update_the_current_tab)

		self.slidePositionController.signal_slide_loading_position_reached.connect(self.navigationWidget.slot_slide_loading_position_reached)
		self.slidePositionController.signal_slide_loading_position_reached.connect(self.multiPointWidget.disable_the_start_aquisition_button)
		self.slidePositionController.signal_slide_scanning_position_reached.connect(self.navigationWidget.slot_slide_scanning_position_reached)
		self.slidePositionController.signal_slide_scanning_position_reached.connect(self.multiPointWidget.enable_the_start_aquisition_button)
		# self.slidePositionController.signal_clear_slide.connect(self.navigationViewer.clear_slide)

		# reset the MCU
		self.microcontroller.reset()

		# reinitialize motor drivers and DAC (in particular for V2.1 driver board where PG is not functional)
		self.microcontroller.initialize_drivers()

		# configure the actuators
		self.microcontroller.configure_actuators()

		# retract the objective
		self.navigationController.home_z()
		# wait for the operation to finish
		t0 = time.time()
		while self.microcontroller.is_busy():
			time.sleep(0.005)
			if time.time() - t0 > 10:
				self.log.error('z homing timeout, the program will exit')
				sys.exit(1)
		self.log.info('objective retracted')

		# set encoder arguments
		# set axis pid control enable
		# only ENABLE_PID_X and HAS_ENCODER_X are both enable, can be enable to PID
		if HAS_ENCODER_X == True:
			self.navigationController.set_axis_PID_arguments(0, PID_P_X, PID_I_X, PID_D_X)
			self.navigationController.configure_encoder(0, (SCREW_PITCH_X_MM * 1000) / ENCODER_RESOLUTION_UM_X, ENCODER_FLIP_DIR_X)
			self.navigationController.set_pid_control_enable(0, ENABLE_PID_X)
		if HAS_ENCODER_Y == True:
			self.navigationController.set_axis_PID_arguments(1, PID_P_Y, PID_I_Y, PID_D_Y)
			self.navigationController.configure_encoder(1, (SCREW_PITCH_Y_MM * 1000) / ENCODER_RESOLUTION_UM_Y, ENCODER_FLIP_DIR_Y)
			self.navigationController.set_pid_control_enable(1, ENABLE_PID_Y)
		if HAS_ENCODER_Z == True:
			self.navigationController.set_axis_PID_arguments(2, PID_P_Z, PID_I_Z, PID_D_Z)
			self.navigationController.configure_encoder(2, (SCREW_PITCH_Z_MM * 1000) / ENCODER_RESOLUTION_UM_Z, ENCODER_FLIP_DIR_Z)
			self.navigationController.set_pid_control_enable(2, ENABLE_PID_Z)

		time.sleep(0.5)

		# homing, set zero and set software limit
		self.navigationController.set_x_limit_pos_mm(100)
		self.navigationController.set_x_limit_neg_mm(-100)
		self.navigationController.set_y_limit_pos_mm(100)
		self.navigationController.set_y_limit_neg_mm(-100)
		self.log.info("start homing")
		self.slidePositionController.move_to_slide_scanning_position()
		while self.slidePositionController.slide_scanning_position_reached == False:
			time.sleep(0.005)
		self.log.info("homing finished")
		self.navigationController.set_x_limit_pos_mm(SOFTWARE_POS_LIMIT.X_POSITIVE)
		self.navigationController.set_x_limit_neg_mm(SOFTWARE_POS_LIMIT.X_NEGATIVE)
		self.navigationController.set_y_limit_pos_mm(SOFTWARE_POS_LIMIT.Y_POSITIVE)
		self.navigationController.set_y_limit_neg_mm(SOFTWARE_POS_LIMIT.Y_NEGATIVE)

		# set output's gains
		div = 1 if OUTPUT_GAINS.REFDIV is True else 0
		gains  = OUTPUT_GAINS.CHANNEL0_GAIN << 0
		gains += OUTPUT_GAINS.CHANNEL1_GAIN << 1
		gains += OUTPUT_GAINS.CHANNEL2_GAIN << 2
		gains += OUTPUT_GAINS.CHANNEL3_GAIN << 3
		gains += OUTPUT_GAINS.CHANNEL4_GAIN << 4
		gains += OUTPUT_GAINS.CHANNEL5_GAIN << 5
		gains += OUTPUT_GAINS.CHANNEL6_GAIN << 6
		gains += OUTPUT_GAINS.CHANNEL7_GAIN << 7
		self.microcontroller.configure_dac80508_refdiv_and_gain(div, gains)

		# set illumination intensity factor
		global ILLUMINATION_INTENSITY_FACTOR
		self.microcontroller.set_dac80508_scaling_factor_for_illumination(ILLUMINATION_INTENSITY_FACTOR)

		# set software limit
		self.navigationController.set_x_limit_pos_mm(SOFTWARE_POS_LIMIT.X_POSITIVE)
		self.navigationController.set_x_limit_neg_mm(SOFTWARE_POS_LIMIT.X_NEGATIVE)
		self.navigationController.set_y_limit_pos_mm(SOFTWARE_POS_LIMIT.Y_POSITIVE)
		self.navigationController.set_y_limit_neg_mm(SOFTWARE_POS_LIMIT.Y_NEGATIVE)
		self.navigationController.set_z_limit_pos_mm(SOFTWARE_POS_LIMIT.Z_POSITIVE)

		# Move to cached position
		if HOMING_ENABLED_X and HOMING_ENABLED_Y and HOMING_ENABLED_Z:
			self.navigationController.move_to_cached_position()
			self.waitForMicrocontroller()

	def update_the_current_tab(self,idx):
		print('current tab is ' + self.controlTabWidget.tabText(idx))
		if self.controlTabWidget.tabText(idx) == 'Spectrum':
			self.liveControlWidget_spectrum .update_DACs()
		elif self.controlTabWidget.tabText(idx) == 'Widefield':
			self.liveControlWidget_widefield.update_DACs()

	def set_the_current_tab(self,channel):
		# self.controlTabWidget.setCurrentIndex()
		self.controlTabWidget.setCurrentWidget(self.controlTabWidget.findChild(QWidget,channel))
		QApplication.processEvents()
		# to be fixed - the above has not effect on the display
		self.liveControlWidgets[channel].update_DACs()
		print('set the current tab to ' + channel)

	def closeEvent(self, event):
		self.navigationController.cache_current_position()

		event.accept()
		# self.softwareTriggerGenerator.stop() @@@ => 
		self.liveController_spectrum.stop_live()
		self.camera_spectrometer.close()
		self.imageSaver.close()
		self.imageDisplay.close()
		self.imageDisplayWindow_spectrum.close()
		self.spectrumDisplayWindow.close()

		self.liveController_widefield.stop_live()
		self.camera_widefield.close()
		self.imageSaver_widefield.close()
		self.imageDisplay_widefield.close()
		self.imageDisplayWindow_widefield.close()
		if SINGLE_WINDOW == False:
			self.displayWindow.close()

		self.microcontroller.analog_write_onboard_DAC(0,0)
		self.microcontroller.analog_write_onboard_DAC(1,0)
		self.microcontroller.close()

	def waitForMicrocontroller(self, timeout=5.0, error_message=None):
		try:
			self.microcontroller.wait_till_operation_is_completed(timeout)
		except TimeoutError as e:
			self.log.error(error_message or "Microcontroller operation timed out!")
			raise e