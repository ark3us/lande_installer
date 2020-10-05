# lande_installer
Installer automatico per shard NWN Lande di Faerun

## Release

E' possibile scaricare da qui la versione già compilata, che ha come unico requisito 7zip:
https://github.com/ark3us/lande_installer/releases

## Esecuzione script

Per eseguire lo script python è necessario Python 3.
```
# Installatione delle dipendenze
pip install -r REQUIREMENTS.txt

# Esecuzione dello script
python lande_installer.py
```

## Creazione dell'eseguibile

Copiare il file `hook-patoolib.py` in:

- (Windows) `<Path di installazione di Python>\Lib\site-packages\Pyinstaller\hooks\`
- (Linux) `<Path di installazione di Python>/site-packages/PyInstaller/hooks/`

quindi eseguire:
```
pyinstaller.exe --onefile lande_installer.py
```
