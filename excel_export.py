from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def export_xlsx(path,rows,fields):
    wb=Workbook(); ws=wb.active; ws.title="Inova"
    ws.freeze_panes="A2"
    green="00843D"
    for i,f in enumerate(fields,1):
        c=ws.cell(1,i,f); c.font=Font(bold=True,color="FFFFFF")
        c.fill=PatternFill("solid",fgColor=green); c.alignment=Alignment(horizontal="center")
    thin=Side(style="thin",color="D6E1DA")
    for r,row in enumerate(rows,2):
        for c,f in enumerate(fields,1):
            cell=ws.cell(r,c,row.get(f,""))
            cell.border=Border(bottom=thin)
            if r%2==0: cell.fill=PatternFill("solid",fgColor="F2F8F4")
    for i,f in enumerate(fields,1):
        width=max(12,len(f)+2,max([len(str(x.get(f,""))) for x in rows]+[0])+2)
        ws.column_dimensions[get_column_letter(i)].width=min(width,42)
    ws.auto_filter.ref=f"A1:{get_column_letter(len(fields))}{len(rows)+1}"
    wb.save(path)
