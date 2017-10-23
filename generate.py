#!/usr/bin/env python3
import os
import shutil
import hashlib
import json

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat

from bs4 import BeautifulSoup

xml_template = """
<?xml version='1.0' encoding='UTF-8'?>
<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>
  <app appid='{id}'>
    <updatecheck codebase='https://korylprince.github.io/chrome_icons/{app}/{id}.crx' version='{version}' />
  </app>
</gupdate>
""".strip()

icon_template = """
<div class="icon">
    <a href="{app}/{id}.crx">
        <img src="{app}/icon128.png" />
        <span>{name}</span>
    </a>
</div>
<a href="#" class="advanced" data-change="{id}">advanced</a>
<div id="{id}" class="icon-info hidden">
    <table class="bordered striped centered">
        <tbody>
            <tr>
                <td>id</td>
                <td>{id}</td>
            </tr>
            <tr>
                <td>update URL</td>
                <td><a href="{app}/update.xml">update.xml</a></td>
            </tr>
        </tbody>
    </table>
</div>
""".strip()

def get_last_modified(app):
    mtimes = []
    for f in os.listdir(os.path.join(app, "src")):
        mtimes.append(os.path.getmtime(os.path.join(app, "src", f)))
    return max(mtimes)

def get_app_id(app):
    #help from https://stackoverflow.com/questions/16993486/how-to-programmatically-calculate-chrome-extension-id
    with open(os.path.join(app, "key.pem"), "rb") as f:
        data = f.read()
    private_pem = load_pem_private_key(data, None, default_backend())
    public_der = private_pem.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    sha = hashlib.sha256(public_der).hexdigest()

    prefix = sha[:32]
    hash = []
    for char in prefix:
        hash.append(chr(int(char, 16) + ord("a")))
    return "".join(hash)

def get_app_name(app):
    with open(os.path.join(app, "src/manifest.json")) as f:
        manifest = json.load(f)
        return manifest["name"]

def get_app_version(app):
    with open(os.path.join(app, "src/manifest.json")) as f:
        manifest = json.load(f)
        return manifest["version"]

def generate_app(app):
    print("Generating", app + ": ", end="")

   #remove old files
    shutil.rmtree(os.path.join(app, "dist"), ignore_errors=True)
    os.makedirs(os.path.join(app, "dist"), exist_ok=True)

   #copy manifest
    shutil.copy(os.path.join(app, "src/manifest.json"), os.path.join(app, "dist"))

   #generate icons
    for size in [16, 24, 32, 48, 128]:
        os.system("convert ./{app}/src/icon.png -resize {size}x{size} ./{app}/dist/icon{size}.png".format(app=app, size=size))
    shutil.copy(os.path.join(app, "dist/icon128.png"), app)

    #generate app
    if os.path.isfile(os.path.join(app, "key.pem")):
        os.system("google-chrome-stable --user-data-dir=/tmp/chrome_profile --pack-extension={app}/dist --pack-extension-key={app}/key.pem --no-message-box".format(app=app))
    else:
        os.system("google-chrome-stable --user-data-dir=/tmp/chrome_profile --pack-extension={app}/dist --no-message-box".format(app=app))
        os.rename(os.path.join(app, "dist.pem"), os.path.join(app, "key.pem"))

    os.rename(os.path.join(app, "dist.crx"), os.path.join(app, get_app_id(app) + ".crx"))

    #update .last_modified
    with open(os.path.join(app, ".last_modified"), "w") as f:
        f.write(str(get_last_modified(app)))

    print(get_app_id(app))

# open index.html
with open("index.html") as f:
    html = BeautifulSoup(f, "lxml")

icons_div = html.find_all("div", class_="icons")[0]
icons_div.clear()

for app in sorted(os.listdir(".")):
    if os.path.isdir(app) and app not in (".git"):
        #generate app if not created or unchanged
        try:
            with open(os.path.join(app, ".last_modified")) as f:
                try:
                    if float(f.read().strip()) < get_last_modified(app):
                        generate_app(app)
                    else:
                        print("Up to date:", app + ":" + get_app_id(app))
                except ValueError:
                    print(app + ": Invalid .last_modified")
                    generate_app(app)
        except FileNotFoundError:
            generate_app(app)
        
        #generate update.xml
        with open(os.path.join(app, "update.xml"), "w") as f:
            f.write(xml_template.format(app=app, id=get_app_id(app), version=get_app_version(app)) + "\n")
        
        #insert icon to index.html
        icons_div.append(BeautifulSoup(icon_template.format(app=app, id=get_app_id(app), name=get_app_name(app)), "html.parser"))

with open("index.html", "w") as f:
    f.write(html.prettify())
