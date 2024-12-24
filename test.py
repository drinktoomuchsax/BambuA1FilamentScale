import machine
import time
import json
import os

# HX711类定义
class HX711:
    def __init__(self, data_pin, clock_pin, gain=128):
        self.DATA = machine.Pin(data_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.CLK = machine.Pin(clock_pin, machine.Pin.OUT)
        self.CLK.value(0)
        self.GAIN = gain

    def read_count(self):
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
            time.sleep_us(1)  # 确保信号稳定

        # 第25个脉冲用于设置增益和读取最后一个脉冲
        self.CLK.value(1)
        count ^= 0x800000  # 转换为补码
        self.CLK.value(0)

        return count

    def read_average(self, times=10):
        total = 0
        for _ in range(times):
            total += self.read_count()
            time.sleep_us(100)
        return total // times

    def get_value(self):
        raw = self.read_average()
        if raw & 0x800000:
            return raw - 0x1000000
        else:
            return raw

    def get_weight(self, offset=0, scale=1):
        return (self.get_value() - offset) / scale

# 校准数据文件路径
CALIB_FILE = 'calib.json'

# 加载校准数据
def load_calibration():
    if 'calib.json' in os.listdir():
        with open('calib.json', 'r') as f:
            data = json.load(f)
            return data.get('offset1', 0), data.get('scale1', 1), data.get('offset2', 0), data.get('scale2', 1)
    else:
        return 0, 1, 0, 1

# 保存校准数据
def save_calibration(offset1, scale1, offset2, scale2):
    data = {
        'offset1': offset1,
        'scale1': scale1,
        'offset2': offset2,
        'scale2': scale2
    }
    with open('calib.json', 'w') as f:
        json.dump(data, f)

# 初始化HX711实例
hx1 = HX711(data_pin=2, clock_pin=3)
hx2 = HX711(data_pin=6, clock_pin=7)

# 加载校准数据
offset1, scale1, offset2, scale2 = load_calibration()

# 初始化GPIO
gpio12 = machine.Pin(12, machine.Pin.OUT)
gpio13 = machine.Pin(13, machine.Pin.OUT)
gpio12.value(1)  # 默认常亮
gpio13.value(0)  # 默认熄灭

# 按键初始化
button = machine.Pin(10, machine.Pin.IN, machine.Pin.PULL_UP)

# 状态机定义
STATE_DEFAULT = 0
STATE_CALIB_1000 = 1
STATE_CALIB_0 = 2
STATE_CALIB_MINUS100 = 3

state = STATE_DEFAULT

# 去抖动参数
last_press = 0
debounce_time = 200  # 毫秒

# 标定目标值
calib_steps = {
    STATE_CALIB_1000: 1000,
    STATE_CALIB_0: 0,
    STATE_CALIB_MINUS100: -100
}

# Blink控制
blink_interval_fast = 200  # 毫秒
blink_interval_slow = 500  # 毫秒
last_blink = 0
blink_state = False

def read_total_weight():
    weight1 = hx1.get_weight(offset1, scale1)
    weight2 = hx2.get_weight(offset2, scale2)
    return weight1 + weight2

def handle_calibration(target_value):
    global offset1, scale1, offset2, scale2
    total = read_total_weight()
    print(f"Calibrating: Total={total} to {target_value}")
    # 简单线性标定，假设scale为 (total - offset) / target
    # 这里需要根据实际需求调整标定逻辑
    # 这里只是一个示例，实际情况可能需要更复杂的算法
    if target_value != 0:
        scale = total / target_value
        offset = 0  # 假设零点偏移为0
    else:
        # 防止除以零，可以设置scale为1或其他默认值
        scale = 1
        offset = total

    # 简单存储相同的offset和scale到两个传感器
    offset1 = offset2 = offset
    scale1 = scale2 = scale

    save_calibration(offset1, scale1, offset2, scale2)
    print(f"Calibration saved: Offset1={offset1}, Scale1={scale1}, Offset2={offset2}, Scale2={scale2}")

def update_blink(current_time):
    global last_blink, blink_state
    if state == STATE_CALIB_1000:
        interval = blink_interval_fast
    elif state == STATE_CALIB_0:
        interval = blink_interval_slow
    else:
        return  # 不需要闪烁

    if current_time - last_blink >= interval:
        blink_state = not blink_state
        gpio13.value(blink_state)
        last_blink = current_time

def button_pressed():
    global state, last_press, offset1, scale1, offset2, scale2
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_press) < debounce_time:
        return False
    last_press = current_time
    return True

while True:
    # 检查按键
    if not button.value():  # 按键按下
        if button_pressed():
            state = (state + 1) % 4
            if state == STATE_DEFAULT:
                gpio12.value(1)
                gpio13.value(0)
                print("Returned to default state")
            elif state == STATE_CALIB_1000:
                gpio12.value(0)
                gpio13.value(1)
                print("Entered calibration state: Step 1 (1000)")
            elif state == STATE_CALIB_0:
                handle_calibration(calib_steps[STATE_CALIB_1000])
                print("Calibration Step 1 completed: Set to 1000")
                print("Entered calibration state: Step 2 (0)")
            elif state == STATE_CALIB_MINUS100:
                handle_calibration(calib_steps[STATE_CALIB_0])
                print("Calibration Step 2 completed: Set to 0")
                print("Entered calibration state: Step 3 (-100)")
            elif state == 3:
                handle_calibration(calib_steps[STATE_CALIB_MINUS100])
                print("Calibration Step 3 completed: Set to -100")
                state = STATE_DEFAULT
                gpio12.value(1)
                gpio13.value(0)
                print("Returned to default state after calibration")
            # 等待按键释放
            while not button.value():
                time.sleep_ms(10)

    # 状态处理
    if state == STATE_DEFAULT:
        gpio12.value(1)
        gpio13.value(0)
        total_weight = read_total_weight()
        print(f"Weight: {total_weight}")
        time.sleep(1)
    elif state == STATE_CALIB_1000:
        gpio12.value(0)
        gpio13.value(1)
        current_time = time.ticks_ms()
        update_blink(current_time)
        time.sleep(0.1)
    elif state == STATE_CALIB_0:
        current_time = time.ticks_ms()
        update_blink(current_time)
        time.sleep(0.1)
    elif state == STATE_CALIB_MINUS100:
        gpio13.value(0)
        gpio12.value(1)
        total_weight = read_total_weight()
        print(f"Weight after calibration: {total_weight}")
        time.sleep(1)
