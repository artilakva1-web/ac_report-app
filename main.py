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
    
    st.divider()
    st.subheader("🛠️ დამატებითი ინფორმაცია")
    free_work_description = st.text_area("უფასოდ შესრულებული სამუშაოები", placeholder="მაგ: გენერალური დალაგება საჩუქრად...")
    
    st.divider()
    uploaded_file = st.file_uploader("ამოირჩიეთ CSV ფაილი", type=["csv"])

st.title(f"🏙️ {project_name}: ფინანსური მენეჯერი")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        names = df.iloc[:, 1]
        debts = df.iloc[:, -2].apply(clean_val)
        advances = df.iloc[:, -1].apply(clean_val)

        temp_df = pd.DataFrame({"სახელი": names, "ვალი": debts, "ავანსი": advances})
        temp_df = temp_df[temp_df["სახელი"].notna() & ~temp_df["სახელი"].str.contains("ჯამი|სულ|total", case=False, na=False)]

        debtors_df = temp_df[temp_df["ვალი"] > 0][["სახელი", "ვალი"]]
        advances_df = temp_df[temp_df["ავანსი"] > 0][["სახელი", "ავანსი"]]

        debtors_count = len(debtors_df)
        total_debt_sum = debtors_df["ვალი"].sum()
        total_advance_sum = advances_df["ავანსი"].sum()
        
        # --- გამოთვლები ---
        new_collection = (total_residents - debtors_count) * tariff
        total_available = previous_balance + new_collection
        final_monthly_balance = total_available - expenses
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        
        # --- PREVIEW ---
        st.subheader("📊 ფინანსური შეჯამება")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ამ თვის შემოსავალი", f"{new_collection:.2f} GEL")
        c2.metric("ჯამური ბალანსი", f"{total_available:.2f} GEL")
        c3.metric("გაწეული ხარჯი", f"-{expenses:.2f} GEL")
        c4.metric("მიმდინარე ნაშთი", f"{final_monthly_balance:.2f} GEL")

        # --- PDF გენერაცია ---
        if st.button("🚀 დააგენერირე PDF ანგარიში", type="primary"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            title_s = ParagraphStyle('Title', fontName='geo', fontSize=18, alignment=1, spaceAfter=5)
            date_s = ParagraphStyle('Date', fontName='geo', fontSize=10, alignment=1, spaceAfter=20)
            section_s = ParagraphStyle('Section', fontName='geo', fontSize=14, alignment=1, spaceAfter=10)
            text_s = ParagraphStyle('Text', fontName='geo', fontSize=11, leading=14)
            bold_text_s = ParagraphStyle('BoldText', fontName='geo', fontSize=11, leading=14, spaceBefore=10)

            elements.append(Paragraph(f"პროექტი: {project_name}", title_s))
            elements.append(Paragraph("ფინანსური ანგარიშგება", title_s))
            elements.append(Paragraph(f"შექმნის თარიღი: {today_str}", date_s))

            summary_data = [
                ["დასახელება", "მნიშვნელობა"],
                ["მობინადრეების სულ რაოდენობა", str(total_residents)],
                ["მევალეების რაოდენობა", str(debtors_count)],
                ["ამ თვის დარიცხული (შემოსავალი)", f"{new_collection:.2f} GEL"],
                ["წინა თვის ნაშთი (+)", f"{previous_balance:.2f} GEL"],
                ["ჯამური თანხა (ხარჯამდე)", f"{total_available:.2f} GEL"],
                ["შესრულებული სამუშაოების ხარჯი (-)", f"{expenses:.2f} GEL"],
                ["მიმდინარე თვის ნაშთი (ნეტო)", f"{final_monthly_balance:.2f} GEL"]
            ]
            
            st_table = Table(summary_data, colWidths=[9.5*cm, 5*cm])
            st_table.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("BACKGROUND", (0, -1), (1, -1), colors.lightgreen),
                ("FONTSIZE", (0, -1), (1, -1), 12),
            ]))
            elements.append(st_table)
            
            # ფასიანი სამუშაოები
            if work_description:
                elements.append(Spacer(1, 15))
                elements.append(Paragraph("<b>🛠️ შესრულებული სამუშაოების დეტალები (ხარჯიანი):</b>", bold_text_s))
                elements.append(Paragraph(work_description.replace('\n', '<br/>'), text_s))

            # უფასო სამუშაოები
            if free_work_description:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("<b>✨ დამატებითი სამუშაოები (ხარჯის გარეშე):</b>", bold_text_s))
                elements.append(Paragraph(free_work_description.replace('\n', '<br/>'), text_s))

            elements.append(PageBreak())

            # მევალეები + ჯამი
            elements.append(Paragraph("მევალეების სია", section_s))
            d_list = [["მესაკუთრე", "დავალიანება"]] + debtors_df.values.tolist()
            d_list.append(["სულ ჯამური დავალიანება:", f"{total_debt_sum:.2f}"]) # ჯამი
            
            dt = Table(d_list, colWidths=[11*cm, 4*cm], repeatRows=1)
            dt.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.indianred), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey), # ჯამის ხაზი
                ("FONTNAME", (0, -1), (-1, -1), "geo"),
            ]))
            elements.append(dt)
            elements.append(PageBreak())

            # ავანსები + ჯამი
            elements.append(Paragraph("ავანსების სია", section_s))
            a_list = [["მესაკუთრე", "ავანსი"]] + advances_df.values.tolist()
            a_list.append(["სულ ჯამური ავანსი:", f"{total_advance_sum:.2f}"]) # ჯამი
            
            at = Table(a_list, colWidths=[11*cm, 4*cm], repeatRows=1)
            at.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.seagreen), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey), # ჯამის ხაზი
                ("FONTNAME", (0, -1), (-1, -1), "geo"),
            ]))
            elements.append(at)

            doc.build(elements)
            st.download_button(f"📥 ჩამოტვირთეთ {project_name}_Report.pdf", buffer.getvalue(), f"{project_name}_Report.pdf", "application/pdf")

    except Exception as e:
        st.error(f"შეცდომა: {e}")
