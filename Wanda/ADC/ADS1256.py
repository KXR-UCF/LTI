import RPi.GPIO as GPIO
import spidev
import time

# gain channel
GAIN_E = {'GAIN_1' : 0, # GAIN   1
          'GAIN_2' : 1,	# GAIN   2
          'GAIN_4' : 2,	# GAIN   4
          'GAIN_8' : 3,	# GAIN   8
          'GAIN_16' : 4,# GAIN  16
          'GAIN_32' : 5,# GAIN  32
          'GAIN_64' : 6,# GAIN  64
                 }

# data rate
DRATE_E = {'30000SPS' : 0xF0, # reset the default values
           '15000SPS' : 0xE0,
           '7500SPS' : 0xD0,
           '3750SPS' : 0xC0,
           '2000SPS' : 0xB0,
           '1000SPS' : 0xA1,
           '500SPS' : 0x92,
           '100SPS' : 0x82,
           '60SPS' : 0x72,
           '50SPS' : 0x63,
           '30SPS' : 0x53,
           '25SPS' : 0x43,
           '15SPS' : 0x33,
           '10SPS' : 0x20,
           '5SPS' : 0x13,
           '2d5SPS' : 0x03
                  }

# registration definition
REG_E = {'REG_STATUS' : 0,  # x1H
         'REG_MUX' : 1,     # 01H
         'REG_ADCON' : 2,   # 20H
         'REG_DRATE' : 3,   # F0H
         'REG_IO' : 4,      # E0H
         'REG_OFC0' : 5,    # xxH
         'REG_OFC1' : 6,    # xxH
         'REG_OFC2' : 7,    # xxH
         'REG_FSC0' : 8,    # xxH
         'REG_FSC1' : 9,    # xxH
         'REG_FSC2' : 10,   # xxH
        }

# command definition
CMD = {'CMD_WAKEUP' : 0x00,     # Completes SYNC and Exits Standby Mode 0000  0000 (00h)
       'CMD_RDATA' : 0x01,      # Read Data 0000  0001 (01h)
       'CMD_RDATAC' : 0x03,     # Read Data Continuously 0000   0011 (03h)
       'CMD_SDATAC' : 0x0F,     # Stop Read Data Continuously 0000   1111 (0Fh)
       'CMD_RREG' : 0x10,       # Read from REG rrr 0001 rrrr (1xh)
       'CMD_WREG' : 0x50,       # Write to REG rrr 0101 rrrr (5xh)
       'CMD_SELFCAL' : 0xF0,    # Offset and Gain Self-Calibration 1111    0000 (F0h)
       'CMD_SELFOCAL' : 0xF1,   # Offset Self-Calibration 1111    0001 (F1h)
       'CMD_SELFGCAL' : 0xF2,   # Gain Self-Calibration 1111    0010 (F2h)
       'CMD_SYSOCAL' : 0xF3,    # System Offset Calibration 1111   0011 (F3h)
       'CMD_SYSGCAL' : 0xF4,    # System Gain Calibration 1111    0100 (F4h)
       'CMD_SYNC' : 0xFC,       # Synchronize the A/D Conversion 1111   1100 (FCh)
       'CMD_STANDBY' : 0xFD,    # Begin Standby Mode 1111   1101 (FDh)
       'CMD_RESET' : 0xFE,      # Reset to Power-Up Values 1111   1110 (FEh)
      }

SPI = spidev.SpiDev(0, 0)
SPI.max_speed_hz = 500000  # 500 kHz


class ADS1256:
    def __init__(self, rst_pin, cs_pin, drdy_pin):
        self.rst_pin = rst_pin
        self.cs_pin = cs_pin
        self.drdy_pin = drdy_pin
        # this was missing from the original library, without this, the mode would not be set by the setMode since it was not a parameter of the class
        self.scan_mode = 1 # currently set as default: 1=differential mode

    # raspberry pi pin managment
    def digital_write(self, pin, value):
        GPIO.output(pin, value)

    def digital_read(self, pin):
        return GPIO.input(self.drdy_pin)

    def delay_ms(self, delaytime):
        time.sleep(delaytime // 1000.0)

    def spi_writebyte(self, data):
        SPI.writebytes(data)
        
    def spi_readbytes(self, reg):
        return SPI.readbytes(reg)
        
    def module_init(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.rst_pin, GPIO.OUT)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        #GPIO.setup(DRDY_PIN, GPIO.IN)
        GPIO.setup(self.drdy_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # SPI.max_speed_hz = 20000
        SPI.mode = 0b01
        return 0

    def module_exit(self):
        GPIO.cleanup()
        SPI.close()

    # Hardware reset
    def reset(self):
        self.digital_write(self.rst_pin, GPIO.HIGH)
        self.delay_ms(200)
        self.digital_write(self.rst_pin, GPIO.LOW)
        self.delay_ms(200)
        self.digital_write(self.rst_pin, GPIO.HIGH)
    
    def writeCmd(self, reg):
        self.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        self.spi_writebyte([reg])
        self.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
    
    def writeReg(self, reg, data):
        self.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        self.spi_writebyte([CMD['CMD_WREG'] | reg, 0x00, data])
        self.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
        
    def readData(self, reg):
        self.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        self.spi_writebyte([CMD['CMD_RREG'] | reg, 0x00])
        data = self.spi_readbytes(1)
        self.digital_write(self.cs_pin, GPIO.HIGH)#cs 1

        return data
        
    def waitDRDY(self):
        for i in range(0,400000,1):
            if(self.digital_read(self.drdy_pin) == 0):
                
                break
        if(i >= 400000):
            print ("Time Out ...\r\n")
        
        
    def readChipID(self):
        self.waitDRDY()
        id = self.readData(REG_E['REG_STATUS'])
        id = id[0] >> 4
        # print 'ID',id
        return id
        
    #The configuration parameters of ADC, gain and data rate
    def configADC(self, gain, drate):
        self.waitDRDY()
        buf = [0,0,0,0,0,0,0,0]
        buf[0] = (0<<3) | (1<<2) | (0<<1)
        buf[1] = 0x08
        buf[2] = (0<<5) | (0<<3) | (gain<<0)
        buf[3] = drate
        
        self.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        self.spi_writebyte([CMD['CMD_WREG'] | 0, 0x03])
        self.spi_writebyte(buf)
        
        self.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
        self.delay_ms(1) 
        self.gain = 2 ** gain



    def setChannel(self, Channel):
        if Channel > 7:
            return 0
        self.writeReg(REG_E['REG_MUX'], (Channel<<4) | (1<<3))


    def setDiffChannel(self, Channel):
        if Channel == 0:
            self.writeReg(REG_E['REG_MUX'], (0 << 4) | 1) 	#DiffChannel  AIN0-AIN1
        elif Channel == 1:
            self.writeReg(REG_E['REG_MUX'], (2 << 4) | 3) 	#DiffChannel   AIN2-AIN3
        elif Channel == 2:
            self.writeReg(REG_E['REG_MUX'], (4 << 4) | 5) 	#DiffChannel    AIN4-AIN5
        elif Channel == 3:
            self.writeReg(REG_E['REG_MUX'], (6 << 4) | 7) 	#DiffChannel   AIN6-AIN7


    # sets mode
    # 0: single ended mode
    # 1: differential mode
    # default: 1
    def setMode(self, Mode):
        self.scan_mode = Mode


    def init(self):
        if (self.module_init() != 0):
            return -1
        self.reset()
        id = self.readChipID()
        if id == 3 :
            print("ID Read success  ")
        else:
            print("ID Read failed   ")
            return -1
        self.configADC(GAIN_E['GAIN_1'], DRATE_E['30000SPS'])
        return 0
        
    def read_ADC_Data(self):
        self.waitDRDY()
        self.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        self.spi_writebyte([CMD['CMD_RDATA']])
        self.delay_ms(10)

        buf = self.spi_readbytes(3)
        self.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
        read = (buf[0]<<16) & 0xff0000
        read |= (buf[1]<<8) & 0xff00
        read |= (buf[2]) & 0xff
        if (read & 0x800000):
            read &= 0xFF000000
        return read
 
    def getChannelValue(self, Channel):
        if(self.scan_mode == 0):# 0  Single-ended input  8 channel1 Differential input  4 channe
            if(Channel>=8):
                return 0
            # print(self.scan_mode)
            self.setChannel(Channel)
            self.writeCmd(CMD['CMD_SYNC'])
            # self.delay_ms(10)
            self.writeCmd(CMD['CMD_WAKEUP'])
            # self.delay_ms(200)
            Value = self.read_ADC_Data()
        else:
            if(Channel>=4):
                return 0
            self.setDiffChannel(Channel)
            self.writeCmd(CMD['CMD_SYNC'])
            self.delay_ms(10)
            self.writeCmd(CMD['CMD_WAKEUP'])
            self.delay_ms(10)
            Value = self.read_ADC_Data()
        return Value
    
    def getChannelVoltage(self, channel, Vref=2.5):
        value = self.getChannelValue(channel)
        voltage = (value * 5.0 / 0x7fffff) / self.gain
        return voltage
        
    # returns all values by channel
    # automatically handles differential mode through getChannelValue
    def getAllValues(self):
        ADC_Value = [0,0,0,0,0,0,0,0]
        for i in range(0,8,1):
            ADC_Value[i] = self.getChannelValue(i)
        return ADC_Value
    
    def getAllVoltages(self):
        ADC_Voltage = [0,0,0,0,0,0,0,0]
        for i in range(0,8,1):
            ADC_Voltage[i] = self.getChannelVoltage(i)
        return ADC_Voltage
### END OF FILE ###

