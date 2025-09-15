import fitz  # PyMuPDF - only for reading
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import io
import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

def check_dependencies():
    """Check if required packages are installed"""
    missing = []
    
    try:
        import fitz
        print("✅ PyMuPDF found")
    except ImportError:
        missing.append("PyMuPDF")
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract found: {version}")
    except Exception as e:
        missing.append("pytesseract/tesseract")
        print(f"❌ Tesseract issue: {e}")
    
    try:
        from PIL import Image
        print("✅ PIL/Pillow found")
    except ImportError:
        missing.append("Pillow")
    
    try:
        from reportlab.pdfgen import canvas
        print("✅ ReportLab found")
    except ImportError:
        missing.append("reportlab")
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        for pkg in missing:
            if pkg == "PyMuPDF":
                print("pip install PyMuPDF")
            elif pkg == "pytesseract/tesseract":
                print("pip install pytesseract")
            elif pkg == "Pillow":
                print("pip install Pillow")
            elif pkg == "reportlab":
                print("pip install reportlab")
        return False
    
    return True

def extract_text_from_page(page, dpi=300):
    """Extract text from a PDF page using OCR with improved settings"""
    try:
        # Convert page to high-quality image
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(img_data))
        
        # Improve OCR accuracy with enhanced configuration
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1 --dpi 300 -c tessedit_char_blacklist=|"</>" -c tessedit_do_invert=0'
        text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
        
        # Get word bounding boxes for better placement
        boxes = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        return text.strip(), image, boxes
    
    except Exception as e:
        print(f"Error processing page: {e}")
        return "", None, None

def create_image_with_selectable_text(original_image, ocr_text, transparency=128):
    """
    Create an image with text overlay that can be saved as PDF
    """
    try:
        # Create a copy of the original image
        img_with_text = original_image.copy().convert('RGBA')
        
        # Create transparent overlay
        overlay = Image.new('RGBA', img_with_text.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Try to use a decent font
        try:
            # Try to use a system font
            font_size = max(12, min(24, img_with_text.height // 40))
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        if ocr_text and font:
            # Split text into lines that fit the image
            words = ocr_text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if font and draw.textlength(test_line, font=font) < (img_with_text.width - 100):
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text lines
            y_pos = 50
            line_height = font_size + 5
            
            for line in lines:
                if y_pos + line_height < img_with_text.height - 50:
                    # Semi-transparent background
                    text_width = draw.textlength(line, font=font) if font else len(line) * 10
                    draw.rectangle(
                        [(50, y_pos - 2), (50 + text_width + 10, y_pos + line_height)],
                        fill=(255, 255, 255, transparency)
                    )
                    
                    # Black text
                    draw.text((55, y_pos), line, font=font, fill=(0, 0, 0, 255))
                    y_pos += line_height
                else:
                    break
        
        # Combine images
        final_image = Image.alpha_composite(img_with_text, overlay)
        return final_image.convert('RGB')
        
    except Exception as e:
        print(f"Error creating text overlay: {e}")
        return original_image.convert('RGB')

def create_pdf_with_reportlab(input_pdf_path, output_pdf_path, dpi=200, add_text_overlay=True):
    """
    Create new PDF using ReportLab - completely avoids PyMuPDF text insertion issues
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"📖 Opening: {input_pdf_path}")
        
        # Open the PDF for reading only
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Creating new PDF with ReportLab: {total_pages} pages...")
        
        # Create new PDF with ReportLab
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        successful_pages = 0
        
        for page_num in range(total_pages):
            print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
            
            try:
                page = pdf_document[page_num]
                
                # Get page dimensions
                page_width = page.rect.width
                page_height = page.rect.height
                
                # Extract text
                text, original_image = extract_text_from_page(page, dpi)
                
                if original_image:
                    # Create image with text overlay if requested
                    if add_text_overlay and text:
                        processed_image = create_image_with_selectable_text(original_image, text)
                    else:
                        processed_image = original_image.convert('RGB')
                    
                    # Save image temporarily
                    temp_image_path = f"temp_page_{page_num}.png"
                    processed_image.save(temp_image_path, "PNG")
                    
                    # Calculate scaling to fit page
                    img_width, img_height = processed_image.size
                    scale_x = letter[0] / img_width
                    scale_y = letter[1] / img_height
                    scale = min(scale_x, scale_y) * 0.95  # 95% to leave margins
                    
                    new_width = img_width * scale
                    new_height = img_height * scale
                    
                    # Center on page
                    x = (letter[0] - new_width) / 2
                    y = (letter[1] - new_height) / 2
                    
                    # Add image to PDF
                    c.drawImage(temp_image_path, x, y, width=new_width, height=new_height)
                    
                    # Clean up temp file
                    os.remove(temp_image_path)
                    
                    # Add invisible text for searchability (ReportLab method)
                    if text and not add_text_overlay:
                        c.setFillColorRGB(1, 1, 1)  # White text (invisible)
                        c.setFont("Helvetica", 1)   # Very small font
                        
                        # Split text into chunks to avoid long lines
                        words = text.split()
                        for i in range(0, len(words), 20):
                            chunk = ' '.join(words[i:i+20])
                            text_y = y + new_height - (i//20 + 1) * 10
                            if text_y > y:
                                c.drawString(x + 5, text_y, chunk[:100])  # Limit length
                    
                    successful_pages += 1
                    print("✓")
                else:
                    print("○")
                
                # Move to next page
                c.showPage()
                
            except Exception as page_error:
                print(f"✗ (Error: {str(page_error)[:30]})")
                c.showPage()  # Still create blank page
                continue
        
        # Save PDF
        c.save()
        pdf_document.close()
        
        print(f"✅ ReportLab PDF created successfully!")
        print(f"📄 Successfully processed: {successful_pages}/{total_pages} pages")
        
        # Show file sizes
        input_size = os.path.getsize(input_pdf_path) / (1024*1024)
        output_size = os.path.getsize(output_pdf_path) / (1024*1024)
        print(f"📊 Input size: {input_size:.1f} MB")
        print(f"📊 Output size: {output_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_text_only_pdf_clean(input_pdf_path, output_pdf_path, dpi=200):
    """
    Create a clean text-only PDF using ReportLab with improved formatting
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"📖 Extracting text from: {input_pdf_path}")
        
        # Open PDF for reading
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Creating clean text PDF from {total_pages} pages...")
        
        # Create new PDF
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        page_width, page_height = letter
        
        # Define margins
        left_margin = 72    # 1 inch in points
        right_margin = page_width - 72
        top_margin = page_height - 72
        bottom_margin = 72
        
        successful_pages = 0
        
        for page_num in range(total_pages):
            print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
            
            try:
                page = pdf_document[page_num]
                text, _ = extract_text_from_page(page, dpi)
                
                if text:
                    # Improved text cleaning and paragraph detection
                    paragraphs = []
                    current_para = []
                    
                    # Split into paragraphs while preserving intentional line breaks
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:  # Empty line indicates paragraph break
                            if current_para:
                                paragraphs.append(' '.join(current_para))
                                current_para = []
                        else:
                            # Check if line ends with period or other sentence endings
                            if line.endswith(('.', '!', '?', ':', ';')) or len(line) < 40:
                                current_para.append(line)
                                paragraphs.append(' '.join(current_para))
                                current_para = []
                            else:
                                current_para.append(line)
                    
                    if current_para:
                        paragraphs.append(' '.join(current_para))
                    
                    # Set up initial text formatting
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(left_margin, top_margin, f"Page {page_num + 1}")
                    
                    # Start text content below header
                    y_pos = top_margin - 30
                    
                    for paragraph in paragraphs:
                        if not paragraph.strip():
                            continue
                            
                        # Detect if paragraph might be a header
                        is_header = len(paragraph) < 60 and paragraph.isupper()
                        
                        # Set appropriate font and size
                        if is_header:
                            c.setFont("Helvetica-Bold", 12)
                            line_height = 20
                        else:
                            c.setFont("Helvetica", 11)
                            line_height = 14
                        
                        # Split paragraph into lines that fit the page width
                        words = paragraph.split()
                        lines = []
                        current_line = []
                        
                        for word in words:
                            test_line = ' '.join(current_line + [word])
                            # Use proper text width calculation
                            text_width = c.stringWidth(test_line, c._fontname, c._fontsize)
                            
                            if text_width < (right_margin - left_margin):
                                current_line.append(word)
                            else:
                                if current_line:
                                    lines.append(' '.join(current_line))
                                current_line = [word]
                        
                        if current_line:
                            lines.append(' '.join(current_line))
                        
                        # Draw paragraph
                        for line in lines:
                            if y_pos > bottom_margin:
                                c.drawString(left_margin, y_pos, line)
                                y_pos -= line_height
                            else:
                                # Start new page if we run out of space
                                c.showPage()
                                c.setFont("Helvetica-Bold", 14)
                                c.drawString(left_margin, top_margin, f"Page {page_num + 1} (continued)")
                                y_pos = top_margin - 30
                                c.setFont(c._fontname, c._fontsize)  # Restore font settings
                                
                        # Add paragraph spacing
                        y_pos -= line_height * 0.5
                    
                    successful_pages += 1
                    print("✓")
                else:
                    print("○")
                
                c.showPage()
                
            except Exception as page_error:
                print(f"✗ ({str(page_error)[:20]})")
                c.showPage()
                continue
        
        c.save()
        pdf_document.close()
        
        print(f"✅ Clean text PDF created!")
        print(f"📄 Successfully processed: {successful_pages}/{total_pages} pages")
        
        # Show file sizes
        input_size = os.path.getsize(input_pdf_path) / (1024*1024)
        output_size = os.path.getsize(output_pdf_path) / (1024*1024)
        print(f"📊 Input size: {input_size:.1f} MB")
        print(f"📊 Output size: {output_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def extract_to_text_file(input_pdf_path, output_txt_path, dpi=200):
    """
    Simple text extraction to .txt file
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"📖 Extracting text from: {input_pdf_path}")
        
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Extracting text from {total_pages} pages...")
        
        all_text = []
        successful_pages = 0
        
        for page_num in range(total_pages):
            print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
            
            try:
                page = pdf_document[page_num]
                text, _ = extract_text_from_page(page, dpi)
                
                if text:
                    all_text.append(f"\n{'='*50}")
                    all_text.append(f"PAGE {page_num + 1}")
                    all_text.append(f"{'='*50}\n")
                    all_text.append(text)
                    all_text.append("\n")
                    successful_pages += 1
                    print("✓")
                else:
                    print("○")
                    
            except Exception as page_error:
                print(f"✗")
                continue
        
        pdf_document.close()
        
        # Save text file
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_text))
        
        print(f"✅ Text file created: {output_txt_path}")
        print(f"📄 Successfully extracted: {successful_pages}/{total_pages} pages")
        
        # Show file size
        output_size = os.path.getsize(output_txt_path) / 1024
        print(f"📊 Text file size: {output_size:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_editable_pdf(input_pdf_path, output_pdf_path, dpi=300):
    """Create a fully editable PDF with properly embedded text"""
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"� Processing: {input_pdf_path}")
        
        # Open the PDF for reading
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Creating editable PDF with {total_pages} pages...")
        
        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Process each page
            page_paths = []
            successful_pages = 0
            
            for page_num in range(total_pages):
                print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
                
                try:
                    page = pdf_document[page_num]
                    
                    # Extract text and get word positions
                    text, image, boxes = extract_text_from_page(page, dpi)
                    
                    if text and image and boxes:
                        # Create new PDF page with reportlab
                        temp_pdf = os.path.join(temp_dir, f"page_{page_num}.pdf")
                        page_width = image.width * 72.0 / dpi
                        page_height = image.height * 72.0 / dpi
                        
                        c = canvas.Canvas(temp_pdf, pagesize=(page_width, page_height))
                        
                        # Add background image
                        temp_img = os.path.join(temp_dir, f"page_{page_num}.png")
                        image.save(temp_img, "PNG")
                        c.drawImage(temp_img, 0, 0, width=page_width, height=page_height)
                        
                        # Add text layer with precise positioning
                        c.setFont("Helvetica", 10)
                        
                        # Process words with their positions
                        for i in range(len(boxes['text'])):
                            if boxes['conf'][i] > 0:  # Skip low confidence or empty text
                                word = boxes['text'][i].strip()
                                if word:
                                    # Convert coordinates to PDF space
                                    x = boxes['left'][i] * 72.0 / dpi
                                    # Convert y-coordinate (PDF coordinates start from bottom)
                                    y = page_height - (boxes['top'][i] + boxes['height'][i]) * 72.0 / dpi
                                    
                                    # Calculate font size based on the height of the word box
                                    font_size = boxes['height'][i] * 72.0 / dpi
                                    # Keep font size within reasonable bounds
                                    font_size = max(min(font_size, 14), 8)
                                    
                                    # Set font and size
                                    c.setFont("Helvetica", font_size)
                                    
                                    # Add small spacing between words
                                    word_width = c.stringWidth(word, "Helvetica", font_size)
                                    space_width = c.stringWidth(" ", "Helvetica", font_size)
                                    
                                    # Check if this is a new line by comparing y-coordinates with previous word
                                    if i > 0:
                                        prev_y = page_height - (boxes['top'][i-1] + boxes['height'][i-1]) * 72.0 / dpi
                                        if abs(y - prev_y) < font_size/2:  # Same line
                                            # Add space only if words are not too far apart
                                            prev_x = boxes['left'][i-1] * 72.0 / dpi
                                            prev_width = boxes['width'][i-1] * 72.0 / dpi
                                            if (x - (prev_x + prev_width)) < space_width * 3:
                                                x += space_width
                                    
                                    # Make text selectable and editable with improved spacing
                                    c.setFillColorRGB(0, 0, 0, 1)  # Black text
                                    c.drawString(x, y, word)
                        
                        c.save()
                        page_paths.append(temp_pdf)
                        successful_pages += 1
                        print("✓")
                    else:
                        print("○")
                
                except Exception as e:
                    print(f"✗ ({str(e)[:30]})")
                    continue
            
            # Merge all pages into final PDF
            if successful_pages > 0:
                output_doc = fitz.open()
                
                for page_path in page_paths:
                    try:
                        temp_doc = fitz.open(page_path)
                        output_doc.insert_pdf(temp_doc)
                        temp_doc.close()
                    except Exception as e:
                        print(f"\nWarning: Could not process temporary file {page_path}: {e}")
                        continue
                
                try:
                    # Save with optimization for editability
                    output_doc.save(output_pdf_path,
                                  deflate=True,
                                  clean=True,
                                  ascii=False,
                                  pretty=False)
                except Exception as e:
                    print(f"\n❌ Error saving final PDF: {e}")
                    return False
                finally:
                    output_doc.close()
                
                print(f"\n✅ Created editable PDF successfully!")
                print(f"📄 Processed {successful_pages}/{total_pages} pages")
                
                # Show file sizes
                input_size = os.path.getsize(input_pdf_path) / (1024*1024)
                output_size = os.path.getsize(output_pdf_path) / (1024*1024)
                print(f"📊 Input size: {input_size:.1f} MB")
                print(f"📊 Output size: {output_size:.1f} MB")
                
                return True
            
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'pdf_document' in locals():
            pdf_document.close()

if __name__ == "__main__":
    print("📝 Enhanced PDF Converter (Creates Editable PDFs)")
    print("=" * 55)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first.")
        sys.exit(1)
    
    # Get PDF files
    current_dir = os.getcwd()
    print(f"\nCurrent directory: {current_dir}")
    
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf') 
                 and not f.startswith(('editable_', 'searchable_', 'overlay_'))]
    
    if not pdf_files:
        print("❌ No PDF files found")
        input_path = input("\nEnter path to PDF: ").strip().strip('"')
        if input_path and os.path.exists(input_path):
            selected_file = input_path
        else:
            print("❌ File not found")
            sys.exit(1)
    else:
        print(f"\nFound {len(pdf_files)} PDF file(s):")
        for i, pdf in enumerate(pdf_files, 1):
            size_mb = os.path.getsize(pdf) / (1024*1024)
            print(f"  {i}. {pdf} ({size_mb:.1f} MB)")
        
        if len(pdf_files) == 1:
            selected_file = pdf_files[0]
        else:
            choice = int(input(f"\nSelect PDF (1-{len(pdf_files)}): ")) - 1
            selected_file = pdf_files[choice]
    
    print(f"\n📄 Selected: {os.path.basename(selected_file)}")
    
    # Quality settings
    quality = input("\nUse high quality processing? (y/n): ").strip().lower()
    dpi = 300 if quality in ['y', 'yes'] else 200
    
    base_name = os.path.splitext(os.path.basename(selected_file))[0]
    output_file = f"editable_{base_name}.pdf"
    
    print(f"\n🚀 Creating editable PDF...")
    print(f"Input: {selected_file}")
    print(f"Output: {output_file}")
    print(f"Quality: {dpi} DPI")
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm in ['y', 'yes', '']:
        success = create_editable_pdf(selected_file, output_file, dpi)
        if success:
            print(f"\n🎉 Successfully created editable PDF: {output_file}")
    
    input("\nPress Enter to exit...")