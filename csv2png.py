import pandas as pd
import matplotlib.pyplot as plt
import os

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 获取当前目录下所有CSV文件
csv_files = [f for f in os.listdir(current_dir) if f.endswith('.csv')]

# 遍历每个CSV文件，进行数据处理并生成图片
for csv_file in csv_files:
    # 构建完整的CSV文件路径
    csv_path = os.path.join(current_dir, csv_file)
    print(f"正在处理文件: {csv_path}")
    
    # 读取CSV数据
    data = pd.read_csv(csv_path)
    
    # 确保数据列名没有多余的空格
    data.columns = data.columns.str.strip()
    
    # 将Timestamp列转换为datetime格式
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
    
    # 计算相对时间（以分钟为单位）
    start_time = data['Timestamp'].iloc[0]
    data['Time (minutes)'] = (data['Timestamp'] - start_time).dt.total_seconds() / 60.0
    
    # 绘制质量随时间变化的曲线
    plt.figure(figsize=(10, 6))
    plt.plot(data['Time (minutes)'], data['Weight(g)'], marker='o', color='b', label='Weight (g)')
    
    # 设置标题和标签
    plt.title('Weight vs Time')
    plt.xlabel('Time (minutes)')
    plt.ylabel('Weight (g)')
    plt.grid(True)
    plt.legend()
    
    # 获取CSV文件的名称（去掉扩展名）作为图片文件名
    image_filename = os.path.splitext(csv_file)[0] + '.png'
    output_image = os.path.join(current_dir, image_filename)
    
    # 保存图像为PNG文件
    plt.savefig(output_image)
    
    # 显示图像
    # plt.show()
    
    print(f"图像已保存为 {output_image}")
