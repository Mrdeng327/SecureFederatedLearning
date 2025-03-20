import rsa

# Generate 2048-bit key pair
(pubkey, privkey) = rsa.newkeys(2048)

# Save the key to a file
with open("hospital_B_public.pem", "wb") as pub_file:
    pub_file.write(pubkey.save_pkcs1("PEM"))

with open("hospital_B_private.pem", "wb") as priv_file:
    priv_file.write(privkey.save_pkcs1("PEM"))

print(" The generation of public and private keys for Hospital B is complete and has been saved to a file!")
