import wx
import sys
import threading
import serial.tools.list_ports
import os
import esptool
from serial import SerialException
from esptool import FatalError
import argparse

# this class credit marcelstoer
# See discussion at http://stackoverflow.com/q/41101897/131929
class RedirectText:
    def __init__(self, text_ctrl):
        self.out = text_ctrl
        self.pending_backspaces = 0

    def write(self, string):
        new_string = ""
        number_of_backspaces = 0
        for c in string:
            if c == "\b":
                number_of_backspaces += 1
            else:
                new_string += c

        if self.pending_backspaces > 0:
            # current value minus pending backspaces plus new string
            new_value = self.out.GetValue()[:-1 * self.pending_backspaces] + new_string
            wx.CallAfter(self.out.SetValue, new_value)
        else:
            wx.CallAfter(self.out.AppendText, new_string)

        self.pending_backspaces = number_of_backspaces

    def flush(self):
        None

class dfuTool(wx.Frame):

    ################################################################
    #                         INIT TASKS                           #
    ################################################################
    def __init__(self, parent, title):
        super(dfuTool, self).__init__(parent, title=title)

        self.baudrates = ['9600', '57600', '74880', '115200', '230400', '460800', '921600']
        self.SetSize(800,550)
        self.SetMinSize(wx.Size(800,500))
        self.Centre()
        self.initUI()
        self.initFlags()
        print('Doayee ESP32 Firmware Flasher')
        print('--------------------------------------------')

    def initUI(self):
        '''Runs on application start to build the GUI'''

        self.mainPanel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        ################################################################
        #                   BEGIN SERIAL OPTIONS GUI                   #
        ################################################################
        self.serialPanel = wx.Panel(self.mainPanel)
        serialhbox = wx.BoxSizer(wx.HORIZONTAL)

        self.serialtext = wx.StaticText(self.serialPanel,label = "Serial Port:", style = wx.ALIGN_CENTRE)
        serialhbox.Add(self.serialtext,0.5,wx.ALL|wx.ALIGN_CENTER_VERTICAL,20)

        devices = self.list_serial_devices()
        self.serialChoice = wx.Choice(self.serialPanel, choices=devices)
        self.serialChoice.Bind(wx.EVT_CHOICE, self.on_serial_list_select)
        serialhbox.Add(self.serialChoice,3,wx.ALL|wx.ALIGN_CENTER_VERTICAL,20)

        self.scanButton = wx.Button(parent=self.serialPanel, label='Rescan Ports')
        self.scanButton.Bind(wx.EVT_BUTTON, self.on_serial_scan_request)
        serialhbox.Add(self.scanButton,2,wx.ALL|wx.ALIGN_CENTER_VERTICAL,20)

        self.serialAutoCheckbox = wx.CheckBox(parent=self.serialPanel,label="Auto-detect (slow)")
        self.serialAutoCheckbox.Bind(wx.EVT_CHECKBOX,self.on_serial_autodetect_check)
        serialhbox.Add(self.serialAutoCheckbox,2,wx.ALL|wx.ALIGN_CENTER_VERTICAL,20)

        vbox.Add(self.serialPanel,1, wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                   BEGIN BAUD RATE GUI                        #
        ################################################################
        self.baudPanel = wx.Panel(self.mainPanel)
        baudhbox = wx.BoxSizer(wx.HORIZONTAL)

        self.baudtext = wx.StaticText(self.baudPanel,label = "Baud Rate:", style = wx.ALIGN_CENTRE)
        baudhbox.Add(self.baudtext,0.5,wx.ALL,20)

        # create a button for each baud rate
        for index, baud in enumerate(self.baudrates):
            # use the first button to initialise the group
            style = wx.RB_GROUP if index == 0 else 0

            baudChoice = wx.RadioButton(self.baudPanel,style=style,label=baud, name=baud)
            baudChoice.Bind(wx.EVT_RADIOBUTTON, self.on_baud_selected)
            baudChoice.baudrate = baud
            baudhbox.Add(baudChoice, 1, wx.TOP | wx.BOTTOM |wx.EXPAND, 20)

            # set the default up
            if index == len(self.baudrates) - 1:
                baudChoice.SetValue(True)
                self.ESPTOOLARG_BAUD = baudChoice.baudrate

        vbox.Add(self.baudPanel,1, wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                   BEGIN ERASE BUTTON GUI                     #
        ################################################################
        self.eraseButton = wx.Button(parent=self.mainPanel, label='Erase ESP')
        self.eraseButton.Bind(wx.EVT_BUTTON, self.on_erase_button)

        self.eraseWarning= wx.StaticText(self.mainPanel,label = "WARNING: Erasing is not mandatory to flash a new app, but if you do, you must reflash ALL 3 files.", style = wx.ALIGN_LEFT)

        vbox.Add(self.eraseButton,1, wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        vbox.Add(self.eraseWarning,0.1,wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, 20 )
        ################################################################
        #                   BEGIN APP DFU FILE GUI                     #
        ################################################################
        self.appDFUpanel = wx.Panel(self.mainPanel)
        self.appDFUpanel.SetBackgroundColour('white')
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.appDFUCheckbox = wx.CheckBox(parent=self.appDFUpanel,label="Flash App at 0x10000                ")
        self.appDFUCheckbox.Bind(wx.EVT_CHECKBOX,self.on_appFlash_check)
        self.appDFUCheckbox.SetValue(True)
        self.appDFUCheckbox.Disable()
        hbox.Add(self.appDFUCheckbox,1,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.app_pathtext = wx.StaticText(self.appDFUpanel,label = "No File Selected", style = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        hbox.Add(self.app_pathtext,5,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.browseButton = wx.Button(parent=self.appDFUpanel, label='Browse...')
        self.browseButton.Bind(wx.EVT_BUTTON, self.on_app_browse_button)
        hbox.Add(self.browseButton, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 10)

        vbox.Add(self.appDFUpanel,1,wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                BEGIN PARTITIONS DFU FILE GUI                 #
        ################################################################
        self.partitionDFUpanel = wx.Panel(self.mainPanel)
        self.partitionDFUpanel.SetBackgroundColour('white')
        partitionhbox = wx.BoxSizer(wx.HORIZONTAL)

        self.partitionDFUCheckbox = wx.CheckBox(parent=self.partitionDFUpanel,label="Flash Partition Table at 0x8000")
        self.partitionDFUCheckbox.Bind(wx.EVT_CHECKBOX,self.on_partitionFlash_check)
        partitionhbox.Add(self.partitionDFUCheckbox,1,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.partition_pathtext = wx.StaticText(self.partitionDFUpanel,label = "No File Selected", style = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        partitionhbox.Add(self.partition_pathtext,5,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.browseButton = wx.Button(parent=self.partitionDFUpanel, label='Browse...')
        self.browseButton.Bind(wx.EVT_BUTTON, self.on_partition_browse_button)
        partitionhbox.Add(self.browseButton, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 10)

        vbox.Add(self.partitionDFUpanel,1,wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                BEGIN BOOTLOADER DFU FILE GUI                 #
        ################################################################
        self.bootloaderDFUpanel = wx.Panel(self.mainPanel)
        self.bootloaderDFUpanel.SetBackgroundColour('white')
        bootloaderhbox = wx.BoxSizer(wx.HORIZONTAL)

        self.bootloaderDFUCheckbox = wx.CheckBox(parent=self.bootloaderDFUpanel,label="Flash Bootloader at 0x1000      ")
        self.bootloaderDFUCheckbox.Bind(wx.EVT_CHECKBOX,self.on_bootloaderFlash_check)
        bootloaderhbox.Add(self.bootloaderDFUCheckbox,1,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.bootloader_pathtext = wx.StaticText(self.bootloaderDFUpanel,label = "No File Selected", style = wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        bootloaderhbox.Add(self.bootloader_pathtext,5,wx.ALL|wx.ALIGN_CENTER_VERTICAL,10)

        self.browseButton = wx.Button(parent=self.bootloaderDFUpanel, label='Browse...')
        self.browseButton.Bind(wx.EVT_BUTTON, self.on_bootloader_browse_button)
        bootloaderhbox.Add(self.browseButton, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 10)

        vbox.Add(self.bootloaderDFUpanel,1,wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                   BEGIN FLASH BUTTON GUI                     #
        ################################################################
        self.flashButton = wx.Button(parent=self.mainPanel, label='Flash')
        self.flashButton.Bind(wx.EVT_BUTTON, self.on_flash_button)

        vbox.Add(self.flashButton,1, wx.LEFT|wx.RIGHT|wx.EXPAND, 20)
        ################################################################
        #                   BEGIN CONSOLE OUTPUT GUI                   #
        ################################################################
        self.consolePanel = wx.TextCtrl(self.mainPanel, style=wx.TE_MULTILINE|wx.TE_READONLY)
        sys.stdout = RedirectText(self.consolePanel)

        vbox.Add(self.consolePanel,5, wx.ALL|wx.EXPAND, 20)
        ################################################################
        #                ASSOCIATE PANELS TO SIZERS                    #
        ################################################################
        self.appDFUpanel.SetSizer(hbox)
        self.partitionDFUpanel.SetSizer(partitionhbox)
        self.bootloaderDFUpanel.SetSizer(bootloaderhbox)
        self.serialPanel.SetSizer(serialhbox)
        self.baudPanel.SetSizer(baudhbox)
        self.mainPanel.SetSizer(vbox)

    def initFlags(self):
        '''Initialises the flags used to control the program flow'''
        self.ESPTOOL_BUSY = False

        self.ESPTOOLARG_AUTOSERIAL = False
        self.ESPTOOLARG_SERIALPORT = self.serialChoice.GetString(self.serialChoice.GetSelection())
        self.ESPTOOLARG_BAUD = self.ESPTOOLARG_BAUD # this default is regrettably loaded as part of the initUI process
        self.ESPTOOLARG_APPPATH = None
        self.ESPTOOLARG_PARTITIONPATH = None
        self.ESPTOOLARG_BOOTLOADERPATH = None
        self.ESPTOOLARG_APPFLASH = True
        self.ESPTOOLARG_PARTITIONFLASH = False
        self.ESPTOOLARG_BOOTLOADERFLASH = False

        self.APPFILE_SELECTED = False
        self.PARTITIONFILE_SELECTED = False
        self.BOOTLOADERFILE_SELECTED = False

        self.ESPTOOLMODE_ERASE = False
        self.ESPTOOLMODE_FLASH = False

        self.ESPTOOL_ERASE_USED = False

    ################################################################
    #                      UI EVENT HANDLERS                       #
    ################################################################
    def on_serial_scan_request(self, event):
        # disallow if automatic serial port is chosen
        if self.ESPTOOLARG_AUTOSERIAL:
            print('disable automatic mode first')
            return

        # repopulate the serial port choices and update the selected port
        print('rescanning serial ports...')
        devices = self.list_serial_devices()
        self.serialChoice.Clear()
        for device in devices:
            self.serialChoice.Append(device)
        self.ESPTOOLARG_SERIALPORT = self.serialChoice.GetString(self.serialChoice.GetSelection())
        print('serial choices updated')

    def on_serial_list_select(self,event):
        port = self.serialChoice.GetString(self.serialChoice.GetSelection())
        self.ESPTOOLARG_SERIALPORT = self.serialChoice.GetString(self.serialChoice.GetSelection())
        print('you chose '+port)

    def on_serial_autodetect_check(self,event):
        self.ESPTOOLARG_AUTOSERIAL = self.serialAutoCheckbox.GetValue()

        if self.ESPTOOLARG_AUTOSERIAL:
            self.serialChoice.Clear()
            self.serialChoice.Append('Automatic')
        else:
            self.on_serial_scan_request(event)

    def on_baud_selected(self,event):
        selection = event.GetEventObject()
        self.ESPTOOLARG_BAUD = selection.baudrate
        print('baud set to '+selection.baudrate)

    def on_erase_button(self, event):
        if self.ESPTOOL_BUSY:
            print('currently busy')
            return
        self.ESPTOOLMODE_ERASE = True
        self.ESPTOOL_ERASE_USED = True
        t = threading.Thread(target=self.esptoolRunner, daemon=True)
        t.start()

    def on_appFlash_check(self, event):
        self.ESPTOOLARG_APPFLASH = self.appDFUCheckbox.GetValue()

    def on_partitionFlash_check(self, event):
        self.ESPTOOLARG_PARTITIONFLASH = self.partitionDFUCheckbox.GetValue()

    def on_bootloaderFlash_check(self, event):
        self.ESPTOOLARG_BOOTLOADERFLASH = self.bootloaderDFUCheckbox.GetValue()

    def on_app_browse_button(self, event):
        with wx.FileDialog(self, "Open", "", "","*.bin", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.APPFILE_SELECTED = True

        self.app_pathtext.SetLabel(os.path.abspath(path))
        self.ESPTOOLARG_APPPATH=os.path.abspath(path)

    def on_partition_browse_button(self, event):
        with wx.FileDialog(self, "Open", "", "","*.bin", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.PARTITIONFILE_SELECTED = True

        self.partition_pathtext.SetLabel(os.path.abspath(path))
        self.ESPTOOLARG_PARTITIONPATH=os.path.abspath(path)

    def on_bootloader_browse_button(self, event):
        with wx.FileDialog(self, "Open", "", "","*.bin", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            path = fileDialog.GetPath()
            self.BOOTLOADERFILE_SELECTED = True

        self.bootloader_pathtext.SetLabel(os.path.abspath(path))
        self.ESPTOOLARG_BOOTLOADERPATH=os.path.abspath(path)

    def on_flash_button(self, event):
        if self.ESPTOOL_BUSY:
            print('currently busy')
            return
        # handle cases where a flash has been requested but no file provided
        elif self.ESPTOOLARG_APPFLASH & ~self.APPFILE_SELECTED:
            print('no app selected for flash')
            return
        elif self.ESPTOOLARG_PARTITIONFLASH & ~self.PARTITIONFILE_SELECTED:
            print('no partition table selected for flash')
            return
        elif self.ESPTOOLARG_BOOTLOADERFLASH & ~self.BOOTLOADERFILE_SELECTED:
            print('no bootloader selected for flash')
            return
        else:
            # if the erase_flash has been used but we have not elected to upload all the required files
            if self.ESPTOOL_ERASE_USED & (~self.ESPTOOLARG_APPFLASH | ~self.ESPTOOLARG_PARTITIONFLASH | ~self.ESPTOOLARG_BOOTLOADERFLASH):
                dialog = wx.MessageDialog(self.mainPanel, 'DoayeeESP32DFU detected use of \"Erase ESP\", which means you should reflash all files. Are you sure you want to continue? ','Warning',wx.YES_NO|wx.ICON_EXCLAMATION)
                ret = dialog.ShowModal()

                if ret == wx.ID_NO:
                    return

            # if we're uploading everything, clear the fact that erase_flash has been used
            if self.ESPTOOLARG_APPFLASH & self.ESPTOOLARG_PARTITIONFLASH & self.ESPTOOLARG_BOOTLOADERFLASH:
                self.ESPTOOL_ERASE_USED = False

            self.ESPTOOLMODE_FLASH = True
            t = threading.Thread(target=self.esptoolRunner, daemon=True)
            t.start()

    ################################################################
    #                      MISC FUNCTIONS                          #
    ################################################################
    def list_serial_devices(self):
        ports = serial.tools.list_ports.comports()
        ports.sort()
        devices = []
        for port in ports:
            devices.append(port.device)
        return devices

    ################################################################
    #                    ESPTOOL FUNCTIONS                         #
    ################################################################
    def esptool_cmd_builder(self):
        '''Build the command that we would give esptool on the CLI'''
        cmd = ['--baud',self.ESPTOOLARG_BAUD]

        if self.ESPTOOLARG_AUTOSERIAL == False:
            cmd = cmd + ['--port',self.ESPTOOLARG_SERIALPORT]

        if self.ESPTOOLMODE_ERASE:
            cmd.append('erase_flash')
        elif self.ESPTOOLMODE_FLASH:
            cmd.append('write_flash')
            if self.ESPTOOLARG_BOOTLOADERFLASH:
                cmd.append('0x1000')
                cmd.append(self.ESPTOOLARG_BOOTLOADERPATH)
            if self.ESPTOOLARG_APPFLASH:
                cmd.append('0x10000')
                cmd.append(self.ESPTOOLARG_APPPATH)
            if self.ESPTOOLARG_PARTITIONFLASH:
                cmd.append('0x8000')
                cmd.append(self.ESPTOOLARG_PARTITIONPATH)

        return cmd

    def esptoolRunner(self):
        '''Handles the interaction with esptool'''
        self.ESPTOOL_BUSY = True

        cmd = self.esptool_cmd_builder()
        try:
            esptool.main(cmd)
            print('esptool execution completed')
        except esptool.FatalError as e:
            print(e)
            pass
        except serial.SerialException as e:
            print(e)
            pass
        except:
            print('unexpected error, maybe you chose invalid files, or files which overlap')
            pass

        self.ESPTOOL_BUSY = False
        self.ESPTOOLMODE_ERASE = False
        self.ESPTOOLMODE_FLASH = False


def main():

    app = wx.App()
    window = dfuTool(None, title='Doayee ESP32 DFU Tool')
    window.Show()

    app.MainLoop()

if __name__ == '__main__':
    main()
