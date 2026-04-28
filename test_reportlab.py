import base64
import io
from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import letter

# 1x1 transparent PNG
img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGP6zwAAAgcBApocMXEAAAAASUVORK5CYII="

def test():
    doc = SimpleDocTemplate("doc_test.pdf", pagesize=letter)
    img_bytes = base64.b64decode(img_b64)
    img_io = io.BytesIO(img_bytes)
    img = Image(img_io, width=100, height=100)
    doc.build([img])
    print("Success!")

if __name__ == "__main__":
    test()
