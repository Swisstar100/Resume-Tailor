import pdfkit, markdown, os
from django.conf import settings

config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
def resume_to_pdf(html_body, output_filename):
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: Arial, sans-serif;
            font-size: 10.5pt;
            color: #000;
            margin: 36px 48px;
            line-height: 1.45;
        }}

        /* Header */
        .resume-header {{ text-align: center; margin-bottom: 14px; }}
        .resume-header h1 {{
            font-size: 22pt;
            font-weight: bold;
            color: #1a5276;
        }}
        .contact {{
            font-size: 9.5pt;
            color: #555;
            margin-top: 3px;
        }}

        /* Section headings */
        h2 {{
            font-size: 12pt;
            font-weight: bold;
            color: #1a5276;
            border-bottom: 1.5px solid #1a5276;
            padding-bottom: 2px;
            margin-top: 14px;
            margin-bottom: 6px;
            text-transform: capitalize;
        }}

        /* Entry block */
        .entry {{ margin-bottom: 8px; }}
        .entry-header {{
            display: table;
            width: 100%;
        }}
        .entry-title {{
            display: table-cell;
            font-weight: bold;
            text-align: left;
        }}
        .entry-date {{
            display: table-cell;
            font-style: italic;
            color: #555;
            font-size: 9.5pt;
            text-align: right;
            white-space: nowrap;
            width: 140px;
        }}

        /* Tech stack / subtitle */
        .entry-sub {{
            font-size: 9.5pt;
            color: #555;
            margin-bottom: 3px;
        }}
        .tech {{
            color: #1a5276;
            font-size: 9.5pt;
        }}

        /* Bullets */
        ul {{
            margin-left: 18px;
            margin-top: 3px;
        }}
        li {{
            margin-bottom: 2px;
            font-size: 10pt;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>"""

    options = {
        'encoding': 'UTF-8',
        'page-size': 'Letter',
        'margin-top': '0.4in',
        'margin-bottom': '0.4in',
        'margin-left': '0.5in',
        'margin-right': '0.5in',
        'enable-local-file-access': ''
    }

    output_path = os.path.join(settings.MEDIA_ROOT, output_filename)
    pdfkit.from_string(styled_html, output_path, options=options, configuration=config)
    return output_path