import io
import json

import qrcode

from app.database.schemas.qr_data import QRData


def generate_qr_code(qr_json: QRData) -> bytes:
    data = json.dumps(qr_json, ensure_ascii=False)

    img = qrcode.make(data=data, box_size=5)
    byte_io = io.BytesIO()
    img.save(byte_io, format="PNG")
    byte_io.seek(0)
    return byte_io.getvalue()
