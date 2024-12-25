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

    def get_raw(self):
        return self.read_average()

# 校准数据文件路径
CALIB_FILE = 'calib.json'

# 加载校准数据
def load_calibration():
    if CALIB_FILE in os.listdir():
        with open(CALIB_FILE, 'r') as f:
            data = json.load(f)
            return data.get('offset', 0), data.get('scale', 1)
    else:
        return 0, 1

# 保存校准数据
def save_calibration(offset, scale):
    data = {
        'offset': offset,
        'scale': scale
    }
    with open(CALIB_FILE, 'w') as f:
        json.dump(data, f)

# 初始化HX711实例
hx1 = HX711(data_pin=2, clock_pin=3)
hx2 = HX711(data_pin=6, clock_pin=7)

# 加载校准数据
offset, scale = load_calibration()

# 初始化GPIO
gpio12 = machine.Pin(12, machine.Pin.OUT)
gpio13 = machine.Pin(13, machine.Pin.OUT)
gpio12.value(1)  # 默认常亮
gpio13.value(0)  # 默认熄灭

# 按键初始化
button = machine.Pin(10, machine.Pin.IN, machine.Pin.PULL_UP)

# 状态机定义
STATE_DEFAULT = 0
STATE_CALIB_ENTER = 1
STATE_CALIB_STEP_1000 = 2
STATE_CALIB_STEP_0 = 3
STATE_CALIB_STEP_MINUS100 = 4

state = STATE_DEFAULT

# 去抖动参数
last_press = 0
debounce_time = 200  # 毫秒

# 标定目标值
calib_steps = {
    STATE_CALIB_STEP_1000: 1000,
    STATE_CALIB_STEP_0: 0,
    STATE_CALIB_STEP_MINUS100: -100
}

# Blink控制参数
blink_interval_fast = 200  # 毫秒
blink_interval_slow = 500  # 毫秒
last_blink = 0
blink_state = False

# 存储校准记录
calib_records = []

def read_total_sum():
    sum1 = hx1.get_raw()
    sum2 = hx2.get_raw()
    total = sum1 + sum2
    return total

def handle_calibration_step(target_value):
    global offset, scale, calib_records
    total = read_total_sum()
    calib_records.append((total, target_value))
    print(f"Calibrating: Recorded Sum={total} for Target={target_value}")

    # 使用两个校准点计算scale和offset
    if len(calib_records) == 2:
        (sum1, target1), (sum2, target2) = calib_records
        if target1 != target2:
            scale = (sum1 - sum2) / (target1 - target2)
            offset = sum2 - scale * target2
            save_calibration(offset, scale)
            print(f"Calibration saved: Offset={offset}, Scale={scale}")
        else:
            print("Error: Calibration targets are the same. Cannot compute scale.")

def get_calibrated_value(sum_total):
    return (sum_total - offset) / scale

def update_blink(current_time):
    global last_blink, blink_state
    if state == STATE_CALIB_STEP_1000:
        interval = blink_interval_fast
    elif state == STATE_CALIB_STEP_0:
        interval = blink_interval_slow
    else:
        return  # 不需要闪烁

    if current_time - last_blink >= interval:
        blink_state = not blink_state
        gpio13.value(blink_state)
        last_blink = current_time

def button_pressed():
    global last_press
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_press) < debounce_time:
        return False
    last_press = current_time
    return True

while True:
    # 检查按键
    if not button.value():  # 按键按下
        if button_pressed():
            state += 1
            if state > STATE_CALIB_STEP_MINUS100:
                state = STATE_DEFAULT
            print(f"State changed to: {state}")

            if state == STATE_DEFAULT:
                gpio12.value(1)
                gpio13.value(0)
                print("Returned to default state")
                calib_records = []  # 清空校准记录
            elif state == STATE_CALIB_ENTER:
                gpio12.value(0)
                gpio13.value(1)
                print("Entered calibration state")
            elif state == STATE_CALIB_STEP_1000:
                handle_calibration_step(calib_steps[STATE_CALIB_STEP_1000])
                print("Calibration Step 1 completed: Set to 1000")
            elif state == STATE_CALIB_STEP_0:
                handle_calibration_step(calib_steps[STATE_CALIB_STEP_0])
                print("Calibration Step 2 completed: Set to 0")
            elif state == STATE_CALIB_STEP_MINUS100:
                handle_calibration_step(calib_steps[STATE_CALIB_STEP_MINUS100])
                print("Calibration Step 3 completed: Set to -100")
                print("Calibration complete. Returning to default state.")
                state = STATE_DEFAULT
                gpio12.value(1)
                gpio13.value(0)
                calib_records = []  # 清空校准记录

            # 等待按键释放
            while not button.value():
                time.sleep_ms(10)

    # 状态处理
    if state == STATE_DEFAULT:
        gpio12.value(1)
        gpio13.value(0)
        total_sum = read_total_sum()
        calibrated_weight = get_calibrated_value(total_sum)
        print(f"Weight: {calibrated_weight:.2f}")
        time.sleep(0.2)
    elif state in (STATE_CALIB_STEP_1000, STATE_CALIB_STEP_0):
        gpio12.value(0)
        current_time = time.ticks_ms()
        update_blink(current_time)
        time.sleep(0.1)
    elif state == STATE_CALIB_STEP_MINUS100:
        gpio12.value(0)
        gpio13.value(0)
        time.sleep(0.1)
