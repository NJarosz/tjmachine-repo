
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

print("Place Card to Reader")

idn, name = reader.read()
print("Current Info:", str(idn), name)

