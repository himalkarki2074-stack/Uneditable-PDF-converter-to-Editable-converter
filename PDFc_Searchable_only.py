import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
import sys

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
        # Test if tesseract executable is accessible
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
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        for pkg in missing:
            if pkg == "PyMuPDF":
                print("pip install PyMuPDF")
            elif pkg == "pytesseract/tesseract":
                print("pip install pytesseract")
                print("Also install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
            elif pkg == "Pillow":
                print("pip install Pillow")
        return False
    
    return True

def extract_text_from_page(page, dpi=200):
    """Extract text from a PDF page using OCR"""
    try:
        # Convert page to image with specified DPI
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(img_data))
        
        # Perform OCR
        text = pytesseract.image_to_string(image, config='--psm 6')
        
        return text.strip()
    
    except Exception as e:
        print(f"Error processing page: {e}")
        return ""

def create_searchable_pdf(input_pdf_path, output_pdf_path, dpi=200):
    """
    Create a searchable PDF by adding invisible text layer
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"📖 Opening: {input_pdf_path}")
        
        # Open the PDF
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Processing {total_pages} pages with OCR...")
        print(f"🔧 Using DPI: {dpi} (higher = better quality, slower processing)")
        
        # Process each page
        for page_num in range(total_pages):
            print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
            
            page = pdf_document[page_num]
            
            # Extract text using OCR
            text = extract_text_from_page(page, dpi)
            
            if text:
                # Add invisible text layer for searchability
                # Insert text in very small font size and white color (invisible)
                text_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                
                # Clean up text for PDF insertion
                clean_text = text.replace('\n\n', '\n').strip()
                
                if clean_text:
                    try:
                        page.insert_textbox(
                            text_rect,
                            clean_text,
                            fontsize=1,  # Very small
                            color=(1, 1, 1),  # White (invisible)
                            overlay=False  # Behind existing content
                        )
                        print("✓", end="")
                    except:
                        print("⚠", end="")  # Warning if text insertion fails
                else:
                    print("-", end="")  # No text found
            else:
                print("○", end="")  # Empty page
            
            print()  # New line after each page
        
        # Save the modified PDF
        print(f"💾 Saving searchable PDF...")
        pdf_document.save(output_pdf_path, garbage=4, deflate=True)
        pdf_document.close()
        
        print(f"✅ Success! Searchable PDF created: {output_pdf_path}")
        
        # Show file sizes
        input_size = os.path.getsize(input_pdf_path) / (1024*1024)
        output_size = os.path.getsize(output_pdf_path) / (1024*1024)
        print(f"📊 Input size: {input_size:.1f} MB")
        print(f"📊 Output size: {output_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def extract_text_only(input_pdf_path, output_txt_path, dpi=200):
    """
    Extract all text to a .txt file (useful for very large PDFs)
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        print(f"📖 Opening: {input_pdf_path}")
        
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Extracting text from {total_pages} pages...")
        
        all_text = []
        
        for page_num in range(total_pages):
            print(f"📝 Page {page_num + 1}/{total_pages}...", end=" ", flush=True)
            
            page = pdf_document[page_num]
            text = extract_text_from_page(page, dpi)
            
            if text:
                all_text.append(f"\n--- Page {page_num + 1} ---\n")
                all_text.append(text)
                all_text.append("\n")
                print("✓")
            else:
                print("○")
        
        pdf_document.close()
        
        # Save all text to file
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_text))
        
        print(f"✅ Text extracted to: {output_txt_path}")
        
        # Show file size
        output_size = os.path.getsize(output_txt_path) / 1024  # KB
        print(f"📊 Text file size: {output_size:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def process_in_chunks(input_pdf_path, output_folder, pages_per_chunk=50):
    """
    Process large PDF in smaller chunks to avoid memory issues
    """
    
    if not os.path.exists(input_pdf_path):
        print(f"❌ Input file not found: {input_pdf_path}")
        return False
    
    try:
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        print(f"📖 Opening: {input_pdf_path}")
        pdf_document = fitz.open(input_pdf_path)
        total_pages = len(pdf_document)
        
        print(f"📄 Processing {total_pages} pages in chunks of {pages_per_chunk}")
        
        chunks_processed = 0
        
        for start_page in range(0, total_pages, pages_per_chunk):
            end_page = min(start_page + pages_per_chunk, total_pages)
            chunk_num = chunks_processed + 1
            
            print(f"\n🔄 Processing chunk {chunk_num}: pages {start_page + 1}-{end_page}")
            
            # Create chunk PDF
            chunk_pdf = fitz.open()
            chunk_pdf.insert_pdf(pdf_document, from_page=start_page, to_page=end_page - 1)
            
            # Save and process chunk
            chunk_path = os.path.join(output_folder, f"chunk_{chunk_num:03d}.pdf")
            chunk_pdf.save(chunk_path)
            
            # Process chunk with OCR
            output_chunk_path = os.path.join(output_folder, f"searchable_chunk_{chunk_num:03d}.pdf")
            success = create_searchable_pdf(chunk_path, output_chunk_path)
            
            chunk_pdf.close()
            
            if success:
                # Remove original chunk to save space
                os.remove(chunk_path)
                chunks_processed += 1
                print(f"✅ Chunk {chunk_num} completed")
            else:
                print(f"❌ Chunk {chunk_num} failed")
        
        pdf_document.close()
        
        print(f"\n🏁 Processing complete!")
        print(f"✅ Processed {chunks_processed} chunks")
        print(f"📁 Output folder: {output_folder}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    
    print("🔍 Python-Only PDF OCR Converter")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first.")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Get current directory and list PDF files
    current_dir = os.getcwd()
    print(f"\nCurrent directory: {current_dir}")
    
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("❌ No PDF files found in current directory")
        input_path = input("\nEnter full path to PDF file: ").strip().strip('"')
        if input_path and os.path.exists(input_path):
            pdf_files = [input_path]
        else:
            print("❌ File not found")
            input("Press Enter to exit...")
            sys.exit(1)
    else:
        print(f"\nFound {len(pdf_files)} PDF file(s):")
        for i, pdf in enumerate(pdf_files, 1):
            size_mb = os.path.getsize(pdf) / (1024*1024)
            print(f"  {i}. {pdf} ({size_mb:.1f} MB)")
    
    # Select file
    if len(pdf_files) == 1:
        selected_file = pdf_files[0]
        print(f"\n📄 Selected: {selected_file}")
    else:
        try:
            choice = int(input(f"\nSelect PDF (1-{len(pdf_files)}): ")) - 1
            selected_file = pdf_files[choice]
        except (ValueError, IndexError):
            print("❌ Invalid selection")
            input("Press Enter to exit...")
            sys.exit(1)
    
    # Get file size
    file_size_mb = os.path.getsize(selected_file) / (1024*1024)
    
    # Choose processing method
    print(f"\n🔧 Choose processing method for {selected_file} ({file_size_mb:.1f} MB):")
    print("1. Create searchable PDF (recommended)")
    print("2. Extract text to .txt file only")
    print("3. Process in chunks (for very large files)")
    
    try:
        method = int(input("\nSelect method (1-3): "))
        
        if method == 1:
            output_file = f"searchable_{selected_file}"
            print(f"\n🚀 Starting OCR conversion...")
            print("⚠️  This may take a long time for large files!")
            
            # Ask about quality
            quality = input("\nUse high quality OCR? (slower but better) (y/n): ").strip().lower()
            dpi = 300 if quality in ['y', 'yes'] else 200
            
            confirm = input(f"\nProceed with conversion? (y/n): ").strip().lower()
            if confirm in ['y', 'yes', '']:
                create_searchable_pdf(selected_file, output_file, dpi)
        
        elif method == 2:
            output_file = selected_file.replace('.pdf', '_extracted.txt')
            print(f"\n🚀 Starting text extraction...")
            
            quality = input("\nUse high quality OCR? (slower but better) (y/n): ").strip().lower()
            dpi = 300 if quality in ['y', 'yes'] else 200
            
            extract_text_only(selected_file, output_file, dpi)
        
        elif method == 3:
            output_folder = selected_file.replace('.pdf', '_chunks')
            pages_per_chunk = int(input("Pages per chunk (default 50): ") or "50")
            
            print(f"\n🚀 Starting chunked processing...")
            process_in_chunks(selected_file, output_folder, pages_per_chunk)
        
        else:
            print("❌ Invalid method selected")
    
    except ValueError:
        print("❌ Invalid input")
    except KeyboardInterrupt:
        print("\n\n🛑 Cancelled by user")
    
    print("\n🏁 Script completed.")
    input("Press Enter to exit...")