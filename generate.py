#!/usr/bin/env python3
import os
import shutil
import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat

xml_template = """
<?xml version='1.0' encoding='UTF-8'?>
<gupdate xmlns='http://www.google.com/update2/response' protocol='2.0'>
  <app appid='{id}'>
    <updatecheck codebase='https://raw.githubusercontent.com/korylprince/chrome_icons/master/{app}/{id}.crx' version='2.0' />
  </app>
</gupdate>
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

    #generate app
    if os.path.isfile(os.path.join(app, "key.pem")):
        os.system("google-chrome-stable --user-data-dir=/tmp/chrome_profile --pack-extension={app}/dist --pack-extension-key={app}/key.pem --no-message-box".format(app=app))
    else:
        os.system("google-chrome-stable --user-data-dir=/tmp/chrome_profile --pack-extension={app}/dist --no-message-box".format(app=app))
        os.rename(os.path.join(app, "dist.pem"), os.path.join(app, "key.pem"))

    os.rename(os.path.join(app, "dist.crx"), os.path.join(app, get_app_id(app) + ".crx"))

    #generate update.xml
    with open(os.path.join(app, "update.xml"), "w") as f:
        f.write(xml_template.format(app=app, id=get_app_id(app)) + "\n")

    #update .last_modified
    with open(os.path.join(app, ".last_modified"), "w") as f:
        f.write(str(get_last_modified(app)))

    print(get_app_id(app))

for app in os.listdir("."):
    if os.path.isdir(app) and app not in (".git", "docs"):
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
