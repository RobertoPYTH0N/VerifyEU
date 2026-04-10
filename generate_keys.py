from nacl.signing import SigningKey

test_private = SigningKey.generate()
test_public = test_private.verify_key

print("Private key:", test_private.encode().hex())
print("Public key:", test_public.encode().hex())
