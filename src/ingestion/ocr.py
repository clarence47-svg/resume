from functools import cached_property

from core.settings import Settings, get_settings


class OcrService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @cached_property
    def engine(self):
        from rapidocr_onnxruntime import RapidOCR

        return RapidOCR()

    def recognize(self, image: bytes) -> list[tuple[str, float]]:
        if not self.settings.ocr_enabled:
            return []
        result, _ = self.engine(image)
        if not result:
            return []
        return [(str(item[1]).strip(), float(item[2])) for item in result if str(item[1]).strip()]
