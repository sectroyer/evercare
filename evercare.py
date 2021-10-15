#!/usr/bin/env python3
#   (c) 2021 sectroyer
#   License: GPLv3


from SLABHIDtoUART import *
import ctypes as ct, datetime

CMD_CLEAR = 0x52
CMD_GETDT = 0x23
CMD_GETREC1 = 0x25
CMD_GETREC2 = 0x26
CMD_INIT = 0x22
CMD_RECCNT = 0x2b
CMD_SETDT = 0x33
CMD_SN1 = 0x27
CMD_SN2 = 0x28

TYPE_GEN = 0
TYPE_AC = 1
TYPE_PC = 2
TYPE_QC = 3

class Measurment:
    def __init__(self):
        self.time = None
        self.value = 0
        self.code = 0
        self.conditions = 0
        self.type = TYPE_GEN
    def GetTimeLabel(self):
        if self.time.hour < 8:
            return "at night"
        elif self.time.hour > 7 and self.time.hour < 11:
            return "before breakfast"
        elif self.time.hour > 11 and self.time.hour < 14: 
            return "after breakfast"
        elif self.time.hour > 14 and self.time.hour < 17: 
            return "before dinner"
        elif self.time.hour > 17 and self.time.hour < 19: 
            return "after dinner"
        elif self.time.hour > 18 and self.time.hour < 20: 
            return "before supper"
        elif self.time.hour > 20: 
            return "after supper"
        return "other"

class Evercare(HidUartDevice):
    def Exec(self, cmd, args):
        buffer = [0]*8
        buffer[0]=0x51
        buffer[1]=cmd
        buffer[6]=0xa3
        for i in range(0,len(args)):
            buffer[2+i] = args[i];
        for j in range(0,len(buffer)-1):
            buffer[len(buffer) - 1] = (buffer[len(buffer) - 1] + buffer[j]) % 0x100
        bufferBytes=bytearray(buffer)
        try:
            buf = (ct.c_ubyte * len(bufferBytes))(*bufferBytes)
            buf2 = ct.create_string_buffer(9)
            written=self.Write(buf,len(buffer))
            result=self.Read(buf2,written)
            bs=bytearray(buf2)
            if bs[1] != cmd:
                return None
            if bs[6] != 0xa5:
                return None
            return [bs[2], bs[3], bs[4], bs[5]]
        except Exception as e:
            print(("Exec: "+str(e)))
    def GetSerialNumber(self):
        buffer=self.Exec(CMD_SN1,[0])
        buffer2=self.Exec(CMD_SN2,[0])
        bufferstr="".join("{:02x}".format(x) for x in buffer2[::-1]) 
        bufferstr+="".join("{:02x}".format(x) for x in buffer[::-1]) 
        return bufferstr
    def GetMeasurmentsNumber(self):
        buffer=self.Exec(CMD_RECCNT,[0])
        if len(buffer) > 1:
            return (buffer[1] << 8) + buffer[0]
        return 0
    def GetMeasurment(self,number):
        try:
            args = [0] * 4
            args[0] = number & 0xff
            args[1] = (number >> 8) & 0xff
            args[3] = 1
            m = Measurment()
            buffer = self.Exec(CMD_GETREC1,args)
            #print buffer
            buffer2 = self.Exec(CMD_GETREC2,args)
            #print buffer2
            day = buffer[0] & 0x1f
            month = ((buffer[0] & 0xe0) >> 5) + ((buffer[1] & 1) << 3)
            year = (buffer[1] >> 1) + 2000
            minute = buffer[2] & 0x3f
            hour = buffer[3] & 0x1f
            m.time=datetime.datetime(year,month,day,hour,minute)
            m.value = buffer2[1] * 0x100 + buffer2[0]
            m.code = buffer2[3] & 0x3f
            m.conditions = buffer2[2]
            m.type = (buffer2[3] & 0xc0) / 0x40
            #print(m.time, m.value, m.code, m.conditions, m.type)
            return m
        except Exception as e:
            print(("Measurment: "+str(e)))

    def GetDatetime(self):
        buffer=self.Exec(CMD_GETDT,[0])
        day = buffer[0] & 0x1f
        month = (buffer[0] >> 5) + ((buffer[1] & 1) << 3)
        year = (buffer[1] >> 1) + 2000
        minute = buffer[2]
        hour = buffer[3]
        return datetime.datetime(year,month,day,hour,minute)
    def SetDatetime(self,dt):
        args = [0] * 4
        args[0] = ((dt.month & 7) << 5) + dt.day
        args[1] = ((dt.year - 2000) << 1) + (dt.month >> 3)
        args[2] = dt.minute 
        args[3] = dt.hour
        self.Exec(CMD_SETDT,args)
    def ClearMeasurments(self):
        self.Exec(CMD_CLEAR,[0])

if __name__ == "__main__":
    import sys
    
    opened = False
    ev  = Evercare()

    ndx = 0
    if len(sys.argv) > 1:
        ndx = int(sys.argv[1])
    else:
        ndx = 0


    NumDevices = GetNumDevices()
    print("Number of devices: " + str(NumDevices))

    if TestInvalDevIndex( NumDevices) == 0:
        if NumDevices :
            ev.Open(ndx)
            opened = True
            ev.SetUartConfig(19200,3,0,0,0)
            ev.Exec(CMD_INIT,[0])
            print("Device SN: " + ev.GetSerialNumber())
            number_of_measurments=ev.GetMeasurmentsNumber()
            print("Number of measurments: " + str(number_of_measurments))
            print("Datetime: " + str(ev.GetDatetime()))
            print("\nMeasurments:")
            last_day=0
            for i in range(0,number_of_measurments):
                m=ev.GetMeasurment(i)
                if m.time.isocalendar()[1] != last_day:
                    print("")
                    last_day=m.time.isocalendar()[1]
                print(m.time,m.value,m.GetTimeLabel())

        if opened :
            ev.Close()
