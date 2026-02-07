import json
from pptx import Presentation

def generate_pptx(json_data, filename="Strategy_Deck.pptx"):
    prs = Presentation()
    
    # Extract slides from the JSON
    slides_data = json_data.get("slides", [])
    
    for slide_info in slides_data:
        # Use a blank layout (Layout Index 1 is usually Title + Content)
        slide_layout = prs.slide_layouts[1] 
        slide = prs.slides.add_slide(slide_layout)
        
        # 1. Set Title
        title = slide.shapes.title
        title.text = slide_info.get("title", "Untitled Slide")
        
        # 2. Add Bullet Points
        if slide.placeholders.placeholders:
            body_shape = slide.placeholders[1]
            tf = body_shape.text_frame
            tf.text = "" # clear default text
            
            for point in slide_info.get("bullets", []):
                p = tf.add_paragraph()
                p.text = point
                p.level = 0
        
        # 3. Add Speaker Notes
        if slide.has_notes_slide:
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_info.get("speaker_notes", "")

    prs.save(filename)
    print(f"\n✅ PowerPoint Saved: {filename}")