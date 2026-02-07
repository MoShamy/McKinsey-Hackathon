import copy
from io import BytesIO
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import PP_ALIGN

# --- COLORS ---
# If no template is provided, we use this "Dark Mode" Theme
DARK_BG = RGBColor(20, 25, 40)      # Deep Navy/Black
DARK_TITLE = RGBColor(255, 255, 255) # White
DARK_TEXT = RGBColor(200, 200, 200)  # Light Grey

def hex_to_rgb(hex_color):
    """Safely converts hex string to RGB tuple. Defaults to White if invalid."""
    if not hex_color or not isinstance(hex_color, str) or not hex_color.startswith('#'):
        return (255, 255, 255)
    try:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except:
        return (255, 255, 255)

def safe_wipe_slides(prs):
    """
    Attempts to delete old slides. 
    CRITICAL: If the template is fragile/protected, this catches the error 
    and STOPS deleting to prevent the 'Repair' crash.
    """
    try:
        xml_slides = prs.slides._sldIdLst
        slides = list(xml_slides)
        # Delete from back to front
        for i in range(len(slides) - 1, -1, -1):
            xml_slides.remove(slides[i])
    except Exception as e:
        print(f"Template is protected. Stopping deletion to prevent corruption. Error: {e}")
        # We proceed without deleting remaining slides to ensure file opens.

def apply_dark_theme(slide):
    """Manually paints the background Dark Navy (for non-template mode)."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = DARK_BG

def generate_pptx(json_data, template_file=None):
    # 1. SETUP
    using_template = False
    if template_file:
        try:
            prs = Presentation(template_file)
            safe_wipe_slides(prs) # Try to clear old slides
            using_template = True
        except Exception:
            # Fallback if file is unreadable
            prs = Presentation()
    else:
        prs = Presentation()

    # 2. DESIGN SETTINGS
    design = json_data.get("design", {})
    font_family = design.get("font_family", "Arial")
    
    # If using a template, respect its colors. If not, force Dark Mode colors.
    if using_template:
        t_rgb = hex_to_rgb(design.get("title_color", "#000000"))
        title_color = RGBColor(*t_rgb)
        body_color = RGBColor(0, 0, 0) # Standard black for templates
    else:
        title_color = DARK_TITLE
        body_color = DARK_TEXT

    # 3. BUILD SLIDES
    slides_data = json_data.get("slides", [])
    
    for slide_info in slides_data:
        # --- A. LAYOUT SELECTION ---
        if using_template:
            # Hunt for a layout with a body text box
            layout = prs.slide_layouts[0] 
            for l in prs.slide_layouts:
                # 1 is usually "Title and Content"
                if l.name == "Title and Content" or l.name == "Content with Caption":
                    layout = l
                    break
            slide = prs.slides.add_slide(layout)
        else:
            # Blank layout for custom Dark Mode
            slide = prs.slides.add_slide(prs.slide_layouts[6]) 
            apply_dark_theme(slide)

        # --- B. TITLE ---
        # If the layout has a title, use it. If not, DRAW it.
        if slide.shapes.title:
            tf_title = slide.shapes.title.text_frame
        else:
            # Draw Title Box: Top Center
            box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
            tf_title = box.text_frame

        tf_title.text = slide_info.get("title", "Untitled")
        
        # Style Title
        for p in tf_title.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for run in p.runs:
                run.font.name = font_family
                run.font.size = Pt(36)
                run.font.bold = True
                run.font.color.rgb = title_color

        # --- C. BODY TEXT (The "Fix") ---
        tf_body = None
        
        # 1. Check if the layout gave us a placeholder
        for shape in slide.placeholders:
            if shape.placeholder_format.type == PP_PLACEHOLDER.BODY:
                if hasattr(shape, "text_frame"):
                    tf_body = shape.text_frame
                    break
        
        # 2. NUCLEAR OPTION: If no placeholder found, DRAW A TEXT BOX.
        if tf_body is None:
            # Draw Box: Left, Top, Width, Height
            textbox = slide.shapes.add_textbox(Inches(0.5), Inches(1.8), Inches(9.0), Inches(5.0))
            tf_body = textbox.text_frame
            tf_body.word_wrap = True

        # Write Content
        tf_body.clear()
        for point in slide_info.get("bullets", []):
            p = tf_body.add_paragraph()
            p.text = point
            p.level = 0
            p.space_after = Pt(14) # Nice spacing
            
            for run in p.runs:
                run.font.name = font_family
                run.font.size = Pt(18)
                run.font.color.rgb = body_color

        # --- D. NOTES ---
        if slide.has_notes_slide:
            slide.notes_slide.notes_text_frame.text = slide_info.get("speaker_notes", "")

    # 4. EXPORT
    pptx_stream = BytesIO()
    prs.save(pptx_stream)
    pptx_stream.seek(0)
    return pptx_stream