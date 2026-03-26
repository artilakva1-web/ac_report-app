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

# ფონტის რეგისტრაცია (ქართულისთვის)
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
    total_residents = st.number_input("მობინადრეების სულ რაოდენობა", min_value=1, value=100)
    tariff = st.number_input("ტარიფი ბალანსისთვის (GEL)", min_value=0.0, value=20.0, step=0.5)
    uploaded_file = st.file_uploader("ამოირჩიეთ CSV ფაილი", type=["csv"])

st.title(f"🏙️ {project_name}: ფინანსური მენეჯერი")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # მონაცემების დამუშავება (პოზიციური ლოგიკა შენარჩუნებულია)
        names = df.iloc[:, 1]
        debts = df.iloc[:, -2].apply(clean_val)
        advances = df.iloc[:, -1].apply(clean_val)

        temp_df = pd.DataFrame({"სახელი": names, "ვალი": debts, "ავანსი": advances})
        temp_df = temp_df[temp_df["სახელი"].notna() & ~temp_df["სახელი"].str.contains("ჯამი|სულ|total", case=False, na=False)]

        debtors_df = temp_df[temp_df["ვალი"] > 0]
        advances_df = temp_df[temp_df["ავანსი"] > 0]

        debtors_count = len(debtors_df)
        # შენი ფორმულა: (სულ - მევალეები) * ტარიფი
        building_balance = (total_residents - debtors_count) * tariff
        
        # --- PREVIEW ---
        st.subheader("📊 წინასწარი გადახედვა")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("მევალეები", debtors_count)
        c2.metric("ბალანსი", f"{building_balance:.2f} GEL")
        c3.metric("ჯამური ვალი", f"{debtors_df['ვალი'].sum():.2f} GEL")
        c4.metric("ჯამური ავანსი", f"{advances_df['ავანსი'].sum():.2f} GEL")

        tab1, tab2 = st.tabs(["🔴 მევალეების სია", "🟢 ავანსების სია"])
        tab1.dataframe(debtors_df, use_container_width=True)
        tab2.dataframe(advances_df, use_container_width=True)

        # --- PDF გენერაცია ---
        if st.button("🚀 დააგენერირე PDF ანგარიში", type="primary"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            
            title_s = ParagraphStyle('Title', fontName='geo', fontSize=18, alignment=1)
            section_s = ParagraphStyle('Section', fontName='geo', fontSize=14, alignment=1, spaceAfter=10)

            elements.append(Paragraph(f"პროექტი: {project_name}", title_s))
            elements.append(Paragraph("ფინანსური ანგარიშგება", title_s))
            elements.append(Spacer(1, 20))

            summary_data = [
                ["დასახელება", "მნიშვნელობა"],
                ["მობინადრეების სულ რაოდენობა", str(total_residents)],
                ["მევალეების რაოდენობა", str(debtors_count)],
                ["ტარიფი ერთ მობინადრეზე", f"{tariff} GEL"],
                ["კორპუსის ბალანსი (დათვლილი)", f"{building_balance:.2f} GEL"],
                ["ჯამური დავალიანება", f"{debtors_df['ვალი'].sum():.2f} GEL"]
            ]
            st_table = Table(summary_data, colWidths=[9*cm, 5*cm])
            st_table.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2C3E50")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("BACKGROUND", (0, 4), (1, 4), colors.lightgreen), # ბალანსის ხაზი
            ]))
            elements.append(st_table)
            elements.append(PageBreak())

            # მევალეების ცხრილი
            elements.append(Paragraph("მევალეების სია", section_s))
            d_list = [["მესაკუთრე", "ვალი"]] + debtors_df.values.tolist()
            dt = Table(d_list, colWidths=[10*cm, 4*cm], repeatRows=1)
            dt.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.indianred), ("TEXTCOLOR", (0,0), (-1,0), colors.white)
            ]))
            elements.append(dt)
            elements.append(PageBreak())

            # ავანსების ცხრილი
            elements.append(Paragraph("ავანსების სია", section_s))
            a_list = [["მესაკუთრე", "ავანსი"]] + advances_df.values.tolist()
            at = Table(a_list, colWidths=[10*cm, 4*cm], repeatRows=1)
            at.setStyle(TableStyle([
                ("FONTNAME", (0,0), (-1,-1), "geo"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.seagreen), ("TEXTCOLOR", (0,0), (-1,0), colors.white)
            ]))
            elements.append(at)

            doc.build(elements)
            st.download_button(f"📥 ჩამოტვირთეთ {project_name}_Report.pdf", buffer.getvalue(), f"{project_name}_Report.pdf", "application/pdf")

    except Exception as e:
        st.error(f"შეცდომა ფაილის დამუშავებისას: {e}")