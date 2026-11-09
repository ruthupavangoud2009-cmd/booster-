import uuid
import json
import random
import string
from datetime import datetime, timedelta

FILE_PATH = "data/keys/keys.json"

def main_menu():
    while True:
        print("\n1. Generate Key")
        print("2. List Keys")
        print("3. Delete Key")
        print("4. Clear File")
        print("5. Exit")

        choice = input("Enter your choice: ")
        handle_choice(choice)

def handle_choice(choice):
    if choice == "1":
        handle_key_generation()
    elif choice == "2":
        handle_list_keys()
    elif choice == "3":
        handle_delete_key()
    elif choice == "4":
        handle_clear_file()
    elif choice == "5":
        print("Exiting program.")
        exit_program()
    else:
        print("Invalid choice. Please try again.")

def handle_key_generation():
    month = int(input("Enter month (e.g., 1 or 3): "))
    amount = int(input("Enter amount: "))
    quantity = int(input("Enter quantity of keys: "))
    keys = load_keys_from_file(FILE_PATH)
    generate_key(keys, month, amount, quantity, FILE_PATH)

def handle_list_keys():
    keys = load_keys_from_file(FILE_PATH)
    print("All Keys:", list_keys(keys))

def handle_delete_key():
    keys = load_keys_from_file(FILE_PATH)
    key_to_delete = input("Enter the key to delete: ")
    delete_key(keys, key_to_delete)
    print("Key deleted.")

def handle_clear_file():
    clear_file(FILE_PATH)
    print("File cleared.")

def load_keys_from_file(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return []

def save_keys_to_file(keys, file_path):
    with open(file_path, "w") as file:
        json.dump(keys, file, indent=4)

def generate_custom_key(month):
    letters = string.ascii_lowercase
    digits = string.digits
    
    segments = []
    for _ in range(3):
        segment = ''.join(random.choice(letters) for _ in range(3))
        segment += random.choice(digits)
        segment_list = list(segment)
        random.shuffle(segment_list)
        segments.append(''.join(segment_list))
    
    key_prefix = f"{month}m"
    return f"{key_prefix}-{segments[0]}-{segments[1]}-{segments[2]}"

def generate_key(keys, month, amount, quantity, file_path):
    new_keys = []
    for _ in range(quantity):
        key = generate_custom_key(month)
        new_keys.append({"key": key, "month": month, "amount": amount})
    keys.extend(new_keys)
    save_keys_to_file(keys, file_path)

def list_keys(keys):
    return keys

def delete_key(keys, key):
    updated_keys = [key_data for key_data in keys if key_data["key"] != key]
    save_keys_to_file(updated_keys, FILE_PATH)

def clear_file(file_path):
    save_keys_to_file([], file_path)

def exit_program():
    print("Exiting program.")
    exit()

if __name__ == "__main__":
    main_menu()