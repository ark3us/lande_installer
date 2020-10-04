'''
    File name: lande_installer.py
    Author: ark3us
    Date created: 10/04/2020
    Date last modified: 10/04/2020
    Python Version: 3.8
'''

import shutil
import simplejson as json
import mega
import os
import requests
import pick
import patoolib
import stat
import tempfile
import traceback
import wget
from bs4 import BeautifulSoup
from typing import Tuple

BASE_URL = "http://5.9.105.28"
NWNCLIENT_URL = "http://5.9.105.28/customdownload/client/NWNclient.zip"
NWNCX_URL = "https://mega.nz/file/x1g2TA4J#BFB2U9fRx0N8LqlEA5133Rhlxx7k0DYukCQWotLm3no"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
MAIN_PATH = os.path.join(SCRIPT_PATH, "NWNclient")
SUBPATHS = {
    "dialog": MAIN_PATH,
    "hak": os.path.join(MAIN_PATH, "hak"),
    "override": os.path.join(MAIN_PATH, "override"),
    "tlk": os.path.join(MAIN_PATH, "tlk"),
    "portraits": os.path.join(MAIN_PATH, "portraits"),
    "music": os.path.join(MAIN_PATH, "music"),
}
DOWNLOAD_PATH = os.path.join(SCRIPT_PATH, "downloads")
DOWNLOAD_OLD = os.path.join(DOWNLOAD_PATH, "old")
ALLOWED_ARCHIVES = [
    "zip",
    "7z"
]
SKIP = [
    "NWNclient",
    "goog.gl",
]


def save_info(archive_path: str, info: dict):
    if not info:
        return
    try:
        info_file = "{}.json".format(archive_path)
        with open(info_file, "w") as fp:
            json.dump(info, fp)
    except:
        traceback.print_exc()


def check_install(url: str, archive_path: str) -> Tuple[bool, dict]:
    info_file = "{}.json".format(archive_path)
    try:
        res = requests.head(url)
        res.raise_for_status()

        new_info = {
            "Last-Modified": res.headers.get("Last-Modified"),
            "Content-Length": res.headers.get("Content-Length"),
        }

        if not os.path.exists(archive_path):
            print("Il file non è presente:", url)
            return False, new_info
            
        file_size = os.path.getsize(archive_path)
        # If the file aready exists, just check the length
        if not os.path.exists(info_file) and str(file_size) == str(new_info.get("Content-Length")):
            print("Nessuna descrizione trovata, ma file già scaricato:", url)
            return True, new_info
        
        with open(info_file) as fp:
            info = json.load(fp)

        if new_info.get("Last-Modified") == info.get("Last-Modified") and new_info.get("Content-Length") == info.get("Content-Length"):
            print("File già scaricato:", url)
            return True, new_info
        else:
            print("Trovato update per il file:", url)
            return False, new_info
    except:
        traceback.print_exc()
        return False, None


def download(url: str, archive_path: str) -> bool:
    print("Scaricando %s -> %s ..." % (url, archive_path))
    try:
        if os.path.exists(archive_path):
            shutil.move(archive_path, os.path.join(DOWNLOAD_OLD, os.path.basename(archive_path)))

        if "mega.nz" in url:
            m = mega.Mega()
            m.download_url(url, dest_filename=archive_path)
        else:
            wget.download(url, out=archive_path)
            print("\n")
        print("Archivio scaricato correttamente: %s" % archive_path)
        return True
    except:
        traceback.print_exc()
        return False


def get_dest_path(url: str) -> str:
    subpath = None
    for key, val in SUBPATHS.items():
        if key in url:
            subpath = val
            break
    return subpath


def install(archive_path: str, dest_path: str) -> bool:
    print("Estrazione: %s -> %s" % (archive_path, dest_path))
    tmp_dir = tempfile.mkdtemp()
    try:
        patoolib.extract_archive(archive_path, verbosity=1, outdir=tmp_dir, interactive=False)
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                ftmp = os.path.join(root, f)
                os.chmod(ftmp, stat.S_IWRITE)  # Fix permissions
                fdst = os.path.join(dest_path, f)
                shutil.move(ftmp, fdst)
                os.chmod(fdst, stat.S_IWRITE)

        print("Archivio estratto correttamente: %s\n" % archive_path)
        return True
    except:
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(tmp_dir)


def check_continue():
    title = "Si è verificato un errore. Vuoi continuare?"
    options = ["Si", "No"]
    _, index = pick.pick(options, title)
    return index == 0


def install_haks(soup: BeautifulSoup, force=False):
    for a in soup.findAll("a"):
        href = a.get("href")
        if not href:
            continue            
        if any(s in href for s in SKIP):
            print("\nOmesso: %s" % href)
            continue
        if not any(href.endswith(ext) for ext in ALLOWED_ARCHIVES):
            print("\nLink non supportato: %s" % href)
            continue

        print("\nArchivio: %s" % href)
        archive_path = os.path.join(DOWNLOAD_PATH, href.split("/")[-1])

        dest_path = get_dest_path(href)
        if not dest_path:
            print("Errore: Link non riconosciuto: %s" % href)
            continue

        is_installed, info = check_install(href, archive_path)
        if is_installed and not force:
            print("Archivio già installato: %s" % href)
            save_info(archive_path, info)
            continue
        
        if not is_installed:
            if not download(href, archive_path):
                print("Errore nello scaricamento dell'archivio: %s" % href)
                if check_continue():
                    continue
                else:
                    break

        if not install(archive_path, dest_path):
            print("Errore nell'installazione dell'archivio: %s" % href)
            if check_continue():
                continue
            else:
                break

        save_info(archive_path, info)


def install_nwnclient(force=False):
    archive_path = os.path.join(DOWNLOAD_PATH, NWNCLIENT_URL.split("/")[-1])
    is_installed, info = check_install(NWNCLIENT_URL, archive_path)
    if is_installed and not force:
        print("NWNclient già installato\n")
        save_info(archive_path, info)
        return
    if not is_installed:
        if not download(NWNCLIENT_URL, archive_path):
            print("Errore nello scaricamento del client: %s" % NWNCLIENT_URL)
            return
    try:
        print("Estrazione: %s -> %s" % (archive_path, SCRIPT_PATH))
        patoolib.extract_archive(archive_path, verbosity=1, outdir=SCRIPT_PATH, interactive=False)
        print("Archivio estratto correttamente: %s\n" % archive_path)
        return True
    except:
        traceback.print_exc()
        return False

def install_nwncx(force=False):
    archive_path = os.path.join(DOWNLOAD_PATH, "nwncx_lande_240615.7z")
    if not download(NWNCX_URL, archive_path):
        print("Errore nello scaricamento di nwncx: %s" % NWNCX_URL)
        return
    return install(archive_path, MAIN_PATH)


def main():
    res = requests.get(BASE_URL)
    soup = BeautifulSoup(res.content, features="html.parser")

    for _, val in SUBPATHS.items():
        if not os.path.exists(val):
            os.makedirs(val)

    if not os.path.exists(DOWNLOAD_OLD):
        os.makedirs(DOWNLOAD_OLD)

    global SKIP
    title = "Lingua del client:"
    options = ["Italiano", "Inglese"]
    _, index = pick.pick(options, title)
    if index == 0:
        SKIP.append("dialog_eng")
    else:
        SKIP.append("dialog_ita")

    reinstall = False
    title = "Desideri installare/reinstallare tutto o soltanto controllare eventuali update?"
    options = ["Controlla update", "Installa/reinstalla"]
    _, index = pick.pick(options, title)
    if index == 1:
        reinstall = True

    install_client = False
    title = "Vuoi installare il client nwn?"
    options = ["No, scarica/installa soltanto gli hak", "Si, scarica/installa nella cartella corrente"]
    _, index = pick.pick(options, title)
    if index == 1:
        install_client = True

    install_cx = False
    title = "Vuoi installare NWNCX?"
    options = ["Si, scarica/installa", "No"]
    _, index = pick.pick(options, title)
    if index == 0:
        install_cx = True

    try:
        if install_client:
            install_nwnclient(reinstall)
        
        install_haks(soup, force=reinstall)
        
        if install_cx:
            install_nwncx(reinstall)

    except:
        traceback.format_exc()

    finally:
        input("\n\nOperazione completata. Premere invio per terminare...")


if __name__ == "__main__":
    main()