import pathlib
import base64
import subprocess
import tempfile
import shutil
import datetime
import getpass
import argparse
import os

from cryptography.fernet import Fernet

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT = os.getenv('DIARY_SALT', '\xf07\xc1:\xee:P^\x84\xd5\xf5\xa2c}~\xf1').encode()
TEXT_EDITOR = os.getenv('DIARY_TEXT_EDITOR', "C:/Program Files/Notepad++/notepad++.exe")

TEXT_EDITOR_READ_OPTIONS = os.getenv('DIARY_TEXT_EDITOR_READ_OPTIONS',
                                     ','.join(['-nosession', '-notabbar', '-multiInst', '-ro'])).split(',')
TEXT_EDITOR_NEW_OPTIONS = os.getenv('DIARY_TEXT_EDITOR_READ_OPTIONS', 
                                    ','.join(['-nosession', '-notabbar', '-multiInst',])).split(',')

DIARY_DIR = os.getenv('DIARY_DIR', "~/diary")


def keyify_pwd(pwd: str):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=480000,
    )

    return base64.urlsafe_b64encode(kdf.derive(pwd.encode()))


def encrypt_text(text: bytes, key: bytes):
    f = Fernet(key)
    return f.encrypt(text)


def decrypt_text(cyphertext: bytes, key: bytes):
    f = Fernet(key)
    return f.decrypt(cyphertext)


def get_tmp_text(template: str | pathlib.Path) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        holding_file = os.path.join(temp_dir, 'temp.txt')
        shutil.copy(template, holding_file)

        result = subprocess.run([TEXT_EDITOR, *TEXT_EDITOR_NEW_OPTIONS, str(holding_file)])
        
        if result.returncode == 0:
            with open(holding_file, 'rb') as fs:
                contents = fs.read()
        else:
            raise RuntimeError("Text editor did not run properly")
            
    return contents


def display_tmp_text(text: bytes):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, 'tmp.txt')
        
        with open(temp_file, 'wb') as fs:
            fs.write(text)
        
        subprocess.run([TEXT_EDITOR, *TEXT_EDITOR_READ_OPTIONS, temp_file])


def get_key():
    passwords_match = False

    while not passwords_match:
        pwd = getpass.getpass("Enter password: ")
        pwd2 = getpass.getpass("Confirm password: ")

        if pwd == pwd2:
            passwords_match = True
        else:
            print("Passwords don't match, please try again")

    return keyify_pwd(pwd)


def get_entry_list(diary_dir) -> list[pathlib.Path]:
    entries = [entry for entry in diary_dir.iterdir() if entry.is_file()]
    
    entries.sort()

    return entries


def write(name, template, diary_dir):
    if name is None:
        name = f'{str(datetime.date.today())}.txt'
    elif not name.endswith('.txt'):
        name = name + '.txt'

    diary_dir = pathlib.Path(diary_dir).expanduser()

    if not diary_dir.exists():
        print("Creating diary directory:", diary_dir)
        diary_dir.mkdir()

    file = diary_dir / name

    if file.exists():
        raise RuntimeError("Diary entry already exists")
    
    print("Launching editor")

    text = get_tmp_text(template)

    key = get_key()

    cyphertext = encrypt_text(text=text, key=key)
    
    with open(file, 'wb') as f:
        f.write(cyphertext)


def read(input: str, diary_dir):
    diary_dir = pathlib.Path(diary_dir).expanduser()

    if input is None:
        input = str(datetime.date.today())

    input_is_index = False
    
    try:
        index = int(input)
        input_is_index = True
    except ValueError:
        input_is_index = False
    
    if input_is_index:
        entries = get_entry_list(diary_dir)
        file = entries[index]
    else:
        if not input.endswith('.txt'):
            input = input + '.txt'

        file = pathlib.Path(input)
    
    if not file.exists():
        file = diary_dir / file

    if not file.exists():
        raise RuntimeError("Entry not found", file)

    print("Reading", file)

    key = get_key()

    with open(file, 'rb') as fs:
        cyphertext = fs.read()

    text = decrypt_text(cyphertext, key)

    display_tmp_text(text)


def list_entries(diary_dir):
    diary_dir = pathlib.Path(diary_dir).expanduser()

    print("Entries in", diary_dir)

    entries = get_entry_list(diary_dir)

    for i, entry in enumerate(entries):
        print(f'{i}:',  entry.name)

    return entries


def main():
    app = argparse.ArgumentParser(description="Encrypted diary maker")
    app.add_argument('cmd', choices=['new', 'read', 'list'], help="New, create new entry. Read, read a specific entry. List, list entries.")
    app.add_argument('-n', '--name', help="Name of diary entry file, defaults to today's date. For read can also be an index, corresponding to output of list.")
    app.add_argument('-t', '--template', default='template.txt', help="Template to use for diary entry.")
    app.add_argument('-d', '--diary-dir', default=DIARY_DIR, help="Directory to put the diary entries into.")

    args = app.parse_args()

    match args.cmd:
        case 'new':
            write(args.name, args.template, args.diary_dir)
        case 'read':
            read(args.name, args.diary_dir)
        case 'list':
            list_entries(args.diary_dir)


if __name__ == '__main__':
    main()
