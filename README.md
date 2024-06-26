# Diary.py

Simple CLI diary.

Diary entries are encrypted on using a password, via the `cryptography` package.

## Installation

Head to the [Releases](https://github.com/0Hughman0/diary.py/releases/tag/v0.1.0) page and download the appropriate build, unzip and use.

## Usage

To make an entry:

```
diary new
```

To list entries:

```
diary list
```

To read an entry:

```
diary read 0  # first entry
```

```
diary read -1  # most recent entry
```

For full command line options:

```
diary -h
```

## Advanced Configuration

### Text editor. 

By default entries are created/ read using notepad++, which `diary.py` will try to launch from `C:/Program Files/Notepad++/notepad++.exe`.

A different executable can be configured by setting the environment variable `DIARY_TEXT_EDITOR`. You will likely also need to add comma separated command line options by also setting `DIARY_TEXT_EDITOR_READ_OPTIONS` and `DIARY_TEXT_EDITOR_NEW_OPTIONS`.

### Diary directory.

The directory where entries are kept by default is `~/diary`. 

This can be configured either by providing the `--diary-dir` command line argument, or by setting the `DIARY_DIR` environment variable.

### Password Salt.

Before generating the key for encrypting your entries, the password you use is salted with a fixed string of bytes.

If you wish, you can use your own fixed string of bytes, which can be set using the `DIARY_SALT` environment variable.

# Disclaimer

This is a little hobby project. It's not comprehensively tested. Use at your own risk... none-the-less bug reports/ PRs welcome!
