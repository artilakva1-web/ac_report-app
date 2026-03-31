import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os
from datetime import datetime

# --- ფონტის რეგისტრაცია (შეცვლილია სახელი უფრო სტანდარტულით) ---
FONT_PATH = 'DejaVuSans.ttf' # დარწმუნდით რომ GitHub-ზე ზუსტად ეს სახელი აქვს!
try:
    pdfmetrics.registerFont(TTFont('geo', FONT_PATH))
    main_font = 'geo'
except:
    st.error(f"❌ ფონტი '{FONT_PATH}' ვერ მოიძებნა! ატვირთეთ იგივე საქაღალდეში.")
    main_font = 'Helvetica' # fallback, მაგრამ ქართულს ვერ აჩვენებს

def clean_val(value):
    if pd.isna(value) or value == "": return 0.0
    val_str = str(value).replace(",", ".")
    cleaned = "".join(c for c in val_str if c.isdigit() or c in ".-")
    try: return float(cleaned)
    except: return 0.0

st.set_page_config(page_title="Financial Manager", layout="wide")

# --- ინტერფეისი ---
with st.sidebar:
    st.header("⚙️ პარამეტრები")
    project_name = st.text_input("პროექტის დასახელება", value="ახალი პროექტი")
    total_residents = st.number_input("მობინადრეების რაოდენობა", min_value=1, value=174)
    tariff = st.number_input("ტარიფი (GEL)", min_value=0.0, value=20.0, step=0.5)
    previous_balance = st.number_input("წინა თვის ნაშთი (GEL)", value=0.0)
    expenses = st.number_input("გაწეული ხარჯი (GEL)", value=0.0)
    manager_salary = st.number_input("თავმჯდომარის ხელფასი (GEL - დარიცხული)", value=0.0)
    work_description = st.text_area("შესრულებული სამუშაოები")
    free_work_description = st.text_area("დამატებითი (უფასო) სამუშაოები")
    
    st.divider()
    uploaded_file = st.file_uploader("ამოირჩიეთ CSV ფაილი", type=["csv"])

if uploaded_file:
    try:
        # ვკითხულობთ CSV-ს
        df = pd.read_csv(uploaded_file)
        
        # ვცდილობთ ვიპოვოთ სვეტები დასახელებებით
        # თუ თქვენს CSV-ში სხვა სახელებია, შეცვალეთ აქ:
        name_col = df.columns[1] # მეორე სვეტი ჩვეულებრივ სახელია
        debt_col = df.columns[-2] # ბოლოსწინა - დავალიანება
        adv_col = df.columns[-1]  # ბოლო - ავანსი
        
        names = df[name_col]
        debts = df[debt_col].apply(clean_val)
        advances = df[adv_col].apply(clean_val)

        temp_df = pd.DataFrame({"სახელი": names, "ვალი": debts, "ავანსი": advances})
        # ვფილტრავთ ცარიელებს და ჯამებს
        temp_df = temp_df[temp_df["სახელი"].notna() & ~temp_df["სახელი"].astype(str).str.contains("ჯამი|სულ|total|Total", case=False)]

        debtors_df = temp_df[temp_df["ვალი"] > 0.1].copy()
        advances_df = temp_df[temp_df["ავანსი"] > 0.1].copy()

        debtors_count = len(debtors_df)
        total_debt_sum = debtors_df["ვალი"].sum()
        total_advance_sum = advances_df["ავანსი"].sum()
        
        # გამოთვლები
        collected_raw = (total_residents - debtors_count) * tariff
        net_collection = collected_raw * 0.8
        net_salary = manager_salary * 0.8
        total_available = previous_balance + net_collection
        final_monthly_balance = total_available - expenses - manager_salary
        
        st.success("✅ მონაცემები წარმატებით დამუშავდა!")
        
        # --- PDF გენერაცია ---
        if st.button("🚀 დააგენერირე PDF ანგარიში", type="primary"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            
            # სტილები (მნიშვნელოვანია fontName='geo')
            title_s = ParagraphStyle('Title', fontName='geo', fontSize=16, alignment=1, spaceAfter=10)
            text_s = ParagraphStyle('Text', fontName='geo', fontSize=10, leading=12)
            
            # ლოგო
            if os.path.exists("logo.png"):
                img = Image("logo.png", width=2.5*cm, height=2.5*cm)
                img.hAlign = 'CENTER'
                elements.append(img)
                elements.append(Spacer(1, 10))

            elements.append(Paragraph(f"პროექტი: {project_name}", title_s))
            elements.append(Paragraph(f"თარიღი: {datetime.now().strftime('%d/%m/%Y')}", text_s))
            elements.append(Spacer(1, 15))

            # შეჯამების ცხრილი
            summary_data = [
                [Paragraph("დასახელება", text_s), Paragraph("მნიშვნელობა", text_s)],
                [Paragraph("შემოსავალი (Netto -20%)", text_s), f"{net_collection:.2f} GEL"],
                [Paragraph("წინა თვის ნაშთი", text_s), f"{previous_balance:.2f} GEL"],
                [Paragraph("ხარჯები (სამუშაოები)", text_s), f"{expenses:.2f} GEL"]
            ]
            
            if manager_salary > 0:
                summary_data.append([Paragraph("თავმჯდომარის ხელფასი (Gross)", text_s), f"{manager_salary:.2f} GEL"])
                summary_data.append([Paragraph("ხელზე ასაღები (Netto)", text_s), f"{net_salary:.2f} GEL"])
            
            summary_data.append([Paragraph("<b>მიმდინარე ნაშთი</b>", text_s), f"<b>{final_monthly_balance:.2f} GEL</b>"])

            ts = Table(summary_data, colWidths=[9*cm, 6*cm])
            ts.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'geo'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(ts)
            
            # მევალეების სია
            if not debtors_df.empty:
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("<b>მევალეების სია:</b>", text_s))
                d_table_data = [[Paragraph("ბინა/სახელი", text_s), Paragraph("ვალი", text_s)]]
                for _, row in debtors_df.iterrows():
                    # აქ ვიყენებთ Paragraph-ს, რომ ქართული ტექსტი აუცილებლად გამოჩნდეს
                    d_table_data.append([Paragraph(str(row["სახელი"]), text_s), f"{row['ვალი']:.2f}"])
                
                dt = Table(d_table_data, colWidths=[11*cm, 4*cm], repeatRows=1)
                dt.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'geo'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('BACKGROUND', (0,0), (-1,0), colors.indianred),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ]))
                elements.append(dt)

            doc.build(elements)
            st.download_button("📥 ჩამოტვირთეთ PDF", buffer.getvalue(), "Report.pdf", "application/pdf")

    except Exception as e:
        st.error(f"❌ მოხდა შეცდომა: {e}")
