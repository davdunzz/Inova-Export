import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from parser import parse_inova
from excel_export import export_xlsx

BG="#F3F7F4"; GREEN="#00843D"; GREEN_DARK="#006B31"; TEXT="#183027"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DLab Data Extractor • Inova")
        self.geometry("1250x820")
        self.minsize(1050,700)
        self.configure(bg=BG)
        self.rows=[]
        self.build_style()
        self.build_ui()

    def build_style(self):
        s=ttk.Style(self); s.theme_use("clam")
        s.configure("TFrame",background=BG)
        s.configure("Card.TFrame",background="white")
        s.configure("Title.TLabel",background=BG,foreground=TEXT,font=("Segoe UI",22,"bold"))
        s.configure("Sub.TLabel",background=BG,foreground="#5C7066",font=("Segoe UI",10))
        s.configure("TLabel",background=BG,foreground=TEXT,font=("Segoe UI",10))
        s.configure("CardLabel.TLabel",background="white",foreground=TEXT,font=("Segoe UI",11,"bold"))
        s.configure("CardSub.TLabel",background="white",foreground="#6A7B73",font=("Segoe UI",9))
        s.configure("Green.TButton",background=GREEN,foreground="white",font=("Segoe UI",10,"bold"),padding=(15,9))
        s.map("Green.TButton",background=[("active",GREEN_DARK)])
        s.configure("TButton",font=("Segoe UI",10),padding=(12,8))
        s.configure("Treeview",rowheight=30,font=("Segoe UI",9),background="white",fieldbackground="white",foreground=TEXT)
        s.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background=GREEN,foreground="white")

    def build_ui(self):
        top=ttk.Frame(self,padding=(28,20,28,8)); top.pack(fill="x")
        ttk.Label(top,text="DLab Data Extractor",style="Title.TLabel").pack(side="left")
        ttk.Label(top,text="Inova • estrazione dati locale",style="Sub.TLabel").pack(side="left",padx=15,pady=(8,0))
        ttk.Button(top,text="Apri file TXT/CSV",command=self.open_file).pack(side="right")

        main=ttk.Frame(self,padding=(28,8,28,20)); main.pack(fill="both",expand=True)

        left=ttk.Frame(main,style="Card.TFrame",padding=16); left.pack(side="left",fill="both",expand=True,padx=(0,10))
        ttk.Label(left,text="1. INCOLLA L'ESPORTAZIONE INOVA",style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(left,text="Incolla tutto il testo copiato dal gestionale, intestazioni comprese.",style="CardSub.TLabel").pack(anchor="w",pady=(3,10))
        self.text=tk.Text(left,wrap="none",font=("Consolas",9),bg="#FBFDFC",fg=TEXT,insertbackground=GREEN,relief="solid",bd=1)
        self.text.pack(fill="both",expand=True)

        actions=ttk.Frame(left,style="Card.TFrame"); actions.pack(fill="x",pady=(9,0))
        ttk.Button(actions,text="SVUOTA",command=lambda:self.text.delete("1.0","end")).pack(side="right")

        right=ttk.Frame(main,style="Card.TFrame",padding=16); right.pack(side="right",fill="y",padx=(10,0))
        ttk.Label(right,text="2. DATI DA ESTRARRE",style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(right,text="Configurazione fissa per l'esportazione Inova.",style="CardSub.TLabel").pack(anchor="w",pady=(3,12))
        fields=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]
        for f in fields:
            ttk.Label(right,text="✓  "+f,background="white",foreground=GREEN,font=("Segoe UI",10,"bold")).pack(anchor="w",pady=4)
        ttk.Separator(right).pack(fill="x",pady=12)
        ttk.Button(right,text="ELABORA DATI",style="Green.TButton",command=self.process).pack(fill="x")
        ttk.Button(right,text="ESPORTA EXCEL",command=self.save_excel).pack(fill="x",pady=(8,0))
        self.status=ttk.Label(right,text="Pronto. Incolla i dati e premi ELABORA DATI.",background="white",foreground="#61736A",wraplength=220)
        self.status.pack(anchor="w",pady=(14,0))

        bottom=ttk.Frame(self,padding=(28,0,28,22)); bottom.pack(fill="both",expand=True)
        ttk.Label(bottom,text="3. ANTEPRIMA RISULTATO",font=("Segoe UI",11,"bold"),background=BG,foreground=TEXT).pack(anchor="w",pady=(0,7))
        card=ttk.Frame(bottom,style="Card.TFrame",padding=1); card.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(card,show="headings")
        self.tree.pack(side="left",fill="both",expand=True)
        ys=ttk.Scrollbar(card,orient="vertical",command=self.tree.yview); ys.pack(side="right",fill="y")
        xs=ttk.Scrollbar(bottom,orient="horizontal",command=self.tree.xview); xs.pack(fill="x")
        self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)

    def open_file(self):
        p=filedialog.askopenfilename(filetypes=[("Testo/CSV","*.txt *.csv"),("Tutti i file","*.*")])
        if p:
            try:
                with open(p,"r",encoding="utf-8-sig",errors="replace") as f: data=f.read()
                self.text.delete("1.0","end"); self.text.insert("1.0",data)
            except Exception as e: messagebox.showerror("Errore",str(e))

    def process(self):
        raw=self.text.get("1.0","end")
        try:
            self.rows=parse_inova(raw)
            fields=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]
            self.tree.delete(*self.tree.get_children())
            self.tree["columns"]=fields
            for f in fields:
                self.tree.heading(f,text=f)
                self.tree.column(f,width=max(120,min(300,len(f)*13)))
            for r in self.rows:
                self.tree.insert("", "end", values=[r.get(f,"") for f in fields])
            self.status.config(text=f"✓ {len(self.rows)} pratiche riconosciute.",foreground=GREEN)
        except Exception as e:
            self.status.config(text="Nessun dato riconosciuto.",foreground="#B3261E")
            messagebox.showwarning("Nessun dato riconosciuto",str(e))

    def save_excel(self):
        if not self.rows:
            return messagebox.showwarning("Nessun dato","Prima premi ELABORA DATI.")
        fields=["Targa","Proprietario","Stato","Tipologia Sinistro","Marchio","Modello"]
        p=filedialog.asksaveasfilename(defaultextension=".xlsx",initialfile="dati_inova.xlsx",filetypes=[("Excel","*.xlsx")])
        if not p: return
        try:
            export_xlsx(p,self.rows,fields)
            messagebox.showinfo("Excel creato",f"File creato correttamente:\n{p}")
        except Exception as e: messagebox.showerror("Errore Excel",str(e))

if __name__=="__main__":
    App().mainloop()
