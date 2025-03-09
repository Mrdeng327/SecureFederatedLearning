import rsa

# 生成 2048 位密钥对（推荐 2048 位，如果是测试可以用 512 位）
(pubkey, privkey) = rsa.newkeys(2048)

# 将密钥保存到文件
with open("hospital_A_public.pem", "wb") as pub_file:
    pub_file.write(pubkey.save_pkcs1("PEM"))

with open("hospital_A_private.pem", "wb") as priv_file:
    priv_file.write(privkey.save_pkcs1("PEM"))

print("The generation of public and private keys for Hospital A is complete and has been saved to a file!")
