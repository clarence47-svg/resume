from ingestion.ocr import OcrService


class FakeOcr:
    def __call__(self, image):
        return ([[None, "中文 OCR", 0.97]], None)


def test_ocr_result_can_be_normalized(test_settings) -> None:
    service = OcrService(test_settings)
    service.__dict__["engine"] = FakeOcr()
    assert service.recognize(b"image") == [("中文 OCR", 0.97)]
