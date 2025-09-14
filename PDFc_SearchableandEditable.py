import fitz  # PyMuPDF - only for reading
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import io
import os
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

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

def extract_text_from_page(page, dpi=200):
    """Extract text from a PDF page using OCR"""
    try:
        # Convert page to image
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image and perform OCR
        image = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(image, config='--psm 6')
        
        return text.strip(), image
    
    except Exception as e:
        print(f"Error processing page: {e}")
        return "", None

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

if __name__ == "__main__":
    
    print("🛠️ Alternative PDF Converter (Avoids PyMuPDF Issues)")
    print("=" * 55)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first:")
        print("pip install PyMuPDF pytesseract Pillow reportlab")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Get PDF files
    current_dir = os.getcwd()
    print(f"\nCurrent directory: {current_dir}")
    
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf') and not f.startswith(('selectable_', 'editable_', 'robust_'))]
    
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
    
    # Choose method
    print(f"\n🔧 Choose method (No PyMuPDF text insertion issues):")
    print("1. PDF with visible text overlay (selectable)")
    print("2. PDF with invisible text layer (searchable)")
    print("3. Clean text-only PDF (editable)")
    print("4. Extract to text file (.txt)")
    
    try:
        method = int(input("\nSelect method (1-4): "))
        
        # Quality setting
        quality = input("\nHigh quality OCR? (y/n): ").strip().lower()
        dpi = 300 if quality in ['y', 'yes'] else 200
        
        base_name = os.path.splitext(os.path.basename(selected_file))[0]
        
        print(f"\n🚀 Starting conversion (DPI={dpi})...")
        print("This method avoids PyMuPDF text insertion completely!")
        
        confirm = input("\nProceed? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '']:
            sys.exit(0)
        
        success = False
        
        if method == 1:
            output_file = f"overlay_{base_name}.pdf"
            success = create_pdf_with_reportlab(selected_file, output_file, dpi, add_text_overlay=True)
            
        elif method == 2:
            output_file = f"searchable_{base_name}.pdf"
            success = create_pdf_with_reportlab(selected_file, output_file, dpi, add_text_overlay=False)
            
        elif method == 3:
            output_file = f"clean_text_{base_name}.pdf"
            success = create_text_only_pdf_clean(selected_file, output_file, dpi)
            
        elif method == 4:
            output_file = f"extracted_{base_name}.txt"
            success = extract_to_text_file(selected_file, output_file, dpi)
        
        if success:
            print(f"\n🎉 Success! Output: {output_file}")
            print("\n💡 This method completely avoids PyMuPDF text insertion issues!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    input("\nPress Enter to exit...")