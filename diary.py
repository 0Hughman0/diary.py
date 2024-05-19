import pathlib
import base64
import subprocess
import tempfile
import shutil
import datetime
import getpass
import argparse
import os
import sys

from cryptography.fernet import Fernet

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ONE_DAY = datetime.timedelta(days=1)

SALT = os.getenv('DIARY_SALT', '\xf07\xc1:\xee:P^\x84\xd5\xf5\xa2c}~\xf1').encode()
TEXT_EDITOR = os.getenv('DIARY_TEXT_EDITOR', "C:/Program Files/Notepad++/notepad++.exe")

TEXT_EDITOR_READ_OPTIONS = os.getenv('DIARY_TEXT_EDITOR_READ_OPTIONS',
                                     ','.join(['-nosession', '-notabbar', '-multiInst', '-ro'])).split(',')
TEXT_EDITOR_NEW_OPTIONS = os.getenv('DIARY_TEXT_EDITOR_NEW_OPTIONS',
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


def get_entry_list(diary_dir: pathlib.Path) -> tuple[list[tuple[datetime.date, pathlib.Path]], list[pathlib.Path], datetime.date]:
    date_files = []
    non_date_files = []

    for entry in diary_dir.iterdir():
        if not entry.is_file():
            continue

        try:
            date = datetime.datetime.strptime(entry.name, '%Y-%m-%d.txt').date()
            date_files.append((date, entry))
        except ValueError:
            non_date_files.append(entry)
    
    date_files.sort(key=lambda v: v[0])

    if date_files:
        day_zero = date_files[0][0]
    else:
        day_zero = datetime.date.today()

    return date_files, non_date_files, day_zero


def int_to_date(day_zero: datetime.date, nafter: int) -> datetime.date:
    if nafter >= 0:
        return day_zero + ONE_DAY * nafter
    else:
        return datetime.date.today() + (ONE_DAY * (nafter + 1))


def parse_name(name, day_zero):
    if name is None:
        name = f'{str(datetime.date.today())}.txt'

    name_is_index = False
    
    try:
        index = int(name)
        name_is_index = True
    except ValueError:
        name_is_index = False
    
    if name_is_index:
        name = str(int_to_date(day_zero, index))
    
    if not name.endswith('.txt'):
        name = name + '.txt'

    return name


def write(name, template, diary_dir):
    diary_dir = pathlib.Path(diary_dir).expanduser()

    if not diary_dir.exists():
        print("Creating diary directory:", diary_dir)
        diary_dir.mkdir()

    date_list, nondate_list, day_zero = get_entry_list(diary_dir)

    name = parse_name(name, day_zero)

    file = diary_dir / name

    if file.exists():
        raise RuntimeError("Diary entry already exists")
    
    print("Launching editor")

    text = get_tmp_text(template)

    key = get_key()

    cyphertext = encrypt_text(text=text, key=key)
    
    with open(file, 'wb') as f:
        f.write(cyphertext)


def read(name: str, diary_dir):
    diary_dir = pathlib.Path(diary_dir).expanduser()

    date_list, nondate_list, day_zero = get_entry_list(diary_dir)

    name = parse_name(name, day_zero)

    file = pathlib.Path(name)

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

    date_entries, nondate_entries, day_zero = get_entry_list(diary_dir)

    print("Dated entries:")

    for date, entry in date_entries:

        print(f'{(date - day_zero).days}:',  entry.name)

    print("Non dated entries:")

    return date_entries, nondate_entries


def main(args):
    app = argparse.ArgumentParser(description="Encrypted diary maker")
    app.add_argument('cmd', choices=['new', 'read', 'list'], help="New, create new entry. Read, read a specific entry. List, list entries.")
    app.add_argument('-n', '--name', help="Name of diary entry file, defaults to today's date. For read can also be an index, corresponding to output of list.")
    app.add_argument('-t', '--template', default='template.txt', help="Template to use for diary entry.")
    app.add_argument('-d', '--diary-dir', default=DIARY_DIR, help="Directory to put the diary entries into.")

    args = app.parse_args(args)

    match args.cmd:
        case 'new':
            return write(args.name, args.template, args.diary_dir)
        case 'read':
            return read(args.name, args.diary_dir)
        case 'list':
            return list_entries(args.diary_dir)


if __name__ == '__main__':
    main(sys.argv[1:])
