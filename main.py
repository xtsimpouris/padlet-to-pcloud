from utils import loadSettings, saveSettings, cleanUp
import re
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import xml.etree.ElementTree as ET
import os

WEBDAV_ENDPOINTS = {
    "api":  "https://webdav.pcloud.com",
    "eapi": "https://ewebdav.pcloud.com",
}

def webdav_auth(settings):
    return HTTPBasicAuth(settings["pcloud"]["email"], settings["pcloud"]["password"])

def webdav_url(settings, path=""):
    base = WEBDAV_ENDPOINTS[settings["pcloud"]["endpoint"]]
    return base + path

def listfolder(settings, folder):
    auth = webdav_auth(settings)
    url = webdav_url(settings, folder)
    resp = requests.request("PROPFIND", url, auth=auth, headers={"Depth": "1"})
    if resp.status_code == 401:
        print("pCloud login failed, check email and password.")
        exit()
    if resp.status_code == 404:
        return None
    root = ET.fromstring(resp.text)
    ns = {"d": "DAV:"}
    files = {}
    for response in root.findall("d:response", ns):
        href = response.findtext("d:href", namespaces=ns) or ""
        name = href.rstrip("/").split("/")[-1]
        name = requests.utils.unquote(name)
        if not name or requests.utils.unquote(href).rstrip("/") == folder.rstrip("/"):
            continue
        x = re.search(r"^[0-9]{4}-[0-9]{2}-[0-9]{2} ([0-9]+).*?\\..*", name)
        if not x:
            continue
        size_el = response.find(".//d:getcontentlength", ns)
        size = int(size_el.text) if size_el is not None else 0
        files[x[1]] = {"name": name, "size": size, "padlet_id": x[1]}
    return files

def upload(settings, local_path, folder):
    filename = os.path.basename(local_path)
    url = webdav_url(settings, folder.rstrip("/") + "/" + filename)
    with open(local_path, "rb") as f:
        resp = requests.put(url, data=f, auth=webdav_auth(settings))
    return resp.status_code in (200, 201, 204)

settings = loadSettings()

existing_files = listfolder(settings, settings["pcloud"]["folder"])
if existing_files is None:
    print("pCloud folder '%s' is not valid, please provide a valid one" % settings["pcloud"]["folder"])
    del settings["pcloud"]["folder"]
    saveSettings(settings)
    exit()

print("Identified %d files already in pCloud" % len(existing_files))

posts = {}
hash_id = "https://padlet.com/api/10/wishes?wall_hashid=%s&page_start=" % settings["padlet"]["wallid"]
while hash_id:
    print("Downloading %s ..." % hash_id)

    response = requests.get(hash_id)
    data = response.json()

    for wish in data.get("data", []):
        posts[wish["id"]] = wish

    if not data.get("meta", {}).get("next", False):
        break

    hash_id = "https://padlet.com/api/10/wishes?wall_hashid=%s&page_start=%s" % (
        settings["padlet"]["wallid"], data.get("meta", {}).get("next", False))

print("Let's start downloading")
for post_id in posts:
    post = posts[post_id]["attributes"]

    if str(post.get("id", "")) in existing_files:
        continue

    created_at = datetime.strptime(post["created_at"], '%Y-%m-%dT%H:%M:%S.%fZ')

    title = cleanUp(post.get("body", ""))
    if not title:
        title = cleanUp(post.get("headline", ""))

    final_name = ("%s %s %s" % (created_at.strftime("%Y-%m-%d"), str(post.get("id", "")), title)).strip()
    final_name += "." + post["attachment_link"]["extension"]

    print("Downloading.. %s" % final_name, end="")
    response = requests.get(post["attachment"])
    if response.status_code == 200:
        with open(final_name, "wb") as f:
            for chunk in response:
                f.write(chunk)
        print(" ..Done")
    else:
        print(" ..Error!!")
        continue

    print("Uploading.. %s" % final_name, end="")
    if upload(settings, final_name, settings["pcloud"]["folder"]):
        print(" ..Done")
    else:
        print(" ..Error!!")

    os.unlink(final_name)
