import ocrmypdf
import os
from pathlib import Path

def convert_ocr_pdf_to_editable(input_pdf_path, output_pdf_path):
    """
    Convert an OCR PDF to an editable/searchable PDF
    
    Args:
        input_pdf_path (str): Path to input PDF file
        output_pdf_path (str): Path for output editable PDF file
    """
    
    # Check if input file exists
    if not os.path.exists(input_pdf_path):
        print(f"Error: Input file '{input_pdf_path}' not found!")
        return False
    
    try:
        print(f"Processing PDF: {input_pdf_path}")
        print("This may take a while for large files...")
        
        # Basic OCR options that work on Windows
        ocrmypdf.ocr(
            input_pdf_path,
            output_pdf_path,
            # Performance options
            jobs=os.cpu_count(),           # Use all CPU cores
            
            # OCR options
            language='eng',                # Change to your language
            force_ocr=True,               # Re-OCR even if text exists
            
            # Output options
            optimize=1,                   # Optimize output size
            pdf_renderer='hocr',          # Create searchable PDF
            
            # Progress tracking
            progress_bar=True,            # Show progress bar
        )
        
        print(f"✅ Successfully converted PDF!")
        print(f"📄 Output saved as: {output_pdf_path}")
        
        # Show file sizes
        input_size = os.path.getsize(input_pdf_path) / (1024*1024)  # MB
        output_size = os.path.getsize(output_pdf_path) / (1024*1024)  # MB
        print(f"📊 Input size: {input_size:.1f} MB")
        print(f"📊 Output size: {output_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during conversion: {str(e)}")
        
        # Check if it's a Tesseract issue
        if "tesseract" in str(e).lower():
            print("\n🔧 Tesseract OCR not found or not properly installed!")
            print("📥 Download and install from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("💡 Make sure to add Tesseract to your system PATH during installation")
        
        return False

def simple_ocr_conversion(input_pdf_path, output_pdf_path):
    """
    Ultra-simple OCR conversion with minimal options
    """
    try:
        print(f"Using minimal OCR method for: {input_pdf_path}")
        
        ocrmypdf.ocr(
            input_pdf_path,
            output_pdf_path,
            language='eng',
            progress_bar=True
        )
        
        print(f"✅ Successfully converted with simple method!")
        print(f"📄 Output saved as: {output_pdf_path}")
        
        # Show file sizes
        input_size = os.path.getsize(input_pdf_path) / (1024*1024)  # MB
        output_size = os.path.getsize(output_pdf_path) / (1024*1024)  # MB
        print(f"📊 Input size: {input_size:.1f} MB")
        print(f"📊 Output size: {output_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple OCR also failed: {str(e)}")
        return False

def batch_convert_pdfs(input_folder, output_folder):
    """
    Convert multiple PDFs in a folder
    
    Args:
        input_folder (str): Folder containing input PDFs
        output_folder (str): Folder for output PDFs
    """
    
    input_path = Path(input_folder)
    output_path = Path(output_folder)
    
    # Create output folder if it doesn't exist
    output_path.mkdir(exist_ok=True)
    
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    successful = 0
    failed = 0
    
    for pdf_file in pdf_files:
        print(f"\n🔄 Processing: {pdf_file.name}")
        
        output_file = output_path / f"editable_{pdf_file.name}"
        
        if convert_ocr_pdf_to_editable(str(pdf_file), str(output_file)):
            successful += 1
        else:
            failed += 1
    
    print(f"\n📈 Batch conversion complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

def check_tesseract():
    """
    Check if Tesseract is properly installed
    """
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ Tesseract found: {version_line}")
            return True
        else:
            print("❌ Tesseract found but not working properly")
            return False
    except FileNotFoundError:
        print("❌ Tesseract OCR not found on system PATH")
        print("📥 Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        print(f"❌ Error checking Tesseract: {e}")
        return False

# Example usage
if __name__ == "__main__":
    
    # First, check if Tesseract is installed
    print("🔍 Checking Tesseract OCR installation...")
    tesseract_ok = check_tesseract()
    
    if not tesseract_ok:
        print("\n⚠️  Tesseract OCR is required for this script to work.")
        print("Would you like to continue anyway? (Some features might not work)")
        continue_anyway = input("Continue? (y/n): ").strip().lower()
        if continue_anyway not in ['y', 'yes']:
            print("Please install Tesseract OCR and try again.")
            exit(1)
    
    # Get the current directory
    current_dir = os.getcwd()
    print(f"\nCurrent directory: {current_dir}")
    
    # List all PDF files in current directory
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    
    if pdf_files:
        print(f"\nFound {len(pdf_files)} PDF file(s):")
        for i, pdf in enumerate(pdf_files, 1):
            size_mb = os.path.getsize(pdf) / (1024*1024)
            print(f"  {i}. {pdf} ({size_mb:.1f} MB)")
        
        # Ask user to select a file
        try:
            choice = input(f"\nSelect a PDF to convert (1-{len(pdf_files)}) or press Enter to use the first one: ").strip()
            
            if not choice:
                choice = "1"
            
            file_index = int(choice) - 1
            
            if 0 <= file_index < len(pdf_files):
                input_file = pdf_files[file_index]
                output_file = f"editable_{input_file}"
                
                print(f"\n🔄 Converting: {input_file}")
                print(f"📄 Output will be: {output_file}")
                print(f"⚠️  This is a large file ({os.path.getsize(input_file) / (1024*1024):.1f} MB) - it may take a long time!")
                
                confirm = input("\nProceed? (y/n): ").strip().lower()
                if confirm in ['y', 'yes', '']:
                    # Try the conversion
                    success = convert_ocr_pdf_to_editable(input_file, output_file)
                    
                    # If that fails, try simple method
                    if not success:
                        print("\n🔄 Trying ultra-simple OCR method...")
                        simple_output = f"simple_{input_file}"
                        success = simple_ocr_conversion(input_file, simple_output)
                        
                        if success:
                            print(f"✅ Conversion completed using simple method!")
                            print(f"📄 File saved as: {simple_output}")
                else:
                    print("Conversion cancelled.")
            else:
                print("Invalid selection.")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nConversion cancelled by user.")
            
    else:
        print("\nNo PDF files found in the current directory.")
        print("Options:")
        print("1. Copy your PDF file to this directory")
        print("2. Or specify the full path below:")
        
        input_path = input("\nEnter full path to your PDF file (or press Enter to skip): ").strip().strip('"')
        
        if input_path and os.path.exists(input_path):
            filename = os.path.basename(input_path)
            output_file = f"editable_{filename}"
            
            print(f"\n🔄 Converting: {filename}")
            print(f"📄 Output will be: {output_file}")
            
            success = convert_ocr_pdf_to_editable(input_path, output_file)
            if not success:
                simple_output = f"simple_{filename}"
                success = simple_ocr_conversion(input_path, simple_output)
        else:
            print("\nTo use this script:")
            print("1. Copy your PDF file to this directory, or")
            print("2. Use batch_convert_pdfs('input_folder', 'output_folder')")
    
    print("\n🏁 Script completed. Press Enter to exit...")
    input()