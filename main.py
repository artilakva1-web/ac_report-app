import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
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

st.set_page_config(page_title="Universal Report Tool", layout="wide")

# --- ინტერფეისი ---
with st.sidebar:
    st.header("⚙️ პარამეტრები")
    project_name = st.text_input("პროექტის დასახელება", value="ახალი პროექტი")
    total_residents = st.number_input("მობინადრეების სულ რაოდენობა", min_value=1, value=174)
    tariff = st.number_input("ტარიფი მობინადრეზე (GEL)", min_value=0.0, value=20.0, step=0.5)
    
    st.divider()
    st.subheader("💰 ფინანსური ნაშთი")
    previous_balance = st.number_input("წინა თვის ნაშთი (GEL)", value=0.0, step=10.0)
    work_description = st.text_area("შესრულებული სამუშაოები (ფასიანი)", placeholder="მაგ: ლიფტის შეკეთება...")
    expenses = st.number_input("გაწეული ხარჯი (GEL)", min_value=0.0, value=0.0, step=10.0)
    manager_salary = st.number_input("თავმჯდომარის ხელფასი (დარიცხული GEL)", min_value=0.0, value=0.0, step=10.0)
    
    st.divider()
    uploaded_file = st.file_uploader("ამოირჩიეთ CSV ფაილი", type=["csv"])

st.title(f"🏙️ {project_name}: ფინანსური მენეჯერი")

if uploaded_file:
    try:
        # მნიშვნელოვანი: utf-8-sig შველის ქართულ ტექსტს CSV-ში
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        
        # თუ მაინც კითხვის ნიშნებია, ვცადოთ სხვა კოდირება
        if df.iloc[:, 1].astype(str).str.contains('').any():
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='cp1251')

        names = df.iloc[:, 1].astype(str)
        debts = df.iloc[:, -2].apply(clean_val)
        advances = df.iloc[:, -1].apply(clean_val)

        temp_df = pd.DataFrame({"სახელი": names, "ვალი": debts, "ავანსი": advances})
        temp_df = temp_df[temp_df["სახელი"].notna() & ~temp_df["სახელი"].str.contains("ჯამი|სულ|total", case=False, na=False)]

        debtors_df = temp_df[temp_df["ვალი"] > 0][["სახელი", "ვალი"]]
        advances_df = temp_df[temp_df["ავანსი"] > 0][["სახელი", "ავანსი"]]

        debtors_count = len(debtors_df)
        total_debt_sum = debtors_df["ვალი"].sum()
        total_advance_sum = advances_df["ავანსი"].sum()
        
        # გამოთვლები
        raw_collection = (total_residents - debtors_count) * tariff
        net_collection = raw_collection * 0.8
        total_available = previous_balance + net_collection
        final_monthly_balance = total_available - expenses - manager_salary
        net_salary = manager_salary * 0.8
        
        # PREVIEW ეკრანზე
        st.subheader("📊 ფინანსური შეჯამება")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("წმინდა შემოსავალი (-20%)", f"{net_collection:.2f} GEL")
        c2.metric("ჯამური ბალანსი", f"{total_available:.2f} GEL")
        c3.metric("ხარჯი + ხელფასი", f"-{(expenses + manager_salary):.2f} GEL")
        c4.metric("მიმდინარე ნაშთი", f"{final_monthly_balance:.2f} GEL")

        tab1, tab2 = st.tabs(["🔴 მევალეების სია", "🟢 ავანსების სია"])
        with tab1:
            st.dataframe(debtors_df, use_container_width=True)
        with tab2:
            st.dataframe(advances_df, use_container_width=True)

        if st.button("🚀 დააგენერირე PDF ანგარიში", type="primary"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []
            
            # სტილები
            cell_text_s = ParagraphStyle('CellText', fontName='geo', fontSize=10, leading=12)
            title_s = ParagraphStyle('Title', fontName='geo', fontSize=18, alignment=1)
            
            elements.append(Paragraph(f"პროექტი: {project_name}", title_s))
            elements.append(Spacer(1, 20))

            # შეჯამების ცხრილი
            summary_data = [
                [Paragraph("დასახელება", cell_text_s), Paragraph("მნიშვნელობა", cell_text_s)],
                [Paragraph("შემოსავალი (წმინდა)", cell_text_s), f"{net_collection:.2f}"],
                [Paragraph("ჯამური ნაშთი", cell_text_s), f"{final_monthly_balance:.2f}"]
            ]
            if manager_salary > 0:
                summary_data.append([Paragraph("ხელფასი (დარიცხული)", cell_text_s), f"{manager_salary:.2f}"])

            st_table = Table(summary_data, colWidths=[10*cm, 5*cm])
            st_table.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(st_table)
            elements.append(PageBreak())

            # მევალეების სია (აუცილებელია Paragraph უჯრაში ქართულისთვის)
            elements.append(Paragraph("მევალეების სია", title_s))
            d_list = [[Paragraph("მესაკუთრე", cell_text_s), Paragraph("დავალიანება", cell_text_s)]]
            for row in debtors_df.values.tolist():
                d_list.append([Paragraph(str(row[0]), cell_text_s), f"{row[1]:.2f}"])
            
            dt = Table(d_list, colWidths=[11.5*cm, 3.5*cm])
            dt.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(dt)

            doc.build(elements)
            st.download_button("📥 ჩამოტვირთეთ PDF", buffer.getvalue(), "Report.pdf", "application/pdf")

    except Exception as e:
        st.error(f"შეცდომა: {e}")
