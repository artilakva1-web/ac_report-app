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
C_SILVER    = "#F4F6F8"
C_LINE      = "#BDC3C7"
C_RED_HDR   = "#922B21"
C_GREEN_HDR = "#1D6A39"
C_TOTAL_BG  = "#EAF0FB"
C_WHITE     = "#FFFFFF"

st.set_page_config(page_title="Universal Report Tool", layout="wide")

# ── გვერდითი პანელი ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ პარამეტრები")
    project_name     = st.text_input("პროექტის დასახელება", value="ახალი პროექტი")
    total_residents  = st.number_input("მობინადრეების რაოდენობა", min_value=1, value=1)
    tariff           = st.number_input("ტარიფი მობინადრეზე (GEL)", min_value=0.0, value=20.0, step=0.5)

    st.divider()
    st.subheader("💰 ფინანსური ნაშთი")
    previous_balance     = st.number_input("წინა თვის ნაშთი (GEL)", value=0.0, step=10.0)
    work_description     = st.text_area("შესრულებული სამუშაოები (ფასიანი)", placeholder="მაგ: ლიფტის შეკეთება...")
    expenses             = st.number_input("გაწეული ხარჯი (GEL)", min_value=0.0, value=0.0, step=10.0)
    manager_salary_gross = st.number_input("თავმჯდომარის ხელფასი (დარიცხული - Gross)", min_value=0.0, value=0.0, step=10.0)

    st.divider()
    st.subheader("⚙️ გადასახადები")
    apply_tax_income = st.checkbox("გამოაკლდეს საშემოსავლო შემოსავალს (20%)", value=True)
    apply_tax_salary = st.checkbox("გამოაკლდეს საშემოსავლო ხელფასს (20%)", value=True)

    st.divider()
    st.subheader("📄 PDF-ის პარამეტრები")
    show_debtors_list = st.checkbox("გამოჩნდეს მევალეების სია PDF-ში", value=True)
    show_advances_list = st.checkbox("გამოჩნდეს ავანსების სია PDF-ში", value=True)

    st.divider()
    st.subheader("🛠️ დამატებითი ინფორმაცია")
    free_work_description = st.text_area("უფასოდ შესრულებული სამუშაოები", placeholder="მაგ: გენერალური დალაგება საჩუქრად...")

    st.divider()
    uploaded_file = st.file_uploader("ამოირჩიეთ CSV ფაილი", type=["csv"])

st.title(f"🏙️ {project_name}: ფინანსური მენეჯერი")

# ── მთავარი ლოგიკა ────────────────────────────────────────────────────────────
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

        names    = df.iloc[:, 1]
        debts    = df.iloc[:, -2].apply(clean_val)
        advances = df.iloc[:, -1].apply(clean_val)

        temp_df = pd.DataFrame({"სახელი": names, "ვალი": debts, "ავანსი": advances})
        temp_df = temp_df[
            temp_df["სახელი"].notna() &
            ~temp_df["სახელი"].str.contains("ჯამი|სულ|total", case=False, na=False)
        ]

        debtors_df  = temp_df[temp_df["ვალი"]   > 0][["სახელი", "ვალი"]]
        advances_df = temp_df[temp_df["ავანსი"] > 0][["სახელი", "ავანსი"]]

        debtors_count     = len(debtors_df)
        total_debt_sum    = debtors_df["ვალი"].sum()
        total_advance_sum = advances_df["ავანსი"].sum()

        # --- გამოთვლის ნაწილი (ეს ჩაანაცვლე შენს კოდში) ---
        payers_count = total_residents - debtors_count 
        
        # კოეფიციენტები გადასახადებისთვის
        tax_inc_multiplier = 0.8 if _income else 1.0
        tax_sal_multiplier = 0.8 if _salary else 1.0
        
        # 1. შემოსავალი (მხოლოდ გადამხდელებისგან)
        raw_collection = payers_count * tariff
        net_collection = raw_collection * tax_inc_multiplier
        
        # 2. თავმჯდომარის ხელფასი (გადამხდელების რაოდენობა * დადგენილი ხელფასი ერთ მობინადრეზე)
        # თუ გინდა რომ ხელფასი ფიქსირებული იყოს და არ იცვლებოდეს მევალეების მიხედვით, 
        # მაშინ აქ payers_count-ის ნაცვლად ჩაწერე total_residents
        total_manager_salary_gross = payers_count * manager_salary_gross
        manager_salary_net = total_manager_salary_gross * tax_sal_multiplier
        
        # 3. ბალანსი (ხელფასის გამოკლების გარეშე, როგორც მთხოვე)
        total_available = previous_balance + net_collection
        final_monthly_balance = total_available - expenses

        today_str = datetime.now().strftime("%d/%m/%Y")

        # ── PREVIEW ──────────────────────────────────────────────────────────
        st.subheader("📊 ფინანსური შეჯამება")
        c1, c2, c3, c4 = st.columns(4)
        
        inc_preview_label = "წმინდა შემოსავალი (-20%)" if _income else "ჯამური შემოსავალი"
        c1.metric(inc_preview_label, f"{net_collection:.2f} GEL")
        c2.metric("ხელმისაწვდომი ჯამში", f"{total_available:.2f} GEL")
        c3.metric("მიმდინარე ხარჯი", f"-{expenses:.2f} GEL")
        c4.metric("მიმდინარე ნაშთი", f"{final_monthly_balance:.2f} GEL")

        tab1, tab2 = st.tabs(["🔴 მევალეების სია", "🟢 ავანსების სია"])
        with tab1:
            st.dataframe(debtors_df, use_container_width=True)
            st.write(f"**ჯამური დავალიანება: {total_debt_sum:.2f} GEL**")
        with tab2:
            st.dataframe(advances_df, use_container_width=True)
            st.write(f"**ჯამური ავანსი: {total_advance_sum:.2f} GEL**")

        # ── PDF გენერაცია ─────────────────────────────────────────────────────
        if st.button("🚀 დააგენერირე PDF ანგარიში", type="primary"):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                rightMargin=2*cm, leftMargin=2*cm,
                topMargin=2*cm,   bottomMargin=2*cm
            )
            PAGE_W = A4[0] - 4*cm

            def geo(size, align=1, leading=None, color=colors.HexColor("#1B2A3B"),
                    space_before=0, space_after=0):
                return ParagraphStyle(
                    'g', fontName='geo', fontSize=size,
                    leading=leading or max(size * 1.45, size + 6),
                    alignment=align, textColor=color,
                    spaceBefore=space_before, spaceAfter=space_after
                )

            title_s      = geo(18, align=1, space_after=4)
            subtitle_s   = geo(11, align=1, color=colors.HexColor(C_SLATE), space_after=2)
            date_s       = geo(9,  align=1, color=colors.HexColor("#7F8C8D"), space_after=0)
            section_s    = geo(13, align=1, color=colors.HexColor(C_NAVY), space_before=20, space_after=10)
            cell_s       = geo(9,  align=0, leading=14)
            cell_right_s = geo(9,  align=2, leading=14)
            cell_bold_s  = geo(9,  align=0, leading=14, color=colors.HexColor(C_NAVY))
            note_s       = geo(10, align=0, leading=15, color=colors.HexColor("#2C3E50"),
                               space_before=6, space_after=4)

            def hr(color=C_LINE, thickness=0.5):
                return HRFlowable(width="100%", thickness=thickness,
                                  color=colors.HexColor(color), spaceAfter=8, spaceBefore=8)

            def base_table_style(hdr_bg, total_row_idx):
                return TableStyle([
                    ("FONTNAME",      (0, 0), (-1, -1), "geo"),
                    ("FONTSIZE",      (0, 0), (-1, -1), 9),
                    ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor(hdr_bg)),
                    ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
                    ("LINEBELOW",     (0, 0), (-1, -2), 0.4, colors.HexColor(C_LINE)),
                    ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor(C_LINE)),
                    ("BACKGROUND",    (0, total_row_idx), (-1, total_row_idx), colors.HexColor(C_TOTAL_BG)),
                    ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ])

            elements = []

            # სათაურის ბლოკი
            header_inner = []
            header_inner.append(Paragraph(project_name, title_s))
            header_inner.append(Paragraph("ფინანსური ანგარიშგება", subtitle_s))
            header_inner.append(Paragraph(today_str, date_s))

            hdr_tbl = Table([[header_inner]], colWidths=[PAGE_W])
            hdr_tbl.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EBF0F5")),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ]))
            elements.append(hdr_tbl)
            elements.append(Spacer(1, 20))

            # ფინანსური შეჯამება
            elements.append(Paragraph("ფინანსური შეჯამება", section_s))
            elements.append(hr())

            inc_pdf_label = " (წმინდა -20%)" if _income else ""
            sal_pdf_label = " (ხელზე ასაღები -20%)" if _salary else ""

            # ცხრილის მონაცემების აწყობა
            summary_data = [
                [Paragraph("დასახელება", cell_bold_s), Paragraph("მნიშვნელობა", cell_bold_s)],
                [Paragraph("მესაკუთრეების რაოდენობა", cell_s), Paragraph(str(total_residents), cell_right_s)],
                [Paragraph("მევალეების რაოდენობა", cell_s), Paragraph(str(debtors_count), cell_right_s)],
                [Paragraph(f"ამ თვის შემოსავალი{inc_pdf_label}", cell_s), Paragraph(f"{net_collection:.2f} GEL", cell_right_s)],
                [Paragraph("წინა თვის ნაშთი (+)", cell_s), Paragraph(f"{previous_balance:.2f} GEL", cell_right_s)],
                [Paragraph("გაწეული ხარჯი (-)", cell_s), Paragraph(f"{expenses:.2f} GEL", cell_right_s)],
            ]

            if total_manager_salary_gross > 0:
                summary_data.append([
                    Paragraph("თავმჯდომარის ხელფასი (ინფორმაციული)", cell_s), 
                    Paragraph(f"{total_manager_salary_gross:.2f} GEL", cell_right_s)
                ])
                if apply_tax_salary:
                    summary_data.append([
                        Paragraph(f"ხელფასი{sal_pdf_label}", cell_s), 
                        Paragraph(f"{manager_salary_net:.2f} GEL", cell_right_s)
                    ])

            summary_data.append([
                Paragraph("მიმდინარე თვის ნაშთი (ნეტო)", cell_bold_s),
                Paragraph(f"{final_monthly_balance:.2f} GEL", cell_right_s)
            ])

            st_table = Table(summary_data, colWidths=[PAGE_W * 0.68, PAGE_W * 0.32])
            st_table.setStyle(base_table_style(C_NAVY, -1))
            elements.append(st_table)

            # სამუშაოების აღწერა
            if work_description:
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("შესრულებული სამუშაოების დეტალები", section_s))
                elements.append(Paragraph(work_description.replace('\n', '<br/>'), note_s))

            if free_work_description:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("დამატებითი სამუშაოები (ხარჯის გარეშე)", section_s))
                elements.append(Paragraph(free_work_description.replace('\n', '<br/>'), note_s))

            elements.append(PageBreak())

            # --- მევალეების სია (მხოლოდ თუ მონიშნულია) ---
            if show_debtors_list:
                elements.append(PageBreak())
                elements.append(Paragraph("მევალეების სია", section_s))
                elements.append(hr(color=C_RED_HDR))

                d_list = [[Paragraph("მესაკუთრე", cell_bold_s), Paragraph("დავალიანება", cell_bold_s)]]
                for row in debtors_df.values.tolist():
                    d_list.append([Paragraph(str(row[0]), cell_s), Paragraph(f"{row[1]:.2f} GEL", cell_right_s)])
                
                d_list.append([Paragraph("სულ ჯამური დავალიანება:", cell_bold_s), Paragraph(f"{total_debt_sum:.2f} GEL", cell_right_s)])

                dt = Table(d_list, colWidths=[PAGE_W * 0.72, PAGE_W * 0.28], repeatRows=1)
                dt.setStyle(base_table_style(C_RED_HDR, -1))
                elements.append(dt)

            # --- ავანსების სია (მხოლოდ თუ მონიშნულია) ---
            if show_advances_list:
                elements.append(PageBreak())
                elements.append(Paragraph("ავანსების სია", section_s))
                elements.append(hr(color=C_GREEN_HDR))

                a_list = [[Paragraph("მესაკუთრე", cell_bold_s), Paragraph("ავანსი", cell_bold_s)]]
                for row in advances_df.values.tolist():
                    a_list.append([Paragraph(str(row[0]), cell_s), Paragraph(f"{row[1]:.2f} GEL", cell_right_s)])
                
                a_list.append([Paragraph("სულ ჯამური ავანსი:", cell_bold_s), Paragraph(f"{total_advance_sum:.2f} GEL", cell_right_s)])

                at = Table(a_list, colWidths=[PAGE_W * 0.72, PAGE_W * 0.28], repeatRows=1)
                at.setStyle(base_table_style(C_GREEN_HDR, -1))
                elements.append(at)

            doc.build(elements)
            st.download_button(
                f"📥 ჩამოტვირთეთ {project_name}_Report.pdf",
                buffer.getvalue(),
                f"{project_name}_Report.pdf",
                "application/pdf"
            )

    except Exception as e:
        st.error(f"შეცდომა დამუშავებისას: {e}")
