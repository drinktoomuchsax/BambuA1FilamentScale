from machine import Pin
import time

# 定义段引脚（A-G 和 DP）
segments = {
    'A': Pin(13, Pin.OUT),
    'B': Pin(2, Pin.OUT),
    'C': Pin(6, Pin.OUT),
    'D': Pin(8, Pin.OUT),
    'E': Pin(5, Pin.OUT),
    'F': Pin(3, Pin.OUT),
    'G': Pin(10, Pin.OUT),
    'DP': Pin(7, Pin.OUT)
}

# 定义位选引脚（位选引脚高电平时点亮）
digits = [
    Pin(0, Pin.OUT),
    Pin(1, Pin.OUT),
    Pin(12, Pin.OUT),
    Pin(9, Pin.OUT)
]

# 当前显示的数字列表，支持4位，每位是一个元组 (字符, 小数点状态)
current_display = [(' ', False), (' ', False), (' ', False), (' ', False)]

# 数字到段的映射（0-9 和 空格）
digit_to_segments = {
    '0': ['A', 'B', 'C', 'D', 'E', 'F'],
    '1': ['B', 'C'],
    '2': ['A', 'B', 'G', 'E', 'D'],
    '3': ['A', 'B', 'G', 'C', 'D'],
    '4': ['F', 'G', 'B', 'C'],
    '5': ['A', 'F', 'G', 'C', 'D'],
    '6': ['A', 'F', 'G', 'C', 'D', 'E'],
    '7': ['A', 'B', 'C'],
    '8': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
    '9': ['A', 'B', 'C', 'D', 'F', 'G'],
    ' ': []  # 空格表示不显示任何段
}


def set_segments(digit_char, dp=False):
    """
    根据输入的字符设置段引脚状态。
    :param digit_char: 要显示的字符（'0'-'9' 或 ' '）
    :param dp: 是否点亮小数点
    """
    # 关闭所有段
    for seg in segments.values():
        seg.on()

    # 根据字符点亮对应的段
    for seg in digit_to_segments.get(digit_char, []):
        segments[seg].off()

    # 设置小数点
    if dp:
        segments['DP'].off()
    else:
        segments['DP'].on()


def set_digit(index):
    """
    激活指定的位选引脚，并关闭其他位选引脚。
    :param index: 位选的索引（0-3）
    """
    # 关闭所有位选
    for d in digits:
        d.off()

    # 打开当前位选
    if 0 <= index < len(digits):
        digits[index].on()


def pad_right(s, length, pad_char=' '):
    """
    手动实现字符串右对齐并填充指定字符。
    :param s: 原始字符串
    :param length: 目标长度
    :param pad_char: 填充字符（默认空格）
    :return: 填充后的字符串
    """
    s = str(s)
    while len(s) < length:
        s = pad_char + s
    if len(s) > length:
        s = s[-length:]
    return s


def display_number(number, decimal_points=None):
    """
    设置要显示的数字。
    :param number: 要显示的数字，可以是字符串或整数
    :param decimal_points: 一个列表，指示每一位是否显示小数点（可选），长度应为4
    """
    # 使用手动填充代替 rjust
    str_num = pad_right(str(number), 4)

    for i in range(4):
        char = str_num[i] if i < len(str_num) else ' '
        dp = False
        if decimal_points and i < len(decimal_points):
            dp = bool(decimal_points[i])
        current_display[i] = (char, dp)


def run_display():
    """
    持续刷新数码管显示，通过循环扫描实现多位显示。
    """
    while True:
        for i in range(4):
            set_digit(i)  # 激活第i位
            char, dp = current_display[i]
            set_segments(char, dp)
            time.sleep_ms(5)  # 短暂延时以确保显示稳定
            digits[i].off()  # 关闭当前位


# 示例：显示数字 "1234" 并在第二位显示小数点
display_number("1234", decimal_points=[False, True, False, False])
print("Displaying 1234 with decimal point on 2nd digit")
run_display()

