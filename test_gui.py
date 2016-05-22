
import wx
import serial
import os
import string
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
import matplotlib.pyplot as plt
import datetime
import sseclient
from sseclient import SSEClient # server side events
# https://pypi.python.org/pypi/sseclient/0.0.8
import threading
from time import gmtime, strftime

API_PREFIX = 'https://api.particle.io'
API_VERSION = '/v1/'
ack_token = 'blank'


readingsPerMsg = 20
scans = []
sets = []

class eventThread(threading.Thread):
	def run(self):
		#url = API_PREFIX + API_VERSION + 'devices/%s/events?access_token=%s' % (frame.currentDeviceID, ack_token)
		#url = API_PREFIX + API_VERSION + 'devices/270046001247343432313031/events?access_token=%s' % ack_token
		url = API_PREFIX + API_VERSION + 'devices/events?access_token=%s' % ack_token
		#response = self.session.get(url)


		scanCount = 0;

		vals = []

		messages = SSEClient(url)
		for msg in messages:

			if (msg.event[0:4] != 'mess'):
				frame.logger.AppendText("Event: %s: %s\n" % (msg.event, msg.data))

			if (msg.event[0:4] == 'wake'):
				print 'msg.id: %s' % msg.id
				print 'msg.event: %s' % msg.event
				print msg.data
				print '\n'

			if (msg.event == 'wake/scan'):
				scanCount = scanCount + 1
				index = 9
				print 'wake/scan msg received #%d\n\r' % scanCount
				for x in range (0, readingsPerMsg):
					mychar = '%c%c.%c' % (msg.data[index], msg.data[index+1], msg.data[index+2])
					#print '%f\n\r' % float(mychar)
					vals.append(float(mychar))
					index = index + 3

				if (scanCount == 5):
					print 'reset scan count to 0'
					scanCount = 0;
					tupl = vals, strftime("%Y-%m-%d %H:%M:%S", gmtime())
					sets.append(tupl)
					vals = []


class MyGUI(wx.Frame):

	def __init__(self, parent, title):
		
		ack_token = input('enter token: ')
		# create a non-resizable frame
		#wx.Frame.__init__(self, parent, title=title, style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
		wx.Frame.__init__(self, parent, title=title, size=(1000,800))

		# A status bar displays current stopwatch mode.
		self.CreateStatusBar()
		self.SetStatusText("Ready.")

		self.currentDeviceID = -1
		self.currentDeviceName = 'Nonya'

		# create read only text box for logging status/data
		self.logger = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)

		# create editable text box for filename entry
		self.filenameText = wx.TextCtrl(self, wx.ID_ANY)

		# add buttons
		StatusButton = wx.Button(self, wx.ID_ANY, label = "Get Status")
		PlotButton = wx.Button(self, wx.ID_ANY, label = "Plot")
		DownloadFileButton = wx.Button(self, wx.ID_ANY, label = "Download File")
		StartLifetestButton = wx.Button(self, wx.ID_ANY, label = "Start Lifetest")
		StartRechargeButton = wx.Button(self, wx.ID_ANY, label = "Start Recharge")
		ChangeFilenameButton = wx.Button(self, wx.ID_ANY, label = "Change Filename")
		EventStreamButton = wx.Button(self, wx.ID_ANY, label = "EventStream")

		self.deviceIDList = ['34002b001247343431373336',
							'270046001247343432313031',
							'28002e000647343432313031',
							'270020001747343432313031',
							'260042001247343432313031',
							'35003f001247343431373336',
							'1d002a001747343432313031',
							'25002b001147343431373336']

		self.deviceNameList = ['FP42-1',
							   'FP42-3',
							   'FP42-4',
							   'FP42-6',
							   'FP42-8',
							   'FP42-10',
							   'FP43-2',
							   'FP43-3']

		deviceNameComboBox = wx.ComboBox(self, wx.ID_ANY, choices=self.deviceNameList, style=wx.CB_READONLY)

		deviceNameSizer = wx.BoxSizer(wx.VERTICAL)
		deviceNameText = wx.StaticText(self, wx.ID_ANY, label="Device Name")
		deviceNameSizer.Add(deviceNameText, 0, wx.ALL)
		deviceNameSizer.Add(deviceNameComboBox, 0, wx.ALL)

		filenameSizer = wx.BoxSizer(wx.VERTICAL)
		filenameTextSizer = wx.StaticText(self, wx.ID_ANY, label="Choose Filename")

		filenameSizer.Add(filenameTextSizer, 0, wx.ALL)
		filenameSizer.Add(self.filenameText, 0, wx.ALL)

		gridSizer = wx.GridSizer(rows = 3, cols = 4, hgap = 10, vgap = 10)

		# add objects to overall grid sizer object
		gridSizer.Add(deviceNameSizer, 0, wx.ALL)
		gridSizer.Add(self.logger, 0, wx.EXPAND)
		gridSizer.Add(StatusButton, 0, wx.ALL)
		gridSizer.Add(PlotButton, 0, wx.ALL)
		gridSizer.Add(filenameSizer, 0, wx.ALL)
		gridSizer.Add(DownloadFileButton, 0, wx.ALL)
		gridSizer.Add(StartLifetestButton, 0, wx.ALL)
		gridSizer.Add(StartRechargeButton, 0, wx.ALL)
		gridSizer.Add(ChangeFilenameButton, 0, wx.ALL)
		gridSizer.Add(EventStreamButton, 0, wx.ALL)

		# http://stackoverflow.com/questions/6294726/setsizer-setsizerandfit-and-resizing-components
		self.SetSizer(gridSizer)


		# bind the event handlers to clicking of buttons
		self.Bind(wx.EVT_BUTTON, self.onStatusButton, StatusButton)
		self.Bind(wx.EVT_BUTTON, self.onPlotButton, PlotButton)
		self.Bind(wx.EVT_BUTTON, self.onDownloadFileButton, DownloadFileButton)
		self.Bind(wx.EVT_BUTTON, self.onStartLifetestButton, StartLifetestButton)
		self.Bind(wx.EVT_BUTTON, self.onStartRechargeButton, StartRechargeButton)
		self.Bind(wx.EVT_BUTTON, self.onChangeFilenameButton, ChangeFilenameButton)
		self.Bind(wx.EVT_BUTTON, self.onEventStreamButton, EventStreamButton)

		# bind clicking on combo boxes to combo box event handlers
		deviceNameComboBox.Bind(wx.EVT_COMBOBOX, self.deviceNameComboBoxHandler)

		# show the window
		self.Show(True)

		# start requests session for http access to device
		self.session = requests.session()

		# send token for access permission
		self.session.headers.update({'Authorization': "Bearer %s" % ack_token,})

	def onStatusButton(self, evt):
		print 'set len: %d\n\r' % len(sets)
		for i in range(len(sets)):
			out = sets[i]
			vol = out[0]
			title = out[1]
			plt1 = plt.figure(1,(10,10),60)
			plt.plot(vol)
			plt.xlabel('reading number')
			plt.ylabel('temperature (deg C)')
			plt.title(title)
			plt.grid(True, linewidth=3)
			#plt.show(block=False)
			plt.show()

		# self.logger.AppendText('Status Button clicked\n')
		# ret = self.function_call(self.currentDeviceID, "cmd", 'm')
		# if (ret["return_value"] < 0):
		# 	print 'cmd function call failed'
		# print ret["return_value"]

	def onDownloadFileButton(self, evt):

		if (self.currentDeviceID == -1):
			print 'select a device ID'
			return None

		filename = self.filenameText.GetValue()

		print 'filename is: %s' %filename

		savename = "D:/Wakee/LifeTesting/" + filename

		newfile = open(savename, 'w')

		ret = self.function_call(self.currentDeviceID, "dwnldFile", filename)

		if (ret["return_value"] < 0):
			print 'downloadFile function call failed'
			print ret["return_value"]
			return None

		cycles = []
		voltageBatt = []
		voltagePWRIn = []

		r = 1
		rowCount = 0
		#for i in range (0, 10):
		while (r == 1):
			ret = self.function_call(self.currentDeviceID, "rdFilDnld", "cmd")
			if(ret["return_value"] < 0):
				print 'readFileDownload functiona call failed'
				print ret["return_value"]
				r = 0
				break
			ret = self.get_variable(self.currentDeviceID, "str2")
			string = ret["result"]
			row = string.split(",")
			print row
			newfile.write(string)
			cycles.append(row[5])
			voltageBatt.append(row[6])
			voltagePWRIn.append(row[7])
			rowCount += 1

		newfile.close()

		ret = self.function_call(self.currentDeviceID, "closeFile", filename)
		print 'file close function call sent'
		if (ret["return_value"] < 0):
			print 'closeFile function call failed'
			print ret["return_value"]
			return None

		title = '%s PWR_IN and Battery Voltage' % self.currentDeviceName

		self.plot(voltageBatt, voltagePWRIn, title)

	def onPlotButton(self,evt):

		var1 = []
		var2 = []

		for d in xrange(0,60):
			var1.append(str(d))
			var2.append(str(d +2))

		self.plot(var1, var2, 'TEST DATA ONLY')

	def onStartLifetestButton(self, evt):
		ret = self.function_call(self.currentDeviceID, "cmd", 't')
		if (ret["return_value"] < 0):
			print 'cmd function call failed'
		print ret["return_value"]
		return None

	def onStartRechargeButton(self, evt):
		ret = self.function_call(self.currentDeviceID, "cmd", 'c')
		if (ret["return_value"] < 0):
			print 'downloadFile function call failed'
		print ret["return_value"]
		return None

	def onChangeFilenameButton(self, evt):
		filename = self.filenameText.GetValue()
		ret = self.function_call(self.currentDeviceID, "chgflnm", filename)
		if (ret["return_value"] < 0):
			print 'downloadFile function call failed'
		print ret["return_value"]
		return None

	def deviceNameComboBoxHandler(self, evt)	:
		self.currentDeviceName = self.deviceNameList[evt.GetSelection()]
		self.currentDeviceID = self.deviceIDList[evt.GetSelection()] # zero indexing
		self.filenameText.Clear()
		now = datetime.datetime.now()
		fp = self.deviceNameList[evt.GetSelection()]
		self.filenameText.AppendText("f%s%s%s%s%s.txt" % (fp[2],fp[3],fp[5],now.month,now.day))
		self.logger.AppendText('%s Device ID is %s\n' %(self.currentDeviceName, self.currentDeviceID))

	def plot(self, variable1, variable2, title):
		#plt1 = plt.subplot(121)
		plt1 = plt.figure(1,(10,10),60)
		plt.plot(variable1,'ro')
		plt.plot(variable2,'bo')
		plt.xlabel('Cycles')
		plt.ylabel('Voltage (V)')
		plt.title(title)
		plt.grid(True, linewidth=3)
		#plt.show(block=False)
		plt.show()

	def function_call(self, device_serial, function_name, arg):
		url = API_PREFIX + API_VERSION + 'devices/%s/%s' % (device_serial, function_name)
		response = self.session.post(url, data = {"arg":arg})
		if response.ok:
			return response.json()
		return None

	def get_variable(self, device_serial, variable_name):
		url = API_PREFIX + API_VERSION + 'devices/%s/%s' % (device_serial, variable_name)
		response = self.session.get(url)
		if response.ok and response.status_code == 200:
			return response.json()
		else:
			print 'get_variable ERROR response not ok or bad status code'
			return None

	def onEventStreamButton(self, evt):
		eventThread().start()
		# url = API_PREFIX + API_VERSION + 'devices/%s/events?access_token=%s' % (self.currentDeviceID, ack_token)
		# #response = self.session.get(url)
		#
		# messages = SSEClient(url)
		# for msg in messages:
		# 	print msg.data


app = wx.App(False)
frame = MyGUI(None,"Wake Python interface")


try:
	app.MainLoop()
except:
	exc_info = sys.exc_info()
	print 'failed on exception'
	input("press something...")
	raise
