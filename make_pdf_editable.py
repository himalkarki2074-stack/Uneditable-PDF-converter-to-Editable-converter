import ocrmypdf
import sys
import os

# Usage: python make_pdf_editable.py input.pdf output.pdf

def main():
    if len(sys.argv) >= 3:
        input_pdf = sys.argv[1]
        output_pdf = sys.argv[2]
    else:
        input_pdf = input("Enter the path to the PDF file you want to convert: ").strip('"')
        if not input_pdf:
            print("No input file provided.")
            sys.exit(1)
        output_pdf = input("Enter the output PDF file name (or path): ").strip('"')
        if not output_pdf:
            print("No output file provided.")
            sys.exit(1)
    if not os.path.exists(input_pdf):
        print(f"Input file not found: {input_pdf}")
        sys.exit(1)
    print(f"Processing: {input_pdf} -> {output_pdf}")
    ocrmypdf.ocr(
        input_pdf,
        output_pdf,
        language="eng",
        force_ocr=True,
        output_type="pdf",
        deskew=True,
        optimize=3,
        progress_bar=True
    )
    print(f"Done! Output saved as: {output_pdf}")

if __name__ == "__main__":
    main()
