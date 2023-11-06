import serial


ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=1)
#ser.flush()

while True:
	line = ser.readline().decode('utf-8').rstrip()
	print("received: ", line)
