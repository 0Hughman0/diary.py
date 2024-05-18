import subprocess
import getpass
import importlib
import datetime
from pathlib import Path

import pytest

import diary


with open('template.txt') as fs:
    TEMPLATE_CONTENT = fs.read()

TODAY_FILE = f'{str(datetime.date.today())}.txt'
ONE_DAY = datetime.timedelta(days=1)


@pytest.fixture
def patch_editor(monkeypatch):
    def make_patch(content, returncode):

        class Patched:

            def __init__(self, content):
                self.content = content
                self.returncode = returncode

                self.opened_content = None
                self.arguments = None
            
            def __call__(self, arguments):
                self.arguments = arguments
                
                path = arguments[-1]

                with open(path, 'r') as fs:
                    self.opened_content = fs.read()

                if self.content is not None:             
                    with open(path, 'w') as fs:
                        fs.write(content)

                return self
        
        patch = Patched(content)

        monkeypatch.setattr(subprocess, 'run', patch)

        return patch

    return make_patch


@pytest.fixture
def setup_main(monkeypatch, tmp_path):
    monkeypatch.setattr(getpass, 'getpass', lambda msg: 'pwd')

    key = diary.keyify_pwd('pwd')
    
    def decoder(text: bytes):
        return diary.decrypt_text(text, key)

    def encoder(text: bytes):
        return diary.encrypt_text(text, key)
    
    monkeypatch.setattr(diary, 'DIARY_DIR', tmp_path)

    return decoder, encoder


def test_env_vars(monkeypatch):
    assert diary.SALT == '\xf07\xc1:\xee:P^\x84\xd5\xf5\xa2c}~\xf1'.encode()
    
    monkeypatch.setenv('DIARY_SALT', 'test salt')
    importlib.reload(diary)
    assert diary.SALT == b'test salt'

    assert diary.TEXT_EDITOR == "C:/Program Files/Notepad++/notepad++.exe"
    monkeypatch.setenv('DIARY_TEXT_EDITOR', 'test editor')
    importlib.reload(diary)
    assert diary.TEXT_EDITOR == 'test editor'
    
    assert diary.TEXT_EDITOR_NEW_OPTIONS == ['-nosession', '-notabbar', '-multiInst']
    monkeypatch.setenv('DIARY_TEXT_EDITOR_NEW_OPTIONS', 'test,editor,new,args')
    importlib.reload(diary)
    assert diary.TEXT_EDITOR_NEW_OPTIONS == ['test', 'editor', 'new', 'args']

    assert diary.TEXT_EDITOR_READ_OPTIONS == ['-nosession', '-notabbar', '-multiInst', '-ro']
    monkeypatch.setenv('DIARY_TEXT_EDITOR_READ_OPTIONS', 'test,editor,read,args')
    importlib.reload(diary)
    assert diary.TEXT_EDITOR_READ_OPTIONS == ['test', 'editor', 'read', 'args']
    
    assert diary.DIARY_DIR == "~/diary"
    monkeypatch.setenv('DIARY_DIR', 'testdiarydir')
    importlib.reload(diary)
    assert diary.DIARY_DIR == 'testdiarydir'


def test_new(setup_main, patch_editor, tmp_path):
    decoder, encoder = setup_main
    editor = patch_editor('test content', returncode=0)
    
    diary.main(['new'])
    
    file = tmp_path / TODAY_FILE

    assert file.exists()
    assert not Path(editor.arguments[0]).exists()
    assert editor.arguments[1:-1] == diary.TEXT_EDITOR_NEW_OPTIONS
    
    assert editor.content == 'test content'
    assert decoder(file.read_bytes()) == b'test content'

    assert editor.opened_content == TEMPLATE_CONTENT

    # test can't repeat entry
    with pytest.raises(RuntimeError):
        diary.main(['new'])

    # test editor returns error
    editor = patch_editor('test return error', returncode=-1)

    with pytest.raises(RuntimeError):
        diary.main(['new', '-n', 'returning-error'])

    # test custom name
    editor = patch_editor('test content custom name', returncode=0)
    
    diary.main(['new', '-n', 'test-name'])

    file = tmp_path / 'test-name.txt'

    assert file.exists()
    assert decoder(file.read_bytes()) == b'test content custom name'

    # test custom tempalte
    template_path = tmp_path / 'custom_template.txt'
    template_path.write_text('test custom template')

    editor = patch_editor('test content custom template', returncode=0)

    diary.main(['new', '-n', 'test-custom-template', '--template', str(template_path)])

    assert editor.opened_content == 'test custom template'

    # test custom diary dir

    subdir = tmp_path / 'subdir'
    subdir.mkdir()

    editor = patch_editor('test content custom diarydir', returncode=0)

    diary.main(['new', '-n', 'custom-dir', '--diary-dir', str(subdir)])

    file = subdir / 'custom-dir.txt'

    assert file.exists()


def test_read(setup_main, patch_editor, tmp_path):
    decoder, encoder = setup_main
    
    dates = []

    for i in range(5):
        editor = patch_editor(f'read test entry {4 - i}', 0)
        date = datetime.date.today() - (ONE_DAY * i)
        dates.append(date)
        
        diary.main(['new', '-n', str(date)])
    
    editor = patch_editor(None, 0)

    diary.main(['read'])

    assert editor.opened_content == 'read test entry 4'

    # test pass integer

    diary.main(['read', '-n', '0'])

    assert editor.opened_content == 'read test entry 0'


def test_list(setup_main, patch_editor, tmp_path):
    decoder, encoder = setup_main

    editor = patch_editor('test list content', 0)

    dates = []

    for i in range(5):
        date = datetime.date.today() - (ONE_DAY * i)
        dates.append(date)
        
        diary.main(['new', '-n', str(date)])

    dates.sort()
    
    entries = diary.main(['list'])

    assert [e.name for e in entries] == [f'{str(e)}.txt' for e in dates]
