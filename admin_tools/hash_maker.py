from passlib.context import CryptContext
import getpass

# Initialize the hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("--- DeepCut Admin Hash Generator ---")
# getpass works exactly like a terminal login—it hides the letters as you type them
new_password = getpass.getpass("Type the new password (input will be hidden): ")

# Generate the hash
hashed = pwd_context.hash(new_password)

print("\nSuccess! Copy this exact string into the hashed_password column in DBeaver:")
print("-" * 50)
print(hashed)
print("-" * 50)
