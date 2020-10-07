#!/bin/env python3

'''
    File name: lande_installer.py
    Author: ark3us
    Date created: 10/04/2020
    Date last modified: 10/04/2020
    Python Version: 3.8
'''

import io
import logging
import mega
import os
import requests
import patoolib
import pkg_resources
import PySimpleGUI as sg
import shutil
import simplejson as json
import stat
import tempfile
import threading
import traceback
import wget
import webbrowser
from bs4 import BeautifulSoup
from typing import Text, Tuple, Dict, List

VERSION = "v2.5"
SETTINGS = "settings.json"
VERBOSITY = 1
RELEASE_URL = "https://api.github.com/repos/ark3us/lande_installer/releases/latest"
UPDATE_URL = "https://github.com/ark3us/lande_installer/releases/latest"
BASE_URL = "http://5.9.105.28"
NWNCLIENT_URL = "http://5.9.105.28/customdownload/client/NWNclient.zip"
NWNCX_URL = "https://mega.nz/file/x1g2TA4J#BFB2U9fRx0N8LqlEA5133Rhlxx7k0DYukCQWotLm3no"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
MAIN_PATH = os.path.join(SCRIPT_PATH, "NWNclient")
DOWNLOAD_PATH = os.path.join(SCRIPT_PATH, "downloads")
ALLOWED_ARCHIVES = [
    "zip",
    "7z"
]
SKIP = [
    "NWNclient",
    "goog.gl",
]
ERROR_FLAG = False
THREAD_EVENT = "LOG"
POPUP_EVENT = "POPUP"
WINDOW = None

def get_paths() -> Dict[str, str]:
    subpaths = {
        "dialog": MAIN_PATH,
        "hak": os.path.join(MAIN_PATH, "hak"),
        "override": os.path.join(MAIN_PATH, "override"),
        "tlk": os.path.join(MAIN_PATH, "tlk"),
        "portraits": os.path.join(MAIN_PATH, "portraits"),
        "music": os.path.join(MAIN_PATH, "music"),
    }
    return subpaths


def print_log(*argv, level=1):
    print(*argv)
    if VERBOSITY >= level and WINDOW:
        WINDOW.write_event_value(THREAD_EVENT, (" ".join(argv),))


def popup(msg: str):
    print(msg)
    if WINDOW:
        WINDOW.write_event_value(POPUP_EVENT, (msg,))


def set_error():
    global ERROR_FLAG
    ERROR_FLAG = True
    print_log(traceback.format_exc())
    logging.error(traceback.format_exc())


def save_info(archive_path: str, info: dict):
    if not info:
        return
    try:
        info_file = "{}.json".format(archive_path)
        with open(info_file, "w") as fp:
            json.dump(info, fp)
    except:
        set_error()


def check_install(url: str, archive_path: str) -> Tuple[bool, dict]:
    info_file = "{}.json".format(archive_path)
    try:
        res = requests.head(url)
        res.raise_for_status()

        new_info = {
            "Last-Modified": res.headers.get("Last-Modified"),
            "Content-Length": res.headers.get("Content-Length"),
        }

        if not os.path.exists(archive_path) and not os.path.exists(info_file):
            print_log("Non è presente nè il file nè i metadati:", url, level=2)
            return False, new_info
            
        elif os.path.exists(archive_path) and not os.path.exists(info_file):
            file_size = os.path.getsize(archive_path)
            # If the file aready exists, just check the length
            if str(file_size) == str(new_info.get("Content-Length")):
                print_log("Metadati non trovati, ma file già scaricato:", url, level=2)
                return True, new_info
            else:
                print_log("Metadati non trovati e file obsoleto:", url, level=2)
                return False, new_info
        
        elif os.path.exists(info_file):
            with open(info_file) as fp:
                info = json.load(fp)

            if new_info.get("Last-Modified") == info.get("Last-Modified") and new_info.get("Content-Length") == info.get("Content-Length"):
                print_log("Il file è già all'ultima versione:", url, level=2)
                return True, new_info
            else:
                print_log("Trovato update per il file:", url)
                return False, new_info

    except:
        set_error()
        return False, None


def download(url: str, archive_path: str) -> bool:
    print_log("Scaricando %s -> %s ..." % (url, archive_path))
    try:
        if os.path.exists(archive_path):
            os.remove(archive_path)

        if "mega.nz" in url:
            m = mega.Mega()
            m.download_url(url, dest_filename=archive_path)
        else:
            wget.download(url, out=archive_path)
            print("\n")
        print_log("Archivio scaricato correttamente: %s" % archive_path)
        return True
    except:
        set_error()
        return False


def get_dest_path(url: str) -> str:
    subpath = None
    for key, val in get_paths().items():
        if key in url:
            subpath = val
            break
    return subpath


def install(archive_path: str, dest_path: str) -> bool:
    print_log("Estrazione: %s -> %s" % (archive_path, dest_path))
    tmp_dir = tempfile.mkdtemp()
    try:
        patoolib.extract_archive(archive_path, verbosity=1, outdir=tmp_dir, interactive=False)
        for root, _, files in os.walk(tmp_dir):
            for f in files:
                ftmp = os.path.join(root, f)
                os.chmod(ftmp, os.stat(ftmp).st_mode | stat.S_IWRITE)  # Fix permissions
                fdst = os.path.join(dest_path, f)
                shutil.move(ftmp, fdst)
                os.chmod(fdst, os.stat(fdst).st_mode | stat.S_IWRITE)  # Fix permissions

        print_log("Archivio estratto correttamente: %s" % archive_path)
        return True
    except:
        set_error()
        return False
    finally:
        shutil.rmtree(tmp_dir)


def install_haks(soup: BeautifulSoup, force=False, dry_run=False, baseline=False) -> int:
    updates = 0
    for a in soup.findAll("a"):
        href = a.get("href")
        if not href:
            continue            
        if any(s in href for s in SKIP):
            print_log("\nOmesso: %s" % href, level=2)
            continue
        if not any(href.endswith(ext) for ext in ALLOWED_ARCHIVES):
            print_log("\nLink non supportato: %s" % href, level=2)
            continue

        print_log("\nArchivio: %s" % href)
        archive_path = os.path.join(DOWNLOAD_PATH, href.split("/")[-1])

        dest_path = get_dest_path(href)
        if not dest_path:
            print_log("Errore: Link non riconosciuto: %s" % href)
            continue

        is_installed, info = check_install(href, archive_path)
        if is_installed and not force:
            print_log("Contenuto già installato: %s" % href)
            if not dry_run:
                save_info(archive_path, info)
                if os.path.exists(archive_path):
                    print_log("Elimino l'archivio", level=2)
                    os.remove(archive_path)
            continue
        
        if not is_installed or not os.path.exists(archive_path):
            if dry_run:
                if baseline:
                    print_log("Richiesto salvataggio metadati:", href)
                else:
                    print_log("Richiesto download e installazione dell'archivio:", href)
                updates += 1
            elif not download(href, archive_path):
                print_log("Errore nello scaricamento dell'archivio: %s" % href)
                break

        if not dry_run:
            if not install(archive_path, dest_path):
                print_log("Errore nell'installazione dell'archivio: %s" % href)
                break
            updates += 1
            
        if not dry_run or baseline:
            print_log("Salvo i metadati", level=2)
            save_info(archive_path, info)
            if os.path.exists(archive_path):
                print_log("Elimino l'archivio", level=2)
                os.remove(archive_path)

    return updates


def install_nwnclient(force=False):
    archive_path = os.path.join(DOWNLOAD_PATH, NWNCLIENT_URL.split("/")[-1])
    is_installed, info = check_install(NWNCLIENT_URL, archive_path)
    if is_installed and not force:
        print_log("NWNclient già installato\n")
        save_info(archive_path, info)
        return
    if not is_installed:
        if not download(NWNCLIENT_URL, archive_path):
            print_log("Errore nello scaricamento del client: %s" % NWNCLIENT_URL)
            return
    try:
        print_log("Estrazione: %s -> %s" % (archive_path, SCRIPT_PATH))
        patoolib.extract_archive(archive_path, verbosity=1, outdir=SCRIPT_PATH, interactive=False)
        print_log("Archivio estratto correttamente: %s\n" % archive_path)
        return True
    except:
        set_error()
        return False


def install_nwncx(force=False):
    archive_path = os.path.join(DOWNLOAD_PATH, "nwncx_lande_240615.7z")
    if not download(NWNCX_URL, archive_path):
        print_log("Errore nello scaricamento di nwncx: %s" % NWNCX_URL)
        return
    return install(archive_path, MAIN_PATH)


def check_self_update() -> List[str]:
    res = requests.get(RELEASE_URL)
    ver = res.json().get("tag_name", "")
    assets = res.json().get("assets", {})
    ass = []
    if pkg_resources.parse_version(ver) > pkg_resources.parse_version(VERSION):
        print("Trovata nuova versione:", ver)
        for asset in assets:
            ass.append(asset.get("browser_download_url"))
    else:
        print("Hai già l'ultima versione dell'app")

    return ass


def main():
    logging.basicConfig(filename='error.log',level=logging.INFO)

    assets = check_self_update()

    settings = {
        "dialog": "Italiano",
        "mode": "Update",
        "downloads_path": DOWNLOAD_PATH,
        "nwnclient_path": MAIN_PATH,
        "nwnclient": False,
        "nwncx": True,
        "verbosity": 1,
    }

    if os.path.exists(SETTINGS):
        try:
            with open(SETTINGS) as fp:
                settings = json.load(fp)
        except:
            print_log("Errore nell'apertura del file di configurazione.")
            os.remove(SETTINGS)

    for _, val in get_paths().items():
        if not os.path.exists(val):
            os.makedirs(val)

    sg.theme("DarkAmber")

    col1 = [
        [sg.Text("--- Dialog ---")],
        [sg.Text("Lingua del client: "), sg.DropDown(["Italiano", "Inglese"], default_value=settings["dialog"])],
        [sg.Text("")],
        [sg.Text("--- Modalità di funzionamento ---")],
        [sg.Text("Modalità update: controlla se ci sono nuovi contenuti custom")],
        [sg.Text("Modalità (re)installazione: (re)installa tutto <- scegliere in caso di prima installazione")],
        [sg.Text("Modalità:"), sg.DropDown(["Update", "(Re)Installazione"], default_value=settings["mode"])],
        [sg.Text("")],
        [sg.Text("--- Sincronizzazione ---")],
        [sg.Text("Se è la prima volta che usi questa applicazione e hai già tutto installato,")],
        [sg.Text("allora utilizza questa funzione per sincronizzare i contenuti: "), sg.Button("Sincronizza")],
    ]

    col2 = [
        [sg.Text("--- Cache ---")],
        [sg.Text("Directory contenente i download/metadati:")],
        [sg.InputText(settings["downloads_path"]), sg.FolderBrowse()],
        [sg.Text("")],
        [sg.Text("--- NWN client ---")],
        [sg.Text("Directory dove è installato o dove installare il client NWN:")],
        [sg.InputText(settings["nwnclient_path"]), sg.FolderBrowse()],
        [sg.Checkbox(" Installare il client NWN?")],
        [sg.Text("")],
        [sg.Text("--- NWNCX ---")],
        [sg.Checkbox(" Installare NWNCX?", default=settings["nwncx"])],
        [sg.Text("")],
    ]

    upd_row = []
    if assets:
        upd_row = [
            [sg.Text("E' disponibile una nuova versione dell'app: ", text_color="red"), sg.Button("Scarica")],
        ]

    layout = [
        [sg.Column(upd_row, justification="center")],
        [sg.Column(col1), sg.VerticalSeparator(), sg.Column(col2)],
        [sg.Text("")],
        [sg.Column([[sg.Button("Controlla aggiornamenti"), sg.Button("Inizia update!")]], justification="center")],
        [sg.Text("")],
        [sg.Text("--- Log ---    "), sg.Text("Verbosità: "), sg.DropDown(["1", "2"], size=(3, 1), default_value="1")],
        [sg.Multiline(size=(150, 20), autoscroll=True, disabled=True, key="LOG")],
        [sg.Button("Pulisci console")],
    ]

    global WINDOW
    WINDOW = sg.Window("Lande Installer & Updater", layout, finalize=True, auto_size_text=True, auto_size_buttons=True, resizable=True)
    while True:
        event, values = WINDOW.read()
        # print(values)
        if event == sg.WIN_CLOSED:
            break

        settings["dialog"] = values[0]
        settings["mode"] = values[1]
        settings["downloads_path"] = values[3]
        settings["nwnclient_path"] = values[4]
        settings["nwnclient"] = values[5]
        settings["nwncx"] = values[7]
        settings["verbosity"] = int(values[7])

        with open(SETTINGS, "w") as fp:
            json.dump(settings, fp)

        if event == THREAD_EVENT:
            WINDOW["LOG"].print(values[THREAD_EVENT][0])
        elif event == POPUP_EVENT:
            sg.Popup(values[POPUP_EVENT][0], keep_on_top=True )
        elif event == "Inizia update!":
            WINDOW["LOG"]("")
            th = threading.Thread(target=start, args=(settings,))
            th.daemon = True
            th.start()
        elif event == "Controlla aggiornamenti":
            WINDOW["LOG"]("")
            th = threading.Thread(target=start, args=(settings, True,))
            th.daemon = True
            th.start()
        elif event == "Sincronizza":
            WINDOW["LOG"]("")
            th = threading.Thread(target=start, args=(settings, True, True, ))
            th.daemon = True
            th.start()
        elif event == "Scarica":
            webbrowser.open_new_tab(UPDATE_URL)
        elif event == "Pulisci console":
            WINDOW["LOG"]("")


def start(settings: list, dry_run=False, baseline=False):
    res = requests.get(BASE_URL)
    soup = BeautifulSoup(res.content, features="html.parser")

    global SKIP
    if settings["dialog"] == "Italiano":
        SKIP.append("dialog_eng")
    else:
        SKIP.append("dialog_ita")

    reinstall = False
    if settings["mode"] != "Update":
        reinstall = True

    global DOWNLOAD_PATH
    DOWNLOAD_PATH = settings["downloads_path"]

    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)

    global MAIN_PATH
    MAIN_PATH = settings["nwnclient_path"]

    install_client = False
    if settings["nwnclient"] == True:
        install_client = True

    install_cx = False
    if settings["nwncx"] == True:
        install_cx = True

    global VERBOSITY
    VERBOSITY = settings["verbosity"]

    try:
        if install_client and not dry_run:
            install_nwnclient(reinstall)
        
        updates = install_haks(soup, force=reinstall, dry_run=dry_run, baseline=baseline)
        if not baseline:
            if dry_run:
                popup("Update disponibili: %s" % updates)
            else:
                popup("Update installati: %s" % updates)
        
        if install_cx and not dry_run:
            install_nwncx(reinstall)

    except:
        set_error()

    finally:
        if not ERROR_FLAG:
            print_log("\n\nOperazione completata con successo.\n")
        else:
            print_log("\n\nOperazione completata con errori. Inviare il file error.log allo sviluppatore.\n")


if __name__ == "__main__":
    main()
