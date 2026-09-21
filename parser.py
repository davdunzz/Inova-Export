import re

FIELDS=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]

# Italian licence plates: exactly 2 letters + 3 digits + 2 letters.
PLATE_RE=re.compile(r"(?<![A-Z0-9])([A-Z]{2}[0-9]{3}[A-Z]{2})(?![A-Z0-9])",re.I)
PRACTICE_RE=re.compile(r"(?<![A-Z0-9])(\d{4,7})\s*(?:\t|\s)+([A-Z]{2}[0-9]{3}[A-Z]{2})(?![A-Z0-9])",re.I)
DATE_RE=re.compile(r"\b\d{2}-\d{2}-\d{4}(?:,\s*\d{2}:\d{2})?\b")

STATES=[
"Inserita - Pending","Perizia - Pianificata","Preventivo - Da Elaborare",
"Preventivo - Autorizzato al Network","Preventivo - In Attesa di Autorizzazione",
"Lavorazione - Da Pianificare","Lavorazione - Pianificata",
"Lavorazione - in Attesa - VHL Presente","Lavorazione - in Corso",
"Lavorazione - Terminata","Da Fatturare","Fatturata",
"Senza Seguito - Pratica Annullata","Lavorazione - da ultimare",
"In Attesa Documenti","Da Ricontattare",
"In Attesa Documenti - VHL Presente","Da Ricontattare - VHL Presente"
]

TYPES=["GRANDINE + CRISTALLO","ATTO VANDALICO","GRANDINE","CRISTALLI","RCA","PRIVATO"]

BRANDS=[
"MERCEDES-BENZ","VOLKSWAGEN","CITROËN","CITROEN","HYUNDAI","TOYOTA",
"PEUGEOT","JEEP","FIAT","MAZDA","BMW","EMC","MG","FORD","RENAULT",
"NISSAN","VOLVO","AUDI","MERCEDES","OPEL","KIA","SUZUKI","SKODA","DACIA","TESLA"
]

MODELS=[
"SERIE 1 «F20...»","SERIE 1 «F20...","SERIE 1 «F20»","208 «II»","AVENGER",
"TIPO «II»","CX30","C3 «III»","WAVE 2","ZS «II»","C4 «III»",
"YARIS «IV»","TUCSON «III»","MG3","TAIGO"
]

def clean(s):
    return re.sub(r"\s+"," ",str(s).replace("\xa0"," ").strip())

def find_starts(lines):
    """Find only true practice starts.

    Inova records always start with:
        NUMERO PRATICA + TARGA PRINCIPALE + DATA CREAZIONE

    We deliberately do NOT use a generic plate/date fallback: later in the
    same record Inova can contain the plate of a substitute vehicle.
    That plate must remain part of the current record and never start a new one.
    """
    starts=[]
    for i,line in enumerate(lines):
        if "Non è possibile cancellare questo file" in line:
            continue
        pm=PRACTICE_RE.search(line)
        if not pm:
            continue
        # The creation date must be after the practice number + main plate.
        if DATE_RE.search(line, pm.end()):
            starts.append(i)
    return starts

def parse_inova(raw):
    raw=raw.replace("\r\n","\n").replace("\r","\n").replace("\ufeff","")
    lines=raw.split("\n")
    starts=find_starts(lines)

    if not starts:
        raise ValueError("Non trovo le pratiche. Esempio atteso: 60122 FX231FH 22-07-2026.")

    records=[]
    for n,start in enumerate(starts):
        end=starts[n+1] if n+1<len(starts) else len(lines)
        block=[x for x in lines[start:end] if "Non è possibile cancellare questo file" not in x]
        if not block: continue

        first=clean(block[0])
        pm=PRACTICE_RE.search(first)
        if not pm:
            continue

        # The plate immediately following the practice number is always the
        # main vehicle plate. Any later plate belongs to fields inside this
        # same record (e.g. substitute vehicle) and is ignored as a key.
        plate=pm.group(2).upper()
        cm=DATE_RE.search(first, pm.end())
        created=cm.group(0) if cm else ""

        # Join all lines in the record. Remove only the first header values.
        tail=clean(" ".join(block))
        # Remove practice number + plate if present, otherwise remove plate.
        tail=tail[pm.end():].strip()
        if created:
            tail=tail.replace(created,"",1).strip()

        # Appointment date is the first remaining date.
        dm=DATE_RE.search(tail)
        if dm:
            tail=tail[dm.end():].strip()

        # Find the workflow state.
        state=""
        pos=-1
        low=tail.casefold()
        for st in sorted(STATES,key=len,reverse=True):
            p=low.find(st.casefold())
            if p>=0 and (pos<0 or p<pos):
                pos=p; state=st

        # If a new/unknown state appears, preserve the record. Use claim type as boundary.
        if pos<0:
            claim_pos=-1
            for typ in sorted(TYPES,key=len,reverse=True):
                p=low.find(typ.casefold())
                if p>0 and (claim_pos<0 or p<claim_pos):
                    claim_pos=p
            if claim_pos<0:
                # Do not discard: keep the whole remaining text as owner and mark unknown.
                owner=clean(tail); state="Stato non riconosciuto"; after=""
            else:
                owner=clean(tail[:claim_pos])
                state="Stato non riconosciuto"
                after=tail[claim_pos:].strip()
        else:
            owner=clean(tail[:pos])
            after=tail[pos+len(state):].strip()

        typ=""
        for t in sorted(TYPES,key=len,reverse=True):
            if after.casefold().startswith(t.casefold()):
                typ=t
                after=after[len(t):].strip()
                break

        brand=""
        after_brand=""
        for b in sorted(BRANDS,key=len,reverse=True):
            m=re.search(r"(?<!\w)"+re.escape(b)+r"(?!\w)",after,re.I)
            if m:
                brand="CITROËN" if b.upper()=="CITROEN" else b
                after_brand=after[m.end():].strip()
                break

        model=""
        if brand:
            for name in sorted(MODELS,key=len,reverse=True):
                if after_brand.casefold().startswith(name.casefold()):
                    model=name
                    break
            if not model:
                stop=re.search(r"\b(Nobis Assicuraz|Axa Italia|Privato|Sì|No|Inova Italia|RESIDENZA|via\s+settembrini)\b",after_brand,re.I)
                candidate=after_brand[:stop.start()] if stop else after_brand
                model=clean(candidate)[:60]

        records.append({
            "Targa":plate,
            "Proprietario":owner,
            "Stato":state,
            "Tipologia Sinistro":typ,
            "Marchio":brand,
            "Modello":model
        })

    if not records:
        raise ValueError("Nessuna pratica riconosciuta.")
    return records
