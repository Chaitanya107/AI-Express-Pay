
#!/usr/bin/env python3

import statistics as stat
import time

import RPi.GPIO as GPIO


class HX711:

    def __init__(self,
                 dout_pin,
                 pd_sck_pin,
                 gain_channel_A=128,
                 select_channel='A'):
        if (isinstance(dout_pin, int)):
            if (isinstance(pd_sck_pin, int)):
                self._pd_sck = pd_sck_pin
                self._dout = dout_pin
            else:
                raise TypeError('pd_sck_pin must be type int. '
                                'Received pd_sck_pin: {}'.format(pd_sck_pin))
        else:
            raise TypeError('dout_pin must be type int. '
                            'Received dout_pin: {}'.format(dout_pin))

        self._gain_channel_A = 0
        self._offset_A_128 = 0
        self._offset_A_64 = 0
        self._offset_B = 0  
        self._last_raw_data_A_128 = 0
        self._last_raw_data_A_64 = 0
        self._last_raw_data_B = 0
        self._wanted_channel = ''
        self._current_channel = ''
        self._scale_ratio_A_128 = 1  
        self._scale_ratio_A_64 = 1  
        self._scale_ratio_B = 1  
        self._debug_mode = False
        self._data_filter = self.outliers_filter  

        GPIO.setup(self._pd_sck, GPIO.OUT)  
        GPIO.setup(self._dout, GPIO.IN)  
        self.select_channel(select_channel)
        self.set_gain_A(gain_channel_A)

    def select_channel(self, channel):
        channel = channel.capitalize()
        if (channel == 'A'):
            self._wanted_channel = 'A'
        elif (channel == 'B'):
            self._wanted_channel = 'B'
        else:
            raise ValueError('Parameter "channel" has to be "A" or "B". '
                             'Received: {}'.format(channel))
        self._read()
        time.sleep(0.5)

    def set_gain_A(self, gain):
        if gain == 128:
            self._gain_channel_A = gain
        elif gain == 64:
            self._gain_channel_A = gain
        else:
            raise ValueError('gain has to be 128 or 64. '
                             'Received: {}'.format(gain))
        self._read()
        time.sleep(0.5)

    def zero(self, readings=30):
        if readings > 0 and readings < 100:
            result = self.get_raw_data_mean(readings)
            if result != False:
                if (self._current_channel == 'A' and
                        self._gain_channel_A == 128):
                    self._offset_A_128 = result
                    return False
                elif (self._current_channel == 'A' and
                      self._gain_channel_A == 64):
                    self._offset_A_64 = result
                    return False
                elif (self._current_channel == 'B'):
                    self._offset_B = result
                    return False
                else:
                    if self._debug_mode:
                        print('Cannot zero() channel and gain mismatch.\n'
                              'current channel: {}\n'
                              'gain A: {}\n'.format(self._current_channel,
                                                    self._gain_channel_A))
                    return True
            else:
                if self._debug_mode:
                    print('From method "zero()".\n'
                          'get_raw_data_mean(readings) returned False.\n')
                return True
        else:
            raise ValueError('Parameter "readings" '
                             'can be in range 1 up to 99. '
                             'Received: {}'.format(readings))

    def set_offset(self, offset, channel='', gain_A=0):
        channel = channel.capitalize()
        if isinstance(offset, int):
            if channel == 'A' and gain_A == 128:
                self._offset_A_128 = offset
                return
            elif channel == 'A' and gain_A == 64:
                self._offset_A_64 = offset
                return
            elif channel == 'B':
                self._offset_B = offset
                return
            elif channel == '':
                if self._current_channel == 'A' and self._gain_channel_A == 128:
                    self._offset_A_128 = offset
                    return
                elif self._current_channel == 'A' and self._gain_channel_A == 64:
                    self._offset_A_64 = offset
                    return
                else:
                    self._offset_B = offset
                    return
            else:
                raise ValueError('Parameter "channel" has to be "A" or "B". '
                                 'Received: {}'.format(channel))
        else:
            raise TypeError('Parameter "offset" has to be integer. '
                            'Received: ' + str(offset) + '\n')

    def set_scale_ratio(self, scale_ratio, channel='', gain_A=0):
        channel = channel.capitalize()
        if isinstance(gain_A, int):
            if channel == 'A' and gain_A == 128:
                self._scale_ratio_A_128 = scale_ratio
                return
            elif channel == 'A' and gain_A == 64:
                self._scale_ratio_A_64 = scale_ratio
                return
            elif channel == 'B':
                self._scale_ratio_B = scale_ratio
                return
            elif channel == '':
                if self._current_channel == 'A' and self._gain_channel_A == 128:
                    self._scale_ratio_A_128 = scale_ratio
                    return
                elif self._current_channel == 'A' and self._gain_channel_A == 64:
                    self._scale_ratio_A_64 = scale_ratio
                    return
                else:
                    self._scale_ratio_B = scale_ratio
                    return
            else:
                raise ValueError('Parameter "channel" has to be "A" or "B". '
                                 'received: {}'.format(channel))
        else:
            raise TypeError('Parameter "gain_A" has to be integer. '
                            'Received: ' + str(gain_A) + '\n')

    def set_data_filter(self, data_filter):
        if callable(data_filter):
            self._data_filter = data_filter
        else:
            raise TypeError('Parameter "data_filter" must be a function. '
                            'Received: {}'.format(data_filter))

    def set_debug_mode(self, flag=False):
        if flag == False:
            self._debug_mode = False
            print('Debug mode DISABLED')
            return
        elif flag == True:
            self._debug_mode = True
            print('Debug mode ENABLED')
            return
        else:
            raise ValueError('Parameter "flag" can be only BOOL value. '
                             'Received: {}'.format(flag))

    def _save_last_raw_data(self, channel, gain_A, data):
        if channel == 'A' and gain_A == 128:
            self._last_raw_data_A_128 = data
        elif channel == 'A' and gain_A == 64:
            self._last_raw_data_A_64 = data
        elif channel == 'B':
            self._last_raw_data_B = data
        else:
            return False

    def _ready(self):
        if GPIO.input(self._dout) == 0:
            return True
        else:
            return False

    def _set_channel_gain(self, num):
        for _ in range(num):
            start_counter = time.perf_counter()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = time.perf_counter()
            if end_counter - start_counter >= 0.00006:
                if self._debug_mode:
                    print('Not enough fast while setting gain and channel')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                result = self.get_raw_data_mean(6)  
                if result == False:
                    return False
        return True

    def _read(self):
        GPIO.output(self._pd_sck, False)
        ready_counter = 0
        while (not self._ready() and ready_counter <= 40):
            time.sleep(0.01) 
            ready_counter += 1
            if ready_counter == 50:
                if self._debug_mode:
                    print('self._read() not ready after 40 trials\n')
                return False
        data_in = 0  
        for _ in range(24):
            start_counter = time.perf_counter()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = time.perf_counter()
            if end_counter - start_counter >= 0.00006:
                if self._debug_mode:
                    print('Not enough fast while reading data')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                return False
            data_in = (data_in << 1) | GPIO.input(self._dout)

        if self._wanted_channel == 'A' and self._gain_channel_A == 128:
            if not self._set_channel_gain(1): 
                return False 
            else:
                self._current_channel = 'A' 
                self._gain_channel_A = 128  
        elif self._wanted_channel == 'A' and self._gain_channel_A == 64:
            if not self._set_channel_gain(3): 
                return False  
            else:
                self._current_channel = 'A' 
                self._gain_channel_A = 64
        else:
            if not self._set_channel_gain(2):  
                return False  
            else:
                self._current_channel = 'B'  

        if self._debug_mode:  
            print('Binary value as received: {}'.format(bin(data_in)))

        if (data_in == 0x7fffff
                or  
                data_in == 0x800000
           ):  
            if self._debug_mode:
                print('Invalid data detected: {}\n'.format(data_in))
            return False  

        
        signed_data = 0
        if (data_in & 0x800000):
            signed_data = -(
                (data_in ^ 0xffffff) + 1)  
        else:  
            signed_data = data_in

        if self._debug_mode:
            print('Converted 2\'s complement value: {}'.format(signed_data))

        return signed_data

    def get_raw_data_mean(self, readings=30):
        backup_channel = self._current_channel
        backup_gain = self._gain_channel_A
        data_list = []
        for _ in range(readings):
            data_list.append(self._read())
        data_mean = False
        if readings > 2 and self._data_filter:
            filtered_data = self._data_filter(data_list)
            if not filtered_data:
                return False
            if self._debug_mode:
                print('data_list: {}'.format(data_list))
                print('filtered_data list: {}'.format(filtered_data))
                print('data_mean:', stat.mean(filtered_data))
            data_mean = stat.mean(filtered_data)
        else:
            data_mean = stat.mean(data_list)
        self._save_last_raw_data(backup_channel, backup_gain, data_mean)
        return int(data_mean)

    def get_data_mean(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result != False:
            if self._current_channel == 'A' and self._gain_channel_A == 128:
                return result - self._offset_A_128
            elif self._current_channel == 'A' and self._gain_channel_A == 64:
                return result - self._offset_A_64
            else:
                return result - self._offset_B
        else:
            return False

    def get_weight_mean(self, readings=30):
        result = self.get_raw_data_mean(readings)
        if result != False:
            if self._current_channel == 'A' and self._gain_channel_A == 128:
                return float(
                    (result - self._offset_A_128) / self._scale_ratio_A_128)
            elif self._current_channel == 'A' and self._gain_channel_A == 64:
                return float(
                    (result - self._offset_A_64) / self._scale_ratio_A_64)
            else:
                return float((result - self._offset_B) / self._scale_ratio_B)
        else:
            return False

    def get_current_channel(self):
        return self._current_channel

    def get_data_filter(self):
        return self._data_filter

    def get_current_gain_A(self):
        return self._gain_channel_A

    def get_last_raw_data(self, channel='', gain_A=0):
        channel = channel.capitalize()
        if channel == 'A' and gain_A == 128:
            return self._last_raw_data_A_128
        elif channel == 'A' and gain_A == 64:
            return self._last_raw_data_A_64
        elif channel == 'B':
            return self._last_raw_data_B
        elif channel == '':
            if self._current_channel == 'A' and self._gain_channel_A == 128:
                return self._last_raw_data_A_128
            elif self._current_channel == 'A' and self._gain_channel_A == 64:
                return self._last_raw_data_A_64
            else:
                return self._last_raw_data_B
        else:
            raise ValueError(
                'Parameter "channel" has to be "A" or "B". '
                'Received: {} \nParameter "gain_A" has to be 128 or 64. Received {}'
                .format(channel, gain_A))

    def get_current_offset(self, channel='', gain_A=0):
        channel = channel.capitalize()
        if channel == 'A' and gain_A == 128:
            return self._offset_A_128
        elif channel == 'A' and gain_A == 64:
            return self._offset_A_64
        elif channel == 'B':
            return self._offset_B
        elif channel == '':
            if self._current_channel == 'A' and self._gain_channel_A == 128:
                return self._offset_A_128
            elif self._current_channel == 'A' and self._gain_channel_A == 64:
                return self._offset_A_64
            else:
                return self._offset_B
        else:
            raise ValueError(
                'Parameter "channel" has to be "A" or "B". '
                'Received: {} \nParameter "gain_A" has to be 128 or 64. Received {}'
                .format(channel, gain_A))

    def get_current_scale_ratio(self, channel='', gain_A=0):
        channel = channel.capitalize()
        if channel == 'A' and gain_A == 128:
            return self._scale_ratio_A_128
        elif channel == 'A' and gain_A == 64:
            return self._scale_ratio_A_64
        elif channel == 'B':
            return self._scale_ratio_B
        elif channel == '':
            if self._current_channel == 'A' and self._gain_channel_A == 128:
                return self._scale_ratio_A_128
            elif self._current_channel == 'A' and self._gain_channel_A == 64:
                return self._scale_ratio_A_64
            else:
                return self._scale_ratio_B
        else:
            raise ValueError(
                'Parameter "channel" has to be "A" or "B". '
                'Received: {} \nParameter "gain_A" has to be 128 or 64. Received {}'
                .format(channel, gain_A))

    def power_down(self):
        GPIO.output(self._pd_sck, False)
        GPIO.output(self._pd_sck, True)
        time.sleep(0.01)

    def power_up(self):
        GPIO.output(self._pd_sck, False)
        time.sleep(0.01)

    def reset(self):
        self.power_down()
        self.power_up()
        result = self.get_raw_data_mean(6)
        if result:
            return False
        else:
            return True


    def outliers_filter(self, data_list, stdev_thresh = 1.0):
        data = [num for num in data_list if (num != -1 and num != False and num != True)] 
        if not data:
            return []

        median = stat.median(data)
        dists_from_median = [(abs(measurement - median)) for measurement in data]
        stdev = stat.stdev(dists_from_median)
        if stdev:
            ratios_to_stdev = [(dist / stdev) for dist in dists_from_median]
        else:
            return [median]
        filtered_data = []
        for i in range(len(data)):
            if ratios_to_stdev[i] < stdev_thresh:
                filtered_data.append(data[i])
        return filtered_data
