from OpenSSL import crypto

# 生成一个新的证书和私钥
key = crypto.PKey()
key.generate_key(crypto.TYPE_RSA, 4096)

cert = crypto.X509()
cert.set_serial_number(1000)
cert.get_subject().CN = "localhost"  # 设置域名（可以是你的 IP）
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 证书有效期 1 年
cert.set_issuer(cert.get_subject())
cert.set_pubkey(key)
cert.sign(key, "sha256")

# 保存证书和私钥
with open("cert.pem", "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

with open("key.pem", "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

print("TLS 证书生成完成！")
