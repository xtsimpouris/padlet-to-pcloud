from yaml import safe_load, dump
from getpass import getpass
from cryptography.fernet import Fernet
import os
import re
import stat

SETTINGS_FILENAME = "settings.yaml"
KEYFILE_PATH = os.path.expanduser("~/.pcloud_keyfile")

def _load_or_create_key():
    if os.path.exists(KEYFILE_PATH):
        with open(KEYFILE_PATH, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(KEYFILE_PATH, "wb") as f:
        f.write(key)
    os.chmod(KEYFILE_PATH, stat.S_IRUSR | stat.S_IWUSR)
    return key

def _encrypt(plaintext):
    return Fernet(_load_or_create_key()).encrypt(plaintext.encode()).decode()

def _decrypt(ciphertext):
    return Fernet(_load_or_create_key()).decrypt(ciphertext.encode()).decode()

def loadSettings():
    settings = {}
    try:
        with open(SETTINGS_FILENAME, 'r') as file:
            settings = safe_load(file)
    except:
        pass

    if "pcloud" not in settings:
        settings["pcloud"] = {}

    if "email" not in settings["pcloud"] or settings["pcloud"]["email"].strip() == "":
        email = input("Please provide email for pCloud: ")
        settings["pcloud"]["email"] = email.strip()

    # Migrate plaintext password to encrypted form if present
    if "password" in settings["pcloud"] and settings["pcloud"]["password"]:
        plaintext = str(settings["pcloud"].pop("password"))
        settings["pcloud"]["password_enc"] = _encrypt(plaintext)

    if "password_enc" not in settings["pcloud"] or not settings["pcloud"]["password_enc"]:
        password = getpass("Please provide password for pCloud: ")
        settings["pcloud"]["password_enc"] = _encrypt(password.strip())

    if "folder" not in settings["pcloud"] or settings["pcloud"]["folder"].strip() == "":
        folder = input("Please provide folder for pCloud: ")
        settings["pcloud"]["folder"] = folder.strip().rstrip("/")

    if "endpoint" not in settings["pcloud"] or settings["pcloud"]["endpoint"].strip() == "":
        endpoint = input("Please provide endpoint for pCloud (eapi or api): ")
        settings["pcloud"]["endpoint"] = endpoint.strip()

    if "padlet" not in settings:
        settings["padlet"] = {}

    if "wallid" not in settings["padlet"] or settings["padlet"]["wallid"].strip() == "":
        wallid = input("Please provide wallid for padlet: ")
        settings["padlet"]["wallid"] = wallid.strip()

    saveSettings(settings)

    # Expose decrypted password in memory only — never written back to disk
    settings["pcloud"]["password"] = _decrypt(settings["pcloud"]["password_enc"])
    return settings

def saveSettings(settings):
    import copy
    safe = copy.deepcopy(settings)
    safe.get("pcloud", {}).pop("password", None)
    with open(SETTINGS_FILENAME, 'w') as file:
        dump(safe, file, allow_unicode=True)

def cleanUp(t, max_len = 100):
    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
    t = tag_re.sub('', t)

    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
    "]+", re.UNICODE)
    t = emoji_pattern.sub('', t)

    t = t.replace("/", "..")
    t = t.replace("\\", "..")
    t = t.replace("!", ", ")
    t = t.replace("?", ", ")
    t = t.replace(":", ", ")
    t = t.replace('”', " ")
    t = t.replace('"', " ")
    t = t.replace('»', " ")
    t = t.replace('«', " ")
    t = t.replace(';', ", ")
    t = t.replace('⁉', ", ")
    t = t.replace('“', " ")

    t = t.replace('.', " . ")
    t = t.replace(',', " , ")
    t = t.replace('(', " ( ")
    t = t.replace(')', " ) ")
    t = t.replace('⏰', " ")
    t = t.replace('—', " - ")
    t = t.replace('-', " - ")


    t = t.strip()   
    t = t.rstrip(".")
    t = t.rstrip(",")

    parts = t.split(" ")
    t = ""
    for part in parts:
        part = part.strip()
        if part == "":
            continue

        if part == "." or part == ",":
            t = t + part
        else:
            t = t + " " + part

        t = t.replace(',,', ",")
        t = t.replace('( ', "(")
        t = t.replace(' )', ")")

        if len(t) > max_len:
            break

    t = t.rstrip(".")
    t = t.rstrip(",")
    return t.strip()
