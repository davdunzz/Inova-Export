import re

AVAILABLE_FIELDS = [
    "Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello",
    "Stato Pratica","Data di creazione","Data appuntamento","Sala Tecnica Sub-Stato",
    "CRM Sub-Stato","Centro di Perizia","Centro di Riparazione","Sede","WinCarNr",
    "Compagnia","Veicolo presente","Veicolo di cortesia","Previsione riconsegna veicolo",
    "Perizia a Domicilio","Pick Up","Consegna"
]

def clean(s):
    s = s.replace("\xa0"," ").strip()
    return re.sub(r"\s+"," ",s)

def normalize_header(s):
    s=clean(s).lower()
    s=s.replace("stato pratica","stato pratica")
    return s

def split_lines(raw):
    # Excel/gestionale exports are normally tab-delimited. Keep tabs because they define cells.
    return [line.rstrip("\r") for line in raw.replace("\r\n","\n").replace("\r","\n").split("\n") if line.strip()]

def find_header(lines):
    for i,line in enumerate(lines):
        c=[clean(x) for x in line.split("\t")]
        joined=" ".join(x.lower() for x in c)
        if "targa" in joined and "proprietario" in joined and "modello" in joined:
            return i,c
    # fallback: sometimes copied text has collapsed spaces
    for i,line in enumerate(lines):
        if re.search(r"\bTarga\b",line,re.I) and re.search(r"\bProprietario\b",line,re.I):
            return i, re.split(r"\t+|\s{2,}",line.strip())
    raise ValueError("Intestazione non trovata. Assicurati di aver copiato anche la riga con Targa, Proprietario, Modello.")

def parse_export(raw, wanted):
    lines=split_lines(raw)
    hi, headers=find_header(lines)

    # The source shown by the user has a first empty column and duplicate 'Stato' concepts.
    # Build a header map by known names, preserving the first occurrence.
    hmap={}
    for idx,h in enumerate(headers):
        h=clean(h)
        if not h: continue
        key=normalize_header(h)
        if key not in hmap: hmap[key]=idx

    # Find positions of important columns. Prefer exact known labels.
    positions={}
    for field in AVAILABLE_FIELDS:
        k=normalize_header(field)
        if k in hmap: positions[field]=hmap[k]

    # Determine rows using Targa as the anchor. In a pasted TSV export, each record normally
    # starts on a line containing the WinCar/ID and targa. Ignore stray application messages.
    targa_idx=positions.get("Targa")
    if targa_idx is None:
        raise ValueError("La colonna Targa non è stata riconosciuta.")

    records=[]
    current=None
    expected_cols=len(headers)

    def flush():
        nonlocal current
        if current is not None:
            records.append(current)
        current=None

    for line in lines[hi+1:]:
        if "Non è possibile cancellare questo file" in line:
            continue
        cells=line.split("\t")
        cells=[clean(x) for x in cells]

        # Skip obvious blank lines.
        if not any(cells): continue

        # A normal record row has enough cells to place Targa. If it is short, it can be
        # a continuation of a wrapped cell (especially dates); append to the current field
        # instead of creating a new record.
        looks_like_record = len(cells) > targa_idx and bool(re.fullmatch(r"[A-Z0-9]{6,8}", cells[targa_idx], re.I))
        if looks_like_record:
            flush()
            # pad/truncate safely
            row=cells + [""]*max(0, expected_cols-len(cells))
            current=row[:max(expected_cols,len(row))]
        elif current is not None:
            # Handle wrapped date/text lines. Put the continuation in the nearest empty
            # cell before the owner/targa area, otherwise ignore as noise.
            nonempty=[i for i,c in enumerate(cells) if c]
            if len(cells)==1 and nonempty:
                val=cells[nonempty[0]]
                # Usually this is a wrapped appointment/creation date. Add to first empty
                # date-like field.
                targets=["Data appuntamento","Data di creazione","Previsione riconsegna veicolo"]
                placed=False
                for f in targets:
                    idx=positions.get(f)
                    if idx is not None and (idx>=len(current) or not current[idx]):
                        while len(current)<=idx: current.append("")
                        current[idx]=val; placed=True; break
                if not placed:
                    pass
            elif len(cells) > 1:
                # merge only if it looks like a continuation of the current record
                for j,v in enumerate(cells):
                    if v and j < len(current) and not current[j]:
                        current[j]=v

    flush()

    # Build output. Also repair the common case where a wrapped appointment line caused
    # owner/status to shift in a collapsed export by using the tab structure whenever possible.
    out=[]
    for rec in records:
        d={}
        for f in wanted:
            idx=positions.get(f)
            d[f]=clean(rec[idx]) if idx is not None and idx < len(rec) else ""
        out.append(d)

    # Remove rows without a usable targa when Targa was requested or when the row is clearly noise.
    cleaned=[]
    for d in out:
        if "Targa" in wanted and not d.get("Targa",""):
            continue
        if any(v for v in d.values()):
            cleaned.append(d)
    return cleaned
