import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR / "a_fusionner"
OUTPUT_PATH = SCRIPT_DIR / "fusion.pdf"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
WORD_EXTENSIONS = {".docx", ".doc"}


def image_to_pdf(image_path, tmp_dir):
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    pdf_path = tmp_dir / (image_path.stem + ".pdf")
    img.save(pdf_path, "PDF")
    return pdf_path


def word_to_pdf(word_path, tmp_dir):
    # Necessite Microsoft Word installe (pilote via docx2pdf/pywin32)
    from docx2pdf import convert
    pdf_path = tmp_dir / (word_path.stem + ".pdf")
    convert(str(word_path), str(pdf_path))
    return pdf_path


def main():
    if not SOURCE_DIR.exists():
        SOURCE_DIR.mkdir(parents=True)
        print(f"Dossier cree : {SOURCE_DIR}")
        print("Mettez-y vos fichiers (pdf, images, word...) puis relancez ce script.")
        return

    fichiers = sorted(
        (f for f in SOURCE_DIR.iterdir() if f.is_file() and not f.name.startswith(".")),
        key=lambda f: f.name.lower()
    )

    if not fichiers:
        print(f"Aucun fichier trouve dans : {SOURCE_DIR}")
        print("Deposez-y vos fichiers a fusionner puis relancez ce script.")
        return

    writer = PdfWriter()
    ajoutes = []
    ignores = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for fichier in fichiers:
            ext = fichier.suffix.lower()
            try:
                if ext == ".pdf":
                    pdf_path = fichier
                elif ext in IMAGE_EXTENSIONS:
                    pdf_path = image_to_pdf(fichier, tmp_dir)
                elif ext in WORD_EXTENSIONS:
                    pdf_path = word_to_pdf(fichier, tmp_dir)
                else:
                    ignores.append(f"{fichier.name} (type non pris en charge)")
                    continue

                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
                ajoutes.append(fichier.name)
            except Exception as e:
                ignores.append(f"{fichier.name} (erreur : {e})")

        if not writer.pages:
            print("Aucun fichier n'a pu etre fusionne.")
            return

        with open(OUTPUT_PATH, "wb") as f:
            writer.write(f)

    print("Fichiers fusionnes :")
    for nom in ajoutes:
        print(f"  - {nom}")

    if ignores:
        print("\nFichiers ignores :")
        for nom in ignores:
            print(f"  - {nom}")

    print(f"\nResultat : {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
