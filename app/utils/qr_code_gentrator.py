import io
import json

import qrcode


def generate_qr_code(qr_json: dict[str, str | int]) -> bytes:
    data = json.dumps(qr_json, ensure_ascii=False)

    img = qrcode.make(data=data, box_size=5)
    byte_io = io.BytesIO()
    img.save(byte_io, format="PNG")
    byte_io.seek(0)
    return byte_io.getvalue()
