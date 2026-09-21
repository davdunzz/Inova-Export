
import re

AVAILABLE_FIELDS = [
    "Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello",
    "Stato Pratica","Data di creazione","Data appuntamento","Sala Tecnica Sub-Stato",
    "CRM Sub-Stato","Centro di Perizia","Centro di Riparazione","Sede","WinCarNr",
    "Compagnia","Veicolo presente","Veicolo di cortesia","Previsione riconsegna veicolo",
    "Perizia a Domicilio","Pick Up","Consegna"
]

HEADER_ALIASES = {
    "stato pratica":"Stato Pratica",
    "pratica":"Stato Pratica",
    "targa":"Targa",
    "data di creazione":"Data di creazione",
    "data appuntamento":"Data appuntamento",
    "proprietario":"Proprietario",
    "stato":"Stato",
    "tipologia sinistro":"Tipologia Sinistro",
    "sala tecnica sub-stato":"Sala Tecnica Sub-Stato",
    "crm sub-stato":"CRM Sub-Stato",
    "centro di perizia":"Centro di Perizia",
    "centro di riparazione":"Centro di Riparazione",
    "sede":"Sede",
    "wincarnr":"WinCarNr",
    "marchio":"Marchio",
    "modello":"Modello",
    "compagnia":"Compagnia",
    "veicolo presente":"Veicolo presente",
    "veicolo di cortesia":"Veicolo di cortesia",
    "previsione riconsegna veicolo":"Previsione riconsegna veicolo",
    "perizia a domicilio":"Perizia a Domicilio",
    "pick up":"Pick Up",
    "consegna":"Consegna",
}

def clean(s):
    s = str(s).replace("\xa0", " ").replace("\r", "")
    return re.sub(r"[ \t]+", " ", s).strip()

def norm(s):
    s = clean(s).lower()
    s = s.replace("–","-").replace("—","-")
    return s

def looks_like_plate(s):
    return bool(re.fullmatch(r"[A-Z]{2,3}[0-9]{3}[A-Z]{0,2}", clean(s).upper()))

def looks_like_date(s):
    return bool(re.search(r"\b\d{2}-\d{2}-\d{4}\b", s))

def find_header(lines):
    # Search a window of lines, because copying from the browser/Excel can wrap the
    # header visually or put part of it on a new line.
    for start in range(min(8, len(lines))):
        window=" ".join(clean(x) for x in lines[start:start+3])
        low=norm(window)
        if "targa" in low and "proprietario" in low and "modello" in low:
            return start
    # Accept even if Model is outside the first three physical lines.
    for i,line in enumerate(lines[:12]):
        low=norm(line)
        if "targa" in low and "proprietario" in low:
            return i
    raise ValueError("Non riconosco le intestazioni. Incolla anche la riga che contiene Targa, Proprietario e Modello.")

def locate_columns(header_text):
    # Use the known headers and their character positions. This works when the
    # clipboard has converted tabs into spaces or when the table is copied as text.
    found=[]
    low=header_text.lower()
    # longest first prevents 'stato' matching inside 'stato pratica'
    aliases=sorted(HEADER_ALIASES.items(), key=lambda x: len(x[0]), reverse=True)
    occupied=[]
    for alias, canonical in aliases:
        for m in re.finditer(r"(?<!\w)"+re.escape(alias)+r"(?!\w)", low):
            if any(not (m.end() <= a or m.start() >= b) for a,b,_ in occupied):
                continue
            occupied.append((m.start(),m.end(),canonical))
            found.append((m.start(),canonical))
            break
    found.sort()
    # If there are duplicate Stato headers, keep both positions under distinct
    # internal names: the first one is usually the practical state, the later one
    # is the workflow state in this export. We primarily need the latter.
    return found

def parse_export(raw, wanted):
    raw=raw.replace("\r\n","\n").replace("\r","\n")
    lines=[x.rstrip() for x in raw.split("\n") if x.strip()]
    if not lines:
        raise ValueError("Non ci sono dati da elaborare.")

    hi=find_header(lines)

    # Reconstruct the header from the first few lines. This is the key difference
    # from the previous version: it does not require all headings to be on one line.
    header_parts=[]
    for line in lines[hi:hi+4]:
        if "Non è possibile cancellare questo file" not in line:
            header_parts.append(line)
        # stop once we see the first plate/id row
        if looks_like_plate(line):
            break
    header_text=" ".join(header_parts)
    columns=locate_columns(header_text)

    # We need positions in character-space. The source can be TSV or whitespace-aligned.
    # For each record, identify the start of the row using the 6-8 character plate.
    # Then extract fields by the header start positions.
    if not columns:
        raise ValueError("Non riesco a leggere le colonne dell'esportazione.")

    # Detect whether tabs exist. If yes, use true TSV parsing; otherwise use fixed-width
    # character positions derived from the header.
    has_tabs="\t" in raw

    records=[]
    if has_tabs:
        # Find the actual header line containing the largest number of known labels.
        best_i=hi; best_count=0
        for i in range(hi,min(hi+5,len(lines))):
            count=sum(1 for a,_ in locate_columns(lines[i]))
            if count>best_count:
                best_i=i; best_count=count
        hdr=[clean(x) for x in lines[best_i].split("\t")]
        positions={}
        for idx,h in enumerate(hdr):
            k=norm(h)
            if k in HEADER_ALIASES and HEADER_ALIASES[k] not in positions:
                positions[HEADER_ALIASES[k]]=idx
        t_idx=positions.get("Targa")
        if t_idx is None:
            # fallback exact label search
            for idx,h in enumerate(hdr):
                if norm(h)=="targa": t_idx=idx; break
        current=None
        for line in lines[best_i+1:]:
            if "Non è possibile cancellare questo file" in line: continue
            cells=[clean(x) for x in line.split("\t")]
            if t_idx is not None and t_idx < len(cells) and looks_like_plate(cells[t_idx]):
                if current: records.append(current)
                current=cells
            elif current and len(cells)==1 and looks_like_date(cells[0]):
                # wrapped appointment/creation date: preserve it in the first empty date field
                current.append(cells[0])
            elif current and any(cells):
                # merge a continuation row conservatively
                for i,v in enumerate(cells):
                    if i<len(current) and not current[i] and v: current[i]=v
        if current: records.append(current)

        out=[]
        for rec in records:
            d={}
            for f in wanted:
                idx=positions.get(f)
                d[f]=clean(rec[idx]) if idx is not None and idx<len(rec) else ""
            if d.get("Targa") or "Targa" not in wanted:
                if any(d.values()): out.append(d)
        return out

    # Fixed-width / whitespace mode.
    # Build header starts and use them as boundaries.
    starts=columns
    # Because some labels may have been merged, force the important labels' relative
    # order according to the actual export.
    wanted_order=[
        "Stato Pratica","Targa","Data di creazione","Data appuntamento","Proprietario",
        "Stato","Tipologia Sinistro","Sala Tecnica Sub-Stato","CRM Sub-Stato",
        "Centro di Perizia","Centro di Riparazione","Sede","WinCarNr","Marchio",
        "Modello","Compagnia","Veicolo presente","Veicolo di cortesia",
        "Previsione riconsegna veicolo","Perizia a Domicilio","Pick Up","Consegna"
    ]
    # Find data rows by plate. In this copied representation the plate is preceded by
    # the numeric practice number, so locate both when possible.
    data_start=hi+1
    # Skip header continuation lines until the first plate.
    first_plate_idx=None
    for i in range(data_start,min(len(lines),data_start+8)):
        if re.search(r"\b\d{5,}\s+[A-Z]{2,3}\d{3}[A-Z]{0,2}\b", lines[i], re.I):
            first_plate_idx=i; break
    if first_plate_idx is None:
        raise ValueError("Non trovo le righe dei sinistri. Il testo deve contenere valori come 60995 FX686TC.")

    # Use a robust line parser tailored to the shown Inova export. Values after the plate
    # are extracted from recognizable tokens rather than depending on exact spacing.
    # We retain the fields the user needs even when other cells are blank.
    for line in lines[first_plate_idx:]:
        if "Non è possibile cancellare questo file" in line: continue
        if not re.search(r"\b\d{5,}\s+[A-Z]{2,3}\d{3}[A-Z]{0,2}\b", line, re.I):
            # continuation line (often appointment date or owner). handled below
            continue

        m=re.search(r"\b(\d{5,})\s+([A-Z]{2,3}\d{3}[A-Z]{0,2})\s+(\d{2}-\d{2}-\d{4})\b", line, re.I)
        if not m: continue
        practice,plate,created=m.groups()
        tail=line[m.end():].strip()

        # If appointment is present at the beginning of the tail, capture it.
        appointment=""
        am=re.match(r"(\d{2}-\d{2}-\d{4}(?:,\s*\d{2}:\d{2})?)\s*",tail)
        if am:
            appointment=am.group(1); tail=tail[am.end():].strip()

        # The owner begins after appointment. We identify the state using known phrases.
        states=[
            "Lavorazione - in Attesa - VHL Presente","Lavorazione - in Attesa",
            "Lavorazione - Pianificata","Lavorazione - in Corso","Lavorazione - Terminata",
            "Preventivo - In Attesa di Autorizzazione","Da Fatturare"
        ]
        state=""
        state_pos=None
        for st in sorted(states,key=len,reverse=True):
            p=tail.find(st)
            if p>=0:
                state=st; state_pos=p; break
        if state_pos is None:
            # owner is usually first token sequence; state may be missing
            continue
        owner=tail[:state_pos].strip()
        after=tail[state_pos+len(state):].strip()

        # Claim type is one of the recognizable values in this export.
        types=[
            "GRANDINE + CRISTALLO","ATTO VANDALICO","GRANDINE","CRISTALLI","RCA","PRIVATO"
        ]
        typ=""
        for t in sorted(types,key=len,reverse=True):
            if after.startswith(t):
                typ=t; after=after[len(t):].strip(); break

        # Locate known brands/models. Model is generally the token(s) immediately after brand.
        brands=["BMW","PEUGEOT","JEEP","FIAT","MAZDA","CITROËN","CITROEN","EMC","MG"]
        brand=""
        for b in brands:
            if re.search(r"(?<!\w)"+re.escape(b)+r"(?!\w)", after,re.I):
                brand=b
                bp=re.search(r"(?<!\w)"+re.escape(b)+r"(?!\w)", after,re.I)
                before_brand=after[:bp.start()].strip()
                after_brand=after[bp.end():].strip()
                break
        else:
            before_brand=after
            after_brand=""

        model=""
        if brand:
            # Models used in the shown export. Stop at insurer/yes/no markers.
            known_models=[
                r"SERIE 1 «F20[^ \t]*",r"208 «II»",r"AVENGER",r"TIPO «II»",
                r"CX30",r"C3 «III»",r"WAVE 2",r"ZS «II»",r"C4 «III»"
            ]
            for pat in known_models:
                mm=re.match(pat,after_brand,re.I)
                if mm:
                    model=mm.group(0); break
            if not model:
                # generic: first 1-3 words before insurer markers
                stop=re.search(r"\b(Nobis Assicuraz|Axa Italia|Privato|Sì|No)\b",after_brand,re.I)
                candidate=after_brand[:stop.start()] if stop else after_brand
                model=clean(candidate).strip()
                model=model[:45]

        d={
            "Targa":plate,
            "Proprietario":owner,
            "Stato":state,
            "Tipologia Sinistro":typ,
            "Marchio":brand,
            "Modello":model,
            "Stato Pratica":practice,
            "Data di creazione":created,
            "Data appuntamento":appointment,
        }
        for f in wanted:
            d.setdefault(f,"")
        records.append({f:d.get(f,"") for f in wanted})

    if not records:
        raise ValueError("Non sono riuscito a riconoscere nessuna riga. Controlla che l'esportazione contenga Targa e i dati dei sinistri.")
    return records
