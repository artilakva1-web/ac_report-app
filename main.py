import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime

# ფონტის რეგისტრაცია
try:
    pdfmetrics.registerFont(TTFont('geo', 'dejavu-sans.book.ttf'))
except:
    st.error("ფონტი 'dejavu-sans.book.ttf' ვერ მოიძებნა!")

def clean_val(value):
    if pd.isna(value) or value == "": return 0.0
    val_str = str(value).replace(",", ".")
    cleaned = "".join(c for c in val_str if c.isdigit() or c in ".-")
    try: return float(cleaned)
    except: return 0.0

# ── პალიტრა ──────────────────────────────────────────────────────────────────
C_NAVY      = "#1B2A3B"
C_SLATE     = "#34495E"
C_LINE      = "#BDC3C7"
C_RED_HDR   = "#922B21"
C_GREEN_HDR = "#1D6A39"
C_TOTAL_BG  = "#EAF0FB"

st.set_page_config(page_title="ფინანსური მენეჯერი", layout="wide")

# ── გვერდითი პანელი (ყველა კონტროლი აქ არის) ───────────────────────────────────
with st.sidebar:
    st.header("⚙️ პარამეტრები")
    project_name     = st.text_input("პროექტის დასახელება", value="ახალი პროექტი")
    total_residents  = st.number_input("მესაკუთრეების რაოდენობა", min_value=1, value=1)
    tariff           = st.number_input("ტარიფი (GEL)", min_value=0.0, value=20.0, step=1.0)
    
    st.divider()
    st.subheader("💰 ფინანსები")
    previous_balance     = st.number_input("წინა თვის ნაშთი", value=0.0)
    expenses             = st.number_input("გაწეული ხარჯი", value=0.0)
    manager_salary_per_res = st.number_input("ხელფასი თითო ბინაზე (Gross)", value=2.0)
    
    st.divider()
    st.subheader("⚖️ გადასახადები (-20%)")
    apply_tax_income = st.checkbox("გამოაკლდეს შემოსავალს", value=True)
    apply_tax_salary = st.checkbox("გამოაკლდეს ხელფასს", value=True)
    
    st.divider()
    st.subheader("📄 PDF-ის კონტროლი")
    show_debtors_list = st.checkbox("მევალეების სია PDF-ში", value=True)
    show_advances_list = st.checkbox("ავანსების სია PDF-ში", value=True)
    
    st.divider()
    work_description = st.text_area("შესრულებული სამუშაოები")
    uploaded_file = st.file_uploader("CSV ფაილი", type=["csv"])

st.title(f"🏙️ {project_name}")

# ── მთავარი ლოგიკა ────────────────────────────────────────────────────────────
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        
        # მონაცემების გასუფთავება
        temp_df = pd.DataFrame({
            "სახელი": df.iloc[:, 1],
            "ვალი": df.iloc[:, -2].apply(clean_val),
            "ავანსი": df.iloc[:, -1].apply(clean_val)
        })
        temp_df = temp_df[temp_df["სახელი"].notna() & ~temp_df["სახელი"].str.contains("ჯამი|სულ", case=False, na=False)]
        
        debtors_df = temp_df[temp_df["ვალი"] > 0][["სახელი", "ვალი"]]
        advances_df = temp_df[temp_df["ავანსი"] > 0][["სახელი", "ავანსი"]]
        
        debtors_count = len(debtors_df)
        payers_count = total_residents - debtors_count
        
        # --- გამოთვლები ---
        tax_mult_inc = 0.8 if apply_tax_income else 1.0
        tax_mult_sal = 0.8 if apply_tax_salary else 1.0
        
        # შემოსავალი (მხოლოდ ვინც გადაიხადა)
        net_income = (payers_count * tariff) * tax_mult_inc
        
        # ხელფასი (დარიცხული ყველა ბინაზე)
        total_salary_gross = total_residents * manager_salary_per_res
        total_salary_net = total_salary_gross * tax_mult_sal
        
        # ნაშთი (შემოსავალი + წინა ნაშთი - ხარჯები)
        # ხელფასი აქ არ აკლდება, როგორც მთხოვეთ
        final_balance = (previous_balance + net_income) - expenses
        
        # --- PREVIEW ---
        st.subheader("📊 შეჯამება")
        col1, col2, col3 = st.columns(3)
        col1.metric("ამ თვის შემოსავალი", f"{net_income:.2f} GEL")
        col2.metric("გაწეული ხარჯი", f"{expenses:.2f} GEL")
        col3.metric("მიმდინარე ნაშთი", f"{final_balance:.2f} GEL")
        
        # --- PDF GENERATION ---
        if st.button("🚀 PDF-ის მომზადება"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
            PAGE_W = A4[0] - 4*cm
            
            def geo(size, align=1, bold=False):
                return ParagraphStyle('g', fontName='geo', fontSize=size, alignment=align, leading=size*1.5)

            elements = []
            
            # სათაური
            elements.append(Paragraph(project_name, geo(18, 1)))
            elements.append(Paragraph(f"ფინანსური ანგარიში - {datetime.now().strftime('%d/%m/%Y')}", geo(11, 1)))
            elements.append(Spacer(1, 20))
            
            # ცხრილი
            summary_data = [
                [Paragraph("დასახელება", geo(10, 0)), Paragraph("მნიშვნელობა", geo(10, 2))],
                [Paragraph("მესაკუთრეების რაოდენობა", geo(9, 0)), Paragraph(str(total_residents), geo(9, 2))],
                [Paragraph("მევალეების რაოდენობა", geo(9, 0)), Paragraph(str(debtors_count), geo(9, 2))],
                [Paragraph(f"ამ თვის შემოსავალი {'(-20%)' if apply_tax_income else ''}", geo(9, 0)), Paragraph(f"{net_income:.2f} GEL", geo(9, 2))],
                [Paragraph("წინა თვის ნაშთი (+)", geo(9, 0)), Paragraph(f"{previous_balance:.2f} GEL", geo(9, 2))],
                [Paragraph("გაწეული ხარჯი (-)", geo(9, 0)), Paragraph(f"{expenses:.2f} GEL", geo(9, 2))],
                [Paragraph("თავმჯდომარის ხელფასი (ინფო)", geo(9, 0)), Paragraph(f"{total_salary_gross:.2f} GEL", geo(9, 2))]
            ]
            
            if apply_tax_salary:
                summary_data.append([Paragraph("ხელფასი (ხელზე)", geo(9, 0)), Paragraph(f"{total_salary_net:.2f} GEL", geo(9, 2))])
            
            summary_data.append([Paragraph("მიმდინარე თვის ნაშთი", geo(10, 0)), Paragraph(f"{final_balance:.2f} GEL", geo(10, 2))])
            
            tbl = Table(summary_data, colWidths=[PAGE_W*0.7, PAGE_W*0.3])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(C_NAVY)),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor(C_TOTAL_BG)),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(tbl)
            
            # მევალეები
            if show_debtors_list and not debtors_df.empty:
                elements.append(PageBreak())
                elements.append(Paragraph("მევალეების სია", geo(14, 1)))
                d_list = [[Paragraph("მესაკუთრე", geo(10, 0)), Paragraph("დავალიანება", geo(10, 2))]]
                for _, r in debtors_df.iterrows():
                    d_list.append([Paragraph(str(r[0]), geo(9, 0)), Paragraph(f"{r[1]:.2f} GEL", geo(9, 2))])
                dt = Table(d_list, colWidths=[PAGE_W*0.7, PAGE_W*0.3])
                dt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor(C_RED_HDR)), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(dt)

            # ავანსები
            if show_advances_list and not advances_df.empty:
                elements.append(PageBreak())
                elements.append(Paragraph("ავანსების სია", geo(14, 1)))
                a_list = [[Paragraph("მესაკუთრე", geo(10, 0)), Paragraph("ავანსი", geo(10, 2))]]
                for _, r in advances_df.iterrows():
                    a_list.append([Paragraph(str(r[0]), geo(9, 0)), Paragraph(f"{r[1]:.2f} GEL", geo(9, 2))])
                at = Table(a_list, colWidths=[PAGE_W*0.7, PAGE_W*0.3])
                at.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor(C_GREEN_HDR)), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
                elements.append(at)

            doc.build(elements)
            st.download_button("📥 ჩამოტვირთეთ PDF", buffer.getvalue(), f"{project_name}.pdf", "application/pdf")

    except Exception as e:
        st.error(f"შეცდომა: {e}")
