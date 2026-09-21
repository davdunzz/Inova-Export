# DLab Data Extractor

App Windows locale per trasformare esportazioni tabellari del gestionale in Excel.

## Caratteristiche
- Nessuna AI.
- Nessuna API.
- Nessun invio di dati online.
- Incolla direttamente il testo copiato dal gestionale.
- Riconosce le intestazioni e le colonne.
- Seleziona solo i campi che vuoi.
- Anteprima.
- Esportazione `.xlsx`.
- Stile verde Inova.

## Avvio locale

```bash
python -m pip install -r requirements.txt
python app.py
```

## Build Windows

È presente una GitHub Action in `.github/workflows/build-windows.yml`.
Ad ogni push può creare automaticamente l'eseguibile Windows tramite PyInstaller.

## Uso

1. Copia l'esportazione completa dal gestionale.
2. Incollala nel riquadro.
3. Seleziona i campi.
4. Premi `ELABORA DATI`.
5. Controlla l'anteprima.
6. Premi `ESPORTA EXCEL`.

## Nota
Il parser è progettato per esportazioni con intestazioni come `Targa`, `Proprietario`, `Stato`, `Tipologia Sinistro`, `Marchio`, `Modello` e per dati copiati da tabelle con tabulazioni.
