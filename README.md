# lande_installer
Installer automatico per shard NWN Lande di Faerun

## Istruzioni
Per eseguire lo script è necessario Python 3.
```
# Installatione delle dipendenze
pip install -r REQUIREMENTS.txt

# Esecuzione dello script
python lande_installer.py
```

# Creazione dell'eseguibile

Copiare il file `hook-patoolib.py` in:

- (Windows) `<Path di installazione di Python>\Lib\site-packages\Pyinstaller\hooks\`
- (Linux) `<Path di installazione di Python>/site-packages/PyInstaller/hooks/`

quindi eseguire:
```
pyinstaller.exe --onefile lande_installer.py
```
