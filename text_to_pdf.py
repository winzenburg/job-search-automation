import os
import markdown
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from bs4 import BeautifulSoup

def create_resume_pdf(text_content, output_path):
    """
    Converts a plain text or markdown resume into a polished PDF.
    """
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        spaceAfter=12,
        textColor=HexColor('#2c3e50')
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=HexColor('#34495e')
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        leftIndent=15,
        spaceAfter=4,
        bulletIndent=5
    )

    story = []
    
    # If the text has markdown-like bolding or headers, process basic markdown
    html = markdown.markdown(text_content)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Process elements
    for el in soup.contents:
        if el.name is None:
            continue
            
        if el.name in ['h1', 'h2']:
            if el.name == 'h1':
                story.append(Paragraph(el.get_text(), title_style))
            else:
                story.append(Paragraph(el.get_text(), h1_style))
                story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#bdc3c7'), spaceAfter=10))
        elif el.name == 'p':
            # Handle inline bold tags (b/strong)
            text = str(el).replace('<p>', '').replace('</p>', '').replace('<strong>', '<b>').replace('</strong>', '</b>')
            story.append(Paragraph(text, body_style))
        elif el.name == 'ul':
            for li in el.find_all('li'):
                text = str(li).replace('<li>', '').replace('</li>', '').replace('<strong>', '<b>').replace('</strong>', '</b>')
                story.append(Paragraph("• " + text, bullet_style))
                
    doc.build(story)
    
    return output_path

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        with open(sys.argv[1], 'r') as f:
            content = f.read()
        create_resume_pdf(content, sys.argv[2])
        print(f"Created PDF at {sys.argv[2]}")
