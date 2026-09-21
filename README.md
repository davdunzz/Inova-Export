# DLab Data Extractor v5

Parser locale dedicato alle esportazioni Inova.

Stati Inova riconosciuti:
- Inserita - Pending
- Perizia - Pianificata
- Preventivo - Da Elaborare
- Preventivo - Autorizzato al Network
- Preventivo - In Attesa di Autorizzazione
- Lavorazione - Da Pianificare
- Lavorazione - Pianificata
- Lavorazione - in Attesa - VHL Presente
- Lavorazione - in Corso
- Lavorazione - Terminata
- Da Fatturare
- Fatturata
- Senza Seguito - Pratica Annullata
- Lavorazione - da ultimare

Il parser include anche un fallback per non scartare una pratica se Inova introduce uno stato nuovo.
Nessuna AI, nessuna API, nessun invio online.
