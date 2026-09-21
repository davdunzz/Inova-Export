import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parser import parse_export, AVAILABLE_FIELDS
from excel_export import export_xlsx

BG = "#F4F8F5"
GREEN = "#00843D"
GREEN_DARK = "#006B31"
GREEN_LIGHT = "#E7F4EC"
TEXT = "#183027"
BORDER = "#C9D9CF"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DLab Data Extractor")
        self.geometry("1250x820")
        self.minsize(1000, 680)
        self.configure(bg=BG)
        self.rows = []
        self.selected_fields = ["Targa", "Proprietario", "Stato", "Tipologia Sinistro", "Marchio", "Modello"]
        self.vars = {}
        self.build_style()
        self.build_ui()

    def build_style(self):
        s=ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background="white")
        s.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 22, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground="#5B6E64", font=("Segoe UI", 10))
        s.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(14,8))
        s.configure("Green.TButton", background=GREEN, foreground="white")
        s.map("Green.TButton", background=[("active", GREEN_DARK)])
        s.configure("Treeview", rowheight=29, font=("Segoe UI", 9), background="white", fieldbackground="white", foreground=TEXT)
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background=GREEN, foreground="white", relief="flat")
        s.configure("TCheckbutton", background="white", foreground=TEXT, font=("Segoe UI", 9))

    def build_ui(self):
        top=ttk.Frame(self, padding=(28,22,28,10)); top.pack(fill="x")
        ttk.Label(top, text="DLab Data Extractor", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="Inova • estrazione dati locale", style="Sub.TLabel").pack(side="left", padx=16, pady=(10,0))
        ttk.Button(top, text="Apri file TXT/CSV", command=self.open_file).pack(side="right")

        body=ttk.Frame(self, padding=(28,8,28,20)); body.pack(fill="both", expand=True)

        left=ttk.Frame(body, style="Card.TFrame", padding=16); left.pack(side="left", fill="both", expand=True, padx=(0,10))
        ttk.Label(left, text="1. INCOLLA L'ESPORTAZIONE", font=("Segoe UI",11,"bold"), background="white", foreground=TEXT).pack(anchor="w")
        ttk.Label(left, text="Incolla direttamente il testo copiato dal gestionale.", background="white", foreground="#6B7D74").pack(anchor="w", pady=(3,10))
        self.text=tk.Text(left, wrap="none", font=("Consolas",9), bg="#FBFDFC", fg=TEXT, insertbackground=GREEN, relief="solid", bd=1)
        self.text.pack(fill="both", expand=True)
        ttk.Button(left, text="SVUOTA", command=lambda:self.text.delete("1.0","end")).pack(anchor="e", pady=(8,0))

        right=ttk.Frame(body, style="Card.TFrame", padding=16); right.pack(side="right", fill="y", padx=(10,0))
        ttk.Label(right, text="2. CAMPI DA ESTRARRE", font=("Segoe UI",11,"bold"), background="white", foreground=TEXT).pack(anchor="w")
        ttk.Label(right, text="Seleziona le colonne per l'Excel.", background="white", foreground="#6B7D74").pack(anchor="w", pady=(3,12))
        for f in AVAILABLE_FIELDS:
            v=tk.BooleanVar(value=f in self.selected_fields); self.vars[f]=v
            ttk.Checkbutton(right, text=f, variable=v).pack(anchor="w", pady=2)
        ttk.Separator(right).pack(fill="x", pady=12)
        ttk.Button(right, text="ELABORA DATI", style="Green.TButton", command=self.process).pack(fill="x")
        ttk.Button(right, text="ESPORTA EXCEL", command=self.save_excel).pack(fill="x", pady=(8,0))
        self.status=ttk.Label(right, text="Pronto.", background="white", foreground=GREEN, wraplength=210)
        self.status.pack(anchor="w", pady=(14,0))

        bottom=ttk.Frame(self, padding=(28,0,28,22)); bottom.pack(fill="both", expand=True)
        ttk.Label(bottom, text="3. ANTEPRIMA", font=("Segoe UI",11,"bold"), background=BG, foreground=TEXT).pack(anchor="w", pady=(0,7))
        card=ttk.Frame(bottom, style="Card.TFrame", padding=1); card.pack(fill="both", expand=True)
        self.tree=ttk.Treeview(card, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)
        ys=ttk.Scrollbar(card, orient="vertical", command=self.tree.yview); ys.pack(side="right", fill="y")
        xs=ttk.Scrollbar(bottom, orient="horizontal", command=self.tree.xview); xs.pack(fill="x")
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

    def open_file(self):
        p=filedialog.askopenfilename(filetypes=[("Testo/CSV","*.txt *.csv"),("Tutti i file","*.*")])
        if p:
            try:
                with open(p,"r",encoding="utf-8-sig",errors="replace") as f: data=f.read()
                self.text.delete("1.0","end"); self.text.insert("1.0",data)
            except Exception as e: messagebox.showerror("Errore", str(e))

    def process(self):
        raw=self.text.get("1.0","end").strip()
        fields=[f for f,v in self.vars.items() if v.get()]
        if not raw: return messagebox.showwarning("Dati mancanti","Incolla prima l'esportazione.")
        if not fields: return messagebox.showwarning("Campi mancanti","Seleziona almeno un campo.")
        try:
            self.rows=parse_export(raw, fields)
            self.refresh_table(fields)
            self.status.config(text=f"Elaborate {len(self.rows)} righe.", foreground=GREEN)
        except Exception as e:
            messagebox.showerror("Errore di elaborazione", str(e))

    def refresh_table(self, fields):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"]=fields
        for f in fields:
            self.tree.heading(f,text=f); self.tree.column(f,width=max(110,min(260,len(f)*12)))
        for r in self.rows:
            self.tree.insert("", "end", values=[r.get(f,"") for f in fields])

    def save_excel(self):
        if not self.rows:
            return messagebox.showwarning("Nessun dato","Prima premi ELABORA DATI.")
        fields=[f for f,v in self.vars.items() if v.get()]
        p=filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="dati_inova.xlsx", filetypes=[("Excel","*.xlsx")])
        if not p: return
        try:
            export_xlsx(p, self.rows, fields)
            messagebox.showinfo("Esportazione completata", f"File creato:\n{p}")
        except Exception as e: messagebox.showerror("Errore Excel", str(e))

if __name__=="__main__":
    App().mainloop()
