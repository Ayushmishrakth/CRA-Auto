import sys, os, re, zipfile, shutil
os.chdir(r"C:\Users\Admin\Desktop\CRA-PP\CRA-Auto\CRA-Tool")
sys.path.insert(0, os.getcwd())

from PIL import Image, ImageDraw
from pathlib import Path
import asyncio

# Create test logo first
logo_path = str(Path("storage/logos/test_logo.png").resolve())
Path("storage/logos").mkdir(parents=True, exist_ok=True)
img = Image.new('RGB', (300, 100), color='#003366')
ImageDraw.Draw(img).text((20, 35), "TPT TEST LOGO", fill='white')
img.save(logo_path)
print(f"[TEST] Logo created: {logo_path}")
print(f"[TEST] Logo exists: {os.path.exists(logo_path)}")

# Import DB exactly as the app does
from app.db.session import AsyncSessionLocal
from app.services.reporting import cra_report_service

async def test():
    assessment_id = "45e55c69-8cec-494b-a190-ef03d9bc3b0a"

    async with AsyncSessionLocal() as db:
        try:
            print(f"[TEST] Calling generate_report_bundle...")
            payload = await cra_report_service.generate_report_bundle(
                assessment_id=assessment_id,
                db=db,
                partner_name="TEST_PARTNER_TPT",
                logo_path=logo_path,
                company_address="Jammu India",
            )
            print(f"[TEST] payload={payload}")

            fp = None
            if isinstance(payload, dict):
                fp = (payload.get('file_path') or
                      payload.get('docx_path') or
                      payload.get('report_path'))
                if not fp and payload.get('artifacts'):
                    a = payload['artifacts']
                    if a:
                        fp = (a[0].get('file_path') or
                              a[0].get('storage_path') or
                              a[0].get('path'))
            elif isinstance(payload, str):
                fp = payload

            print(f"[TEST] Output file: {fp}")
            print(f"[TEST] Exists: {os.path.exists(fp) if fp else False}")

            if fp and os.path.exists(fp):
                with zipfile.ZipFile(fp) as z:
                    doc = z.read('word/document.xml').decode('utf-8')
                    media = [n for n in z.namelist() if 'media/' in n]
                    hdr = z.read('word/header1.xml').decode('utf-8') \
                          if 'word/header1.xml' in z.namelist() else ''

                print(f"[TEST] Images in doc: {doc.count('<w:drawing>')}")
                print(f"[TEST] Media files: {len(media)}")
                print(f"[TEST] Header images: {hdr.count('<w:drawing>')}")
                print(f"[TEST] Header texts: {re.findall(r'<w:t[^>]*>([^<]+)</w:t>', hdr)}")
                print(f"[TEST] Partner in doc: {'TEST_PARTNER_TPT' in doc}")
                print(f"[TEST] File size: {os.path.getsize(fp)}")

                shutil.copy(fp, "storage/TEST_OUTPUT.docx")
                print("[TEST] Saved to storage/TEST_OUTPUT.docx")

                if hdr.count('<w:drawing>') > 0:
                    print("[RESULT] ✅ LOGO IN HEADER - header injection WORKS")
                else:
                    print("[RESULT] ❌ NO LOGO IN HEADER - broken in report_builder.py")

                if 'TEST_PARTNER_TPT' in doc:
                    print("[RESULT] ✅ PARTNER NAME WORKS")
                else:
                    print("[RESULT] ❌ PARTNER NAME MISSING - not injected")

        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
