from machine import Pin
import time


class HX711:
    def __init__(self, data_pin, clock_pin, gain=128):
        """
        初始化HX711模块。

        :param data_pin: 数据引脚编号
        :param clock_pin: 时钟引脚编号
        :param gain: 增益因子（默认128）
        """
        self.DATA = Pin(data_pin, Pin.IN, Pin.PULL_UP)
        self.CLK = Pin(clock_pin, Pin.OUT)
        self.CLK.value(0)
        self.GAIN = gain

    def read_count(self):
        """
        读取原始ADC值（24位）。

        :return: 原始ADC值
        """
        count = 0
        # 等待数据引脚为低，表示数据准备好
        while self.DATA.value():
            pass

        for _ in range(24):
            self.CLK.value(1)
            count = count << 1
            self.CLK.value(0)
            if self.DATA.value():
                count += 1
            # 可根据需要添加短暂的延时以确保稳定性
            time.sleep_us(1)

        # 第25个脉冲用于设置增益和读取最后一个脉冲
        self.CLK.value(1)
        count ^= 0x800000  # 将数据转换为补码
        self.CLK.value(0)

        return count

    def read_average(self, times=10):
        """
        读取多次并取平均值，以提高稳定性。

        :param times: 读取次数
        :return: 平均ADC值
        """
        sum = 0
        for _ in range(times):
            sum += self.read_count()
            time.sleep_us(100)
        return sum // times

    def get_value(self):
        """
        获取最终的ADC值，考虑补码转换。

        :return: ADC的有符号值
        """
        raw = self.read_average()
        if raw & 0x800000:
            # 如果最高位为1，表示负数
            return raw - 0x1000000
        else:
            return raw

    def get_weight(self, offset=0, scale=1):
        """
        获取校准后的重量值。

        :param offset: 零点偏移
        :param scale: 缩放因子
        :return: 计算后的重量值
        """
        return (self.get_value() - offset) / scale


# 使用示例
# 请根据实际连接的GPIO引脚编号进行修改
data_pin = 2  # 例如GPIO5连接到HX711的DT引脚
clock_pin = 3  # 例如GPIO18连接到HX711的SCK引脚

hx = HX711(data_pin, clock_pin)

# 校准参数，需要根据实际使用的传感器进行调整
offset = 0
scale = 1

while True:
    weight = hx.get_weight(offset, scale)
    print("Weight:", weight)
    time.sleep(1)
