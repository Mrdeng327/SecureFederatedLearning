import numpy as np
import json

# 1️⃣ 真实梯度（医院 A 和 B）
real_bias_gradient_A = -5.584002792602405e-05
real_weight_gradient_A = np.array([
    [0.00797811, 0.07008306, 0.05766758, 0.06413166, 0.10698919, 0.11710357]
])

real_bias_gradient_B = -6.584002792602405e-05
real_weight_gradient_B = np.array([
    [0.00697811, 0.06008306, 0.04766758, 0.05413166, 0.09698919, 0.10710357]
])

# 2️⃣ 生成随机掩码（保证 `mask_A + mask_B = 0`）
mask_bias_A = np.random.rand()
mask_weight_A = np.random.rand(*real_weight_gradient_A.shape)

mask_bias_B = -mask_bias_A  # 确保掩码相加为 0
mask_weight_B = -mask_weight_A

# 3️⃣ 计算 `mask ingredients`
mask_ingredient_A = {
    "hospital": "Hospital A",
    "mask_ingredient": {
        "bias_gradient": real_bias_gradient_A + mask_bias_A,
        "weight_gradient": (real_weight_gradient_A + mask_weight_A).tolist()
    }
}

mask_ingredient_B = {
    "hospital": "Hospital B",
    "mask_ingredient": {
        "bias_gradient": real_bias_gradient_B + mask_bias_B,
        "weight_gradient": (real_weight_gradient_B + mask_weight_B).tolist()
    }
}

# 4️⃣ 存储 `mask ingredients`
mask_ingredients = [mask_ingredient_A, mask_ingredient_B]

with open("mask_ingredients.json", "w") as f:
    json.dump(mask_ingredients, f, indent=4)

print("✅ Mask ingredients saved to mask_ingredients.json")
def start_secure_aggregation():
    """执行安全聚合，计算全局梯度"""
    print("⚡ Performing secure aggregation...")

    # 1️⃣ 读取 JSON 数据
    with open("mask_ingredients.json", "r") as f:
        mask_ingredients = json.load(f)

    # 2️⃣ 初始化全局梯度
    global_bias_gradient = 0
    global_weight_gradient = np.zeros_like(mask_ingredients[0]["mask_ingredient"]["weight_gradient"])

    # 3️⃣ 计算全局梯度（去掩码）
    for item in mask_ingredients:
        global_bias_gradient += item["mask_ingredient"]["bias_gradient"]
        global_weight_gradient += np.array(item["mask_ingredient"]["weight_gradient"])

    # 4️⃣ 计算全局模型哈希
    global_model_hash = hash(str(global_weight_gradient.tolist()))

    # 5️⃣ 输出计算结果
    print(f"✅ Global Bias Gradient: {global_bias_gradient}")
    print(f"✅ Global Weight Gradient: {global_weight_gradient}")
    print(f"✅ Global Model Hash: {global_model_hash}")

# 运行测试
if __name__ == "__main__":
    start_secure_aggregation()

