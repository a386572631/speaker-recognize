import logging
import torch
from pathlib import Path
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class DiarizationService:
    def __init__(self):
        self._pipeline = None

    def load(self):
        logger.info("加载 pyannote diarization")
        from pyannote.audio import Pipeline

        token = settings.pyannote_token or None

        self._pipeline = Pipeline.from_pretrained(
            str(settings.pyannote_model_path),
            token=token,
        )
        self._pipeline.to(torch.device(settings.device))

        try:
            from diarizers import SegmentationModel
            model = SegmentationModel().from_pretrained(
                str(settings.pyannote_segmentation_model_path),
                token=token,
            )
            model = model.to_pyannote_model()
            self._pipeline._segmentation.model = model.to(torch.device(settings.device))
            logger.info("替换 segmentation 模型：pyannote-segmentation-zho-001")
        except Exception as e:
            logger.warning(f"替换 segmentation 模型失败: {e}")

        logger.info(f"Pyannote pipeline 加载成功: {settings.device}")

    def diarize(self, audio_path: str, num_speakers: int = 0):
        if not self._pipeline:
            self.load()

        from pyannote.audio.pipelines.utils.hook import ProgressHook
        logger.info("说话人数设置: " + str(num_speakers))
        with ProgressHook() as hook:
            if num_speakers > 0:
                output = self._pipeline(audio_path, hook=hook, num_speakers=num_speakers)
            else:
                output = self._pipeline(audio_path, hook=hook, min_speakers=1, max_speakers=3)

        segments = []
        for turn, speaker in output.speaker_diarization:
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })
        return segments


diarization_service = DiarizationService()