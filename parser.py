import re

FIELDS=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]

PRACTICE_RE=re.compile(r"(?<![A-Z0-9])(\d{4,7})\s+([A-Z]{2,3}[0-9]{3}[A-Z]{0,2})(?![A-Z0-9])",re.I)
PLATE_RE=re.compile(r"(?<![A-Z0-9])([A-Z]{2,3}[0-9]{3}[A-Z]{0,2})(?![A-Z0-9])",re.I)
DATE_RE=re.compile(r"\b\d{2}-\d{2}-\d{4}(?:,\s*\d{2}:\d{2})?\b")

STATES=[
    "Inserita - Pending",
    "Perizia - Pianificata",
    "Preventivo - Da Elaborare",
    "Preventivo - Autorizzato al Network",
    "Preventivo - In Attesa di Autorizzazione",
    "Lavorazione - Da Pianificare",
    "Lavorazione - Pianificata",
    "Lavorazione - in Attesa - VHL Presente",
    "Lavorazione - in Corso",
    "Lavorazione - Terminata",
    "Da Fatturare",
    "Fatturata",
    "Senza Seguito - Pratica Annullata",
    "Lavorazione - da ultimare",
    "In Attesa Documenti",
    "Da Ricontattare",
    "In Attesa Documenti - VHL Presente",
    "Da Ricontattare - VHL Presente",
]

TYPES=[
    "GRANDINE + CRISTALLO","ATTO VANDALICO","GRANDINE","CRISTALLI","RCA","PRIVATO"
]

BRANDS=[
    "MERCEDES-BENZ","VOLKSWAGEN","CITROËN","CITROEN","HYUNDAI","TOYOTA",
    "PEUGEOT","JEEP","FIAT","MAZDA","BMW","EMC","MG","FORD","RENAULT",
    "NISSAN","VOLVO","AUDI","MERCEDES","OPEL","KIA","SUZUKI","SKODA",
    "DACIA","TESLA"
]

MODELS=[
    "SERIE 1 «F20...","SERIE 1 «F20»","208 «II»","AVENGER","TIPO «II»",
    "CX30","C3 «III»","WAVE 2","ZS «II»","C4 «III»","YARIS «IV»",
    "TUCSON «III»","MG3"
]

def clean(s):
    return re.sub(r"\s+"," ",str(s).replace("\xa0"," ").strip())

def parse_inova(raw):
    raw=raw.replace("\r\n","\n").replace("\r","\n")
    lines=raw.split("\n")

    starts=[]
    for i,line in enumerate(lines):
        if "Non è possibile cancellare questo file" in line:
            continue
        m=PRACTICE_RE.search(line)
        if m and DATE_RE.search(line,m.end()):
            starts.append(i)

    if not starts:
        # More tolerant fallback: plate + date, even if the practice number was lost.
        for i,line in enumerate(lines):
            if "Non è possibile cancellare questo file" in line:
                continue
            if PLATE_RE.search(line) and DATE_RE.search(line):
                starts.append(i)

    if not starts:
        raise ValueError("Non trovo le pratiche. Servono righe come: 60995 FX686TC 02-09-2026.")

    starts=list(dict.fromkeys(starts))
    records=[]

    for n,start in enumerate(starts):
        end=starts[n+1] if n+1<len(starts) else len(lines)
        block=[x for x in lines[start:end] if "Non è possibile cancellare questo file" not in x]
        if not block:
            continue

        first=clean(block[0])
        pm=PRACTICE_RE.search(first)
        if pm:
            plate=pm.group(2).upper()
            prefix_end=pm.end()
        else:
            pl=PLATE_RE.search(first)
            if not pl:
                continue
            plate=pl.group(1).upper()
            prefix_end=pl.end()

        cm=DATE_RE.search(first,prefix_end)
        created=cm.group(0) if cm else ""

        tail=clean(" ".join(clean(x) for x in block))
        tail=tail[prefix_end:].strip()
        if created:
            tail=tail.replace(created,"",1).strip()

        # The next date in the block is normally the appointment.
        appointment=""
        dm=DATE_RE.search(tail)
        if dm:
            appointment=dm.group(0)
            tail=tail[dm.end():].strip()

        # Find a known state. Longest first.
        state=""
        pos=-1
        for st in sorted(STATES,key=len,reverse=True):
            p=tail.find(st)
            if p>=0 and (pos<0 or p<pos):
                pos=p
                state=st

        # If the state is new/unknown, do not drop the practice.
        # Find the claim type and preserve everything before it.
        if pos<0:
            claim_pos=-1
            for t in sorted(TYPES,key=len,reverse=True):
                p=tail.find(t)
                if p>0 and (claim_pos<0 or p<claim_pos):
                    claim_pos=p
            if claim_pos<0:
                continue
            before_claim=clean(tail[:claim_pos])
            # In an unknown-state row, owner is the text before the first recognizable
            # workflow phrase if present; otherwise preserve it as owner and mark state.
            state="Stato non riconosciuto"
            owner=before_claim
            after=tail[claim_pos:].strip()
        else:
            owner=clean(tail[:pos])
            after=tail[pos+len(state):].strip()

        typ=""
        for t in sorted(TYPES,key=len,reverse=True):
            if after.startswith(t):
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
                if after_brand.upper().startswith(name.upper()):
                    model=name
                    break
            if not model:
                stop=re.search(r"\b(Nobis Assicuraz|Axa Italia|Privato|Sì|No|Inova Italia)\b",after_brand,re.I)
                candidate=after_brand[:stop.start()] if stop else after_brand
                model=clean(candidate)[:60]

        records.append({
            "Targa":plate,
            "Proprietario":owner,
            "Stato":state,
            "Tipologia Sinistro":typ,
            "Marchio":brand,
            "Modello":model,
        })

    if not records:
        raise ValueError("Non sono riuscito a riconoscere nessuna pratica.")
    return records
