import re

FIELDS=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]

PLATE_RE=re.compile(r"\b([A-Z]{2,3}[0-9]{3}[A-Z]{0,2})\b",re.I)
PRACTICE_RE=re.compile(r"\b\d{4,7}\s+([A-Z]{2,3}[0-9]{3}[A-Z]{0,2})\b",re.I)
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
]
TYPES=[
"GRANDINE + CRISTALLO",
"ATTO VANDALICO",
"GRANDINE",
"CRISTALLI",
"RCA",
"PRIVATO",
]

BRANDS=["BMW","PEUGEOT","JEEP","FIAT","MAZDA","CITROËN","CITROEN","EMC","MG"]

MODELS=[
"SERIE 1 «F20»","SERIE 1 «F20...","208 «II»","AVENGER","TIPO «II»","CX30",
"C3 «III»","WAVE 2","ZS «II»","C4 «III»"
]

def clean(s):
    return re.sub(r"\s+"," ",str(s).replace("\xa0"," ").strip())

def parse_inova(raw):
    raw=raw.replace("\r\n","\n").replace("\r","\n")
    lines=raw.split("\n")

    # Every new record starts with: practice number + plate + creation date.
    starts=[]
    for i,line in enumerate(lines):
        m=PRACTICE_RE.search(line)
        if m and DATE_RE.search(line):
            starts.append(i)

    if not starts:
        # fallback: plate + creation date, without relying on practice number
        for i,line in enumerate(lines):
            if PLATE_RE.search(line) and DATE_RE.search(line):
                starts.append(i)

    if not starts:
        raise ValueError("Non trovo le righe delle pratiche. Il testo deve contenere righe come: 60995 FX686TC 02-09-2026.")

    starts=list(dict.fromkeys(starts))
    records=[]

    for n,start in enumerate(starts):
        end=starts[n+1] if n+1<len(starts) else len(lines)
        block=[lines[start]] + lines[start+1:end]

        # Ignore the browser/Excel warning if copied inside the block.
        block=[x for x in block if "Non è possibile cancellare questo file" not in x]
        first=clean(block[0])

        pm=PRACTICE_RE.search(first)
        plate=pm.group(1).upper() if pm else PLATE_RE.search(first).group(1).upper()
        cm=DATE_RE.search(first)
        created=cm.group(0) if cm else ""

        # Join the record but preserve the order. Wrapped appointment dates are harmless.
        tail=clean(" ".join(clean(x) for x in block))
        # Remove the leading practice/plate/date.
        if pm:
            tail=tail[pm.end():].strip()
        if created and tail.startswith(created):
            tail=tail[len(created):].strip()

        # The first date after creation is appointment when present.
        appointment=""
        dm=DATE_RE.search(tail)
        if dm:
            appointment=dm.group(0)
            tail=tail[dm.end():].strip()

        # Find state. Owner is the text between appointment and state.
        state=""
        pos=-1
        for st in sorted(STATES,key=len,reverse=True):
            p=tail.find(st)
            if p>=0 and (pos<0 or p<pos):
                pos=p; state=st
        if pos<0:
            # Fallback: do not discard the practice just because Inova introduced
            # a new state. The owner is followed by the state and then by the claim type.
            fallback_pos=-1
            for t in sorted(TYPES,key=len,reverse=True):
                p=tail.find(t)
                if p>0:
                    fallback_pos=p
                    break
            if fallback_pos>0:
                owner_and_state=clean(tail[:fallback_pos])
                # Owner is generally the first 1-4 words. Prefer the last known
                # state-like segment after the owner; otherwise keep a useful value.
                words=owner_and_state.split()
                if len(words)>=2:
                    # Common customer names/company names are short; preserve a
                    # conservative owner prefix and use the remainder as state.
                    owner=" ".join(words[:min(4,len(words)-1)])
                    state=" ".join(words[min(4,len(words)-1):]).strip()
                    after=tail[fallback_pos:].strip()
                    if not state:
                        owner=owner_and_state
                        state="Non riconosciuto"
                else:
                    owner=owner_and_state
                    state="Non riconosciuto"
                pos=fallback_pos
            else:
                continue
        else:
            owner=clean(tail[:pos])
            after=tail[pos+len(state):].strip()

        # Find claim type after state.
        typ=""
        for t in sorted(TYPES,key=len,reverse=True):
            if after.startswith(t):
                typ=t
                after=after[len(t):].strip()
                break

        # Find vehicle brand. Everything between type and brand is usually sub-state noise.
        brand=""
        brand_pos=-1
        for b in sorted(BRANDS,key=len,reverse=True):
            m=re.search(r"(?<!\w)"+re.escape(b)+r"(?!\w)",after,re.I)
            if m:
                brand=b.upper() if b not in ["CITROËN","CITROEN"] else "CITROËN"
                brand_pos=m.start()
                after_brand=after[m.end():].strip()
                break
        else:
            after_brand=""

        model=""
        if brand:
            # Prefer exact known models from the shown export.
            for model_name in sorted(MODELS,key=len,reverse=True):
                if after_brand.upper().startswith(model_name.upper()):
                    model=model_name
                    break
            if not model:
                # Generic fallback: take text until insurer / vehicle-present markers.
                stop=re.search(r"\b(Nobis Assicuraz|Axa Italia|Privato|Sì|No|Inova Italia)\b",after_brand,re.I)
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
        raise ValueError("Ho trovato le pratiche ma non sono riuscito a ricavare i campi richiesti.")
    return records
