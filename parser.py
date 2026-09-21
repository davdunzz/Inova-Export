import re

AVAILABLE_FIELDS = [
    "Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello",
    "Stato Pratica","Data di creazione","Data appuntamento","Sala Tecnica Sub-Stato",
    "CRM Sub-Stato","Centro di Perizia","Centro di Riparazione","Sede","WinCarNr",
    "Compagnia","Veicolo presente","Veicolo di cortesia","Previsione riconsegna veicolo",
    "Perizia a Domicilio","Pick Up","Consegna"
]

TARGA_RE = re.compile(r"^[A-Z0-9]{5,8}$", re.I)
DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}(?:,\s*\d{2}:\d{2})?$")

def clean(s):
    s = s.replace("\xa0"," ").strip()
    return re.sub(r"\s+"," ",s)

def split_lines(raw):
    return [line.rstrip("\r") for line in raw.replace("\r\n","\n").replace("\r","\n").split("\n") if line.strip()]

def find_header(lines):
    for i,line in enumerate(lines):
        cells=[clean(x) for x in line.split("\t")]
        joined=" ".join(cells).lower()
        if "targa" in joined and "proprietario" in joined and "modello" in joined:
            return i,cells
    raise ValueError("Intestazione non trovata. Incolla anche la riga con Targa, Proprietario e Modello.")

def is_targa(s):
    s=clean(s)
    return bool(TARGA_RE.fullmatch(s)) and any(ch.isdigit() for ch in s) and any(ch.isalpha() for ch in s)

def parse_export(raw, wanted):
    lines=split_lines(raw)
    hi, headers=find_header(lines)

    # Header positions.
    hpos={}
    for i,h in enumerate(headers):
        h=clean(h)
        if h and h.lower() not in hpos:
            hpos[h.lower()]=i

    # Important: in the actual Inova clipboard export, the data can contain an
    # extra leading ID/blank cell compared with the header. We therefore find
    # the Targa cell in each record and align the remaining cells relative to it.
    targa_header = hpos.get("targa")
    if targa_header is None:
        raise ValueError("La colonna Targa non è stata trovata nell'intestazione.")

    records=[]
    current=None

    def flush():
        nonlocal current
        if current and any(clean(x) for x in current):
            records.append(current)
        current=None

    for line in lines[hi+1:]:
        if "Non è possibile cancellare questo file" in line:
            continue
        cells=[clean(x) for x in line.split("\t")]
        if not any(cells):
            continue

        # Find a targa anywhere in the row.
        t_idx=None
        for j,c in enumerate(cells):
            if is_targa(c):
                t_idx=j
                break

        if t_idx is not None:
            flush()
            # Store row plus detected targa index. We use the row's targa as the
            # anchor and map fields by their expected distance from Targa.
            current={"cells": cells, "targa_idx": t_idx}
        elif current is not None:
            # Wrapped clipboard lines: append to the current record.
            # If it is a one-cell date/name continuation, keep it in a side list.
            current.setdefault("continuations", []).extend(cells)

    flush()

    # Convert records to logical column maps.
    output=[]
    for rec in records:
        cells=rec["cells"]
        ti=rec["targa_idx"]

        # Build relative map around Targa. Header has:
        # Targa, Data creazione, Data appuntamento, Proprietario, Stato...
        # The user's export can have an extra ID cell immediately before Targa.
        # Determine offset from the number of cells after Targa and known markers.
        logical={}

        # Targa itself.
        logical["Targa"]=cells[ti]

        # After Targa, the next cells are generally date creation, appointment,
        # owner, status, claim type, ..., with wrapped lines potentially moved
        # to continuations. Map what exists directly.
        after=cells[ti+1:]
        names_after=["Data di creazione","Data appuntamento","Proprietario","Stato",
                     "Tipologia Sinistro","Sala Tecnica Sub-Stato","CRM Sub-Stato",
                     "Centro di Perizia","Centro di Riparazione","Sede","WinCarNr",
                     "Marchio","Modello","Compagnia","Veicolo presente",
                     "Veicolo di cortesia","Previsione riconsegna veicolo",
                     "Perizia a Domicilio","Pick Up","Consegna"]

        # If first value after Targa is clearly a date, normal mapping.
        for k,v in zip(names_after, after):
            logical[k]=v

        # Some exports put the creation/appointment dates on wrapped lines.
        cont=rec.get("continuations",[])
        for val in cont:
            val=clean(val)
            if not val: continue
            if DATE_RE.match(val):
                if not logical.get("Data appuntamento"):
                    logical["Data appuntamento"]=val
                elif not logical.get("Data di creazione"):
                    logical["Data di creazione"]=val
                else:
                    # preserve as appointment if both already exist only when empty
                    pass

        # Critical repair for the common pasted format:
        # after Targa: creation date, appointment date, owner, status, claim...
        # In the user's sample, the first date may be in the row and the second
        # date may be on the next line, followed by owner/status. We can consume
        # continuation tokens to fill missing fields in order.
        missing_order=["Data di creazione","Data appuntamento","Proprietario","Stato","Tipologia Sinistro"]
        # If owner is empty or looks like a date, use continuations for missing slots.
        cont2=[x for x in cont if clean(x)]
        ci=0
        for field in missing_order:
            if logical.get(field):
                continue
            while ci < len(cont2):
                val=cont2[ci]; ci+=1
                if DATE_RE.match(val) and field in ("Data di creazione","Data appuntamento"):
                    logical[field]=val; break
                if field not in ("Data di creazione","Data appuntamento"):
                    logical[field]=val; break

        d={f:clean(logical.get(f,"")) for f in wanted}
        # If targa requested, always require it.
        if d.get("Targa","") and any(v for v in d.values()):
            output.append(d)

    return output
