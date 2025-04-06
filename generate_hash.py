import hashlib

# The password and salt from our test and policy
password = "password"
salt = "0123456789abcdef0123456789abcdef"

# Hash the password with the salt
hash_obj = hashlib.sha256((password + salt).encode())
hashed_password = hash_obj.hexdigest()

print(f"Password: {password}")
print(f"Salt: {salt}")
print(f"Hashed Password: {hashed_password}")
