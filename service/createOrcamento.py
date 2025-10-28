from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.utils import ImageReader
from io import BytesIO
from decimal import Decimal
from datetime import date
import gzip


def _fmt_money(v) -> str:
    """Formata número/Decimal em padrão brasileiro: 1234.5 -> '1.234,50'."""
    if isinstance(v, Decimal):
        v = float(v)
    if v is None:
        v = 0.0
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _get_logo_image(companie_obj):
    """
    Reconstrói o logo salvo em companie_obj.imagem_bloob (gzip + binário),
    devolve um ImageReader ou None.
    """
    raw_gz = getattr(companie_obj, "imagem_bloob", None)
    if not raw_gz:
        return None
    try:
        raw = gzip.decompress(raw_gz)
        return ImageReader(BytesIO(raw))
    except Exception:
        return None

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.utils import ImageReader
from io import BytesIO
from decimal import Decimal
from datetime import date
import gzip


def _fmt_money(v) -> str:
    """
    Formata número ou Decimal no formato brasileiro: 1234.5 -> '1.234,50'
    """
    if isinstance(v, Decimal):
        v = float(v)
    if v is None:
        v = 0.0
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _get_logo_image(companie_obj):
    """
    Tenta reconstruir o logo salvo na empresa.
    Espera que companie_obj.imagem_bloob seja gzip de bytes crus da imagem.
    Retorna ImageReader ou None se não der pra montar.
    """
    raw_gz = getattr(companie_obj, "imagem_bloob", None)
    if not raw_gz:
        return None
    try:
        raw = gzip.decompress(raw_gz)
        return ImageReader(BytesIO(raw))
    except Exception:
        return None


def gerar_pdf_orcamento_venda_reportlab(
    companie_obj,
    venda_obj,
    validade_orcamento="7 dias",
    observacoes_finais="Obrigado pela preferência.",
):
    """
    Gera e retorna (bytes) um PDF de orçamento referente a uma venda.
    companie_obj  -> objeto da empresa (tabela companie)
    venda_obj     -> objeto venda (com cliente, veiculo, itens)
    """

    # ==========================
    # 1. Coleta de dados
    # ==========================

    empresa_nome = getattr(companie_obj, "nome", "") or ""
    empresa_cnpj = getattr(companie_obj, "cnpj", "") or "-"
    empresa_end = getattr(companie_obj, "endereco", "") or "-"
    empresa_num = getattr(companie_obj, "numero", "") or "-"

    numero_orcamento = venda_obj.id_venda
    data_emissao = (
        venda_obj.created_at.date().strftime("%d/%m/%Y")
        if getattr(venda_obj, "created_at", None)
        else date.today().strftime("%d/%m/%Y")
    )
    status_venda = getattr(venda_obj, "status", "") or ""
    forma_pagamento = getattr(venda_obj, "pagamento", "") or ""
    desc_venda = getattr(venda_obj, "descricao", "") or "-"

    cli = getattr(venda_obj, "cliente", None)
    cli_nome = cli.nome if cli and getattr(cli, "nome", None) else ""
    cli_doc = cli.cpf if cli and getattr(cli, "cpf", None) else ""
    cli_tel = cli.numero if cli and getattr(cli, "numero", None) else ""

    veic = getattr(venda_obj, "veiculo", None)
    veic_placa = getattr(veic, "placa", "") if veic else ""

    # itens e totais
    subtotal_bruto = Decimal("0")
    desconto_total = Decimal("0")
    linhas_itens = []

    for item in venda_obj.itens:
        desc_item = item.descricao or ""
        preco_unit = Decimal(str(item.preco_unit or 0))
        qtd = int(item.quantidade or 0)
        desc_desconto = Decimal(str(item.desconto or 0))
        linha_total = (preco_unit * qtd) - desc_desconto

        subtotal_bruto += (preco_unit * qtd)
        desconto_total += desc_desconto

        linhas_itens.append([
            desc_item,
            str(qtd),
            f"R$ {_fmt_money(preco_unit)}",
            f"R$ {_fmt_money(desc_desconto)}",
            f"R$ {_fmt_money(linha_total)}",
        ])

    total_final = venda_obj.total or 0

    # ==========================
    # 2. Setup de PDF
    # ==========================

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Margens
    margin_left = 20 * mm
    margin_right = 20 * mm
    max_width = largura - margin_left - margin_right
    cursor_y = altura - 20 * mm

    # ==========================
    # 3. Estilos de texto
    # ==========================

    style_normal = ParagraphStyle(
        name="Normal",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    style_bold = ParagraphStyle(
        name="Bold",
        parent=style_normal,
        fontName="Helvetica-Bold",
    )

    style_section_title = ParagraphStyle(
        name="SectionTitle",
        parent=style_normal,
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#2563eb"),
    )

    style_right = ParagraphStyle(
        name="Right",
        parent=style_normal,
        alignment=TA_RIGHT,
    )

    style_total_label = ParagraphStyle(
        name="TotalLabel",
        parent=style_normal,
        alignment=TA_RIGHT,
        textColor=colors.black,
        fontName="Helvetica",
    )

    style_total_value = ParagraphStyle(
        name="TotalValue",
        parent=style_normal,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#2563eb"),
        fontName="Helvetica-Bold",
        fontSize=11,
    )

    style_sign = ParagraphStyle(
        name="Sign",
        parent=style_normal,
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
    )

    # ==========================
    # 4. Cabeçalho (logo + dados empresa + meta do orçamento)
    # ==========================

    logo_img = _get_logo_image(companie_obj)

    left_x = margin_left
    right_x = largura - margin_right

    # Logo (22mm x 22mm) + dados da empresa
    if logo_img:
        c.drawImage(
            logo_img,
            left_x,
            cursor_y - 20 * mm,
            width=22 * mm,
            height=22 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_block_x = left_x + 24 * mm
    else:
        text_block_x = left_x

    c.setFont("Helvetica-Bold", 10)
    c.drawString(text_block_x, cursor_y - 6, empresa_nome)

    c.setFont("Helvetica", 8)
    c.drawString(text_block_x, cursor_y - 18, f"CNPJ: {empresa_cnpj}")
    c.drawString(text_block_x, cursor_y - 28, f"{empresa_end}, Nº {empresa_num}")

    # bloco meta do orçamento, alinhado à direita
    meta_lines = [
        f"ORÇAMENTO Nº {numero_orcamento:04d}",
        f"Data: {data_emissao}",
        f"Validade: {validade_orcamento}",
        f"Status: {status_venda}",
        f"Pagamento: {forma_pagamento}",
    ]
    c.setFont("Helvetica", 8)
    text_w = max(c.stringWidth(l, "Helvetica", 8) for l in meta_lines)
    meta_x = right_x - text_w
    ty = cursor_y - 6
    for l in meta_lines:
        c.drawString(meta_x, ty, l)
        ty -= 10

    # desce cursor depois do header
    cursor_y -= 30 * mm

    # linha separadora azul
    c.setStrokeColor(colors.HexColor("#2563eb"))
    c.setLineWidth(1)
    c.line(margin_left, cursor_y, right_x, cursor_y)
    cursor_y -= 8

    # ==========================
    # 5. Dados do Cliente
    # ==========================

    p_title = Paragraph("Dados do Cliente", style_section_title)
    w, h = p_title.wrapOn(c, max_width, 100)
    p_title.drawOn(c, margin_left, cursor_y - h)
    cursor_y -= (h + 4)

    cliente_text = (
        f"<b>Cliente:</b> {cli_nome}<br/>"
        f"<b>CPF:</b> {cli_doc}<br/>"
        f"<b>Telefone:</b> {cli_tel}<br/>"
        f"<b>Veículo / Placa:</b> {veic_placa}<br/>"
        f"<b>Observação / Descrição:</b> {desc_venda}"
    )
    p_cli = Paragraph(cliente_text, style_normal)
    w, h = p_cli.wrapOn(c, max_width, 200)
    p_cli.drawOn(c, margin_left, cursor_y - h)
    cursor_y -= (h + 12)

    # ==========================
    # 6. Itens do Orçamento
    # ==========================

    p_itens_title = Paragraph("Itens do Orçamento", style_section_title)
    w, h = p_itens_title.wrapOn(c, max_width, 100)

    # quebra de página se faltar espaço antes da tabela
    if cursor_y - h < 60 * mm:
        c.showPage()
        cursor_y = altura - 20 * mm

    p_itens_title.drawOn(c, margin_left, cursor_y - h)
    cursor_y -= (h + 4)

    # tabela com os itens
    table_data = [
        ["Descrição", "Qtd", "Unitário (R$)", "Desc (R$)", "Subtotal (R$)"]
    ] + linhas_itens

    col_widths = [
        max_width * 0.40,
        max_width * 0.10,
        max_width * 0.15,
        max_width * 0.15,
        max_width * 0.20,
    ]

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f9fafb")),

        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),

        ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor("#d1d5db")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#d1d5db")),
    ]))

    tw, th = tbl.wrapOn(c, max_width, cursor_y - 30 * mm)

    # se a tabela não couber
    if cursor_y - th < 60 * mm:
        c.showPage()
        cursor_y = altura - 20 * mm

    tbl.drawOn(c, margin_left, cursor_y - th)
    cursor_y -= (th + 16)

    # ==========================
    # 7. Totais (sem moldura)
    # ==========================

    # garante espaço para os totais
    if cursor_y < 70 * mm:
        c.showPage()
        cursor_y = altura - 20 * mm

    totais_rows = [
        [
            Paragraph("Subtotal bruto:", style_total_label),
            Paragraph(f"R$ {_fmt_money(subtotal_bruto)}", style_right),
        ],
        [
            Paragraph("Descontos aplicados:", style_total_label),
            Paragraph(f"R$ {_fmt_money(desconto_total)}", style_right),
        ],
        [
            Paragraph("<b>Total:</b>", style_total_label),
            Paragraph(f"<b>R$ {_fmt_money(total_final)}</b>", style_total_value),
        ],
    ]

    totais_tbl = Table(
        totais_rows,
        colWidths=[max_width * 0.35, max_width * 0.20],
        hAlign='RIGHT'
    )

    totais_tbl.setStyle(TableStyle([
        # linhas normais
        ('FONT', (0,0), (-1,-2), 'Helvetica', 9),
        ('TEXTCOLOR', (0,0), (-1,-2), colors.black),

        # última linha (Total) em destaque
        ('FONT', (0,-1), (-1,-1), 'Helvetica-Bold', 10),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor("#2563eb")),

        # alinhar à direita
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),

        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING',    (0,0), (-1,-1), 4),

        # sem bordas
        ('BOX', (0,0), (-1,-1), 0, colors.white),
        ('INNERGRID', (0,0), (-1,-1), 0, colors.white),
    ]))

    tw_tot, th_tot = totais_tbl.wrapOn(c, max_width, 9999)

    # desenhar a tabela de totais "colada" à direita
    totais_x = margin_left + max_width - tw_tot
    totais_y_top = cursor_y
    totais_tbl.drawOn(c, totais_x, totais_y_top - th_tot)

    cursor_y = (totais_y_top - th_tot) - 20

    # ==========================
    # 8. Observações
    # ==========================

    if cursor_y < 60 * mm:
        c.showPage()
        cursor_y = altura - 20 * mm

    obs_title = Paragraph("Observações", style_section_title)
    w, h = obs_title.wrapOn(c, max_width, 100)
    obs_title.drawOn(c, margin_left, cursor_y - h)
    cursor_y -= (h + 6)

    obs_text = (
        f"<b>Validade do orçamento:</b> {validade_orcamento}. "
        "Valores sujeitos a alteração após esse prazo.<br/><br/>"
        f"{observacoes_finais}"
    )
    p_obs = Paragraph(obs_text, style_normal)
    w, h = p_obs.wrapOn(c, max_width, 200)
    p_obs.drawOn(c, margin_left, cursor_y - h)
    cursor_y -= (h + 30)

    # ==========================
    # 9. Assinaturas
    # ==========================

    minimo_assinatura = 40 * mm
    if cursor_y < minimo_assinatura:
        c.showPage()
        cursor_y = altura - 20 * mm

    linha_y = cursor_y - 20 * mm

    col_gap = 10 * mm
    col_width = (max_width - col_gap) / 2.0

    linha_esq_x1 = margin_left
    linha_esq_x2 = margin_left + col_width
    linha_dir_x1 = linha_esq_x2 + col_gap
    linha_dir_x2 = linha_dir_x1 + col_width

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(linha_esq_x1, linha_y, linha_esq_x2, linha_y)
    c.line(linha_dir_x1, linha_y, linha_dir_x2, linha_y)

    empresa_label = f"{empresa_nome}  -  CNPJ: {empresa_cnpj}"
    cliente_label = f"{cli_nome}  -  {cli_doc}"

    p_emp = Paragraph(empresa_label, style_sign)
    p_cli = Paragraph(cliente_label, style_sign)

    ew, eh = p_emp.wrapOn(c, col_width, 30)
    cw, ch = p_cli.wrapOn(c, col_width, 30)

    p_emp.drawOn(
        c,
        linha_esq_x1 + (col_width - ew) / 2,
        linha_y - eh - 4
    )

    p_cli.drawOn(
        c,
        linha_dir_x1 + (col_width - cw) / 2,
        linha_y - ch - 4
    )

    # ==========================
    # 10. Finaliza
    # ==========================

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
