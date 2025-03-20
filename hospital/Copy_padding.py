import numpy as np

# 读取文件
grad_weights = np.load("grad_weights.npy")  # shape (8000, 2)
grad_weights2 = np.load("grad_weights2.npy")  # shape (7998, 2)

# 计算缺失的行数
num_missing_rows = grad_weights.shape[0] - grad_weights2.shape[0]  # 8000 - 7998 = 2

# 复制最后一行填充
last_rows = np.tile(grad_weights2[-1], (num_missing_rows, 1))

# 拼接补全
grad_weights2_padded = np.vstack((grad_weights2, last_rows))

print(grad_weights2_padded.shape)  # (8000, 2)

# 保存填充后的数组
np.save("grad_weights2_padded.npy", grad_weights2_padded)
