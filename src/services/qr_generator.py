from PIL import Image as PILImage
import qrcode
from qrcode.constants import ERROR_CORRECT_M


class QRGenerator:
    """Generates QR code images encoding a URL for each part number."""

    def __init__(self, base_url: str = "https://brennaninc.com/parts/"):
        self.base_url = base_url

    def generate(self, part_number: str, size_px: int = 150) -> PILImage.Image:
        """Generate a QR code image for the given part number.

        Returns a PIL Image of the QR code at the requested pixel size.
        """
        url = f"{self.base_url}{part_number}"
        qr = qrcode.QRCode(
            version=None,  # auto-size
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((size_px, size_px), PILImage.Resampling.NEAREST)
        return img
