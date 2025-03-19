from OpenSSL import crypto

# Generate a new certificate and private key
key = crypto.PKey()
key.generate_key(crypto.TYPE_RSA, 4096)

cert = crypto.X509()
cert.set_serial_number(1000)
cert.get_subject().CN = "localhost"
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Certificate validity 1 year
cert.set_issuer(cert.get_subject())
cert.set_pubkey(key)
cert.sign(key, "sha256")

# Keeping certificates and private keys
with open("cert.pem", "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

with open("key.pem", "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

print("TLS certificate generation is complete!")
