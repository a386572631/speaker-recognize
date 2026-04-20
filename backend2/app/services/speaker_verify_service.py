import logging
import torch
import numpy as np
import tempfile
import os
from pathlib import Path
from typing import Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeakerVerifyService:
    def __init__(self):
        self._model = None

    def load(self):
        if not settings.wespeaker_enabled:
            logger.info("Wespeaker 模型未开启")
            return

        import wespeaker

        model_path = settings.wespeaker_model_path
        if model_path.exists() and (model_path / "pytorch_model.bin").exists():
            self._model = wespeaker.load_model(str(model_path))
        else:
            self._model = wespeaker.load_model("chinese")

        logger.info("Wespeaker 模型加载成功")

    def compute_similarity(self, audio_path1: str, audio_path2: str) -> float:
        if not self._model:
            return 0.0
        return self._model.compute_similarity(audio_path1, audio_path2)

    def split_audio_by_segments(self, audio_path: str, segments: List[dict]) -> List[str]:
        import torchaudio

        waveforms, sample_rate = torchaudio.load(audio_path)
        if sample_rate != 16000:
            waveforms = torchaudio.transforms.Resample(sample_rate, 16000)(waveforms)
            sample_rate = 16000

        if waveforms.shape[0] > 1:
            waveforms = waveforms.mean(dim=0, keepdim=True)

        audio_files = []
        for i, seg in enumerate(segments):
            start_sample = int(seg["start"] * sample_rate)
            end_sample = int(seg["end"] * sample_rate)

            segment_audio = waveforms[:, start_sample:end_sample]

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                torchaudio.save(tmp.name, segment_audio, sample_rate)
                audio_files.append(tmp.name)

        return audio_files

    def verify_and_merge(
        self,
        audio_path: str,
        segments: List[dict],
        similarity_threshold: float = 0.7
    ) -> List[dict]:
        if not segments:
            return []

        if len(segments) == 1:
            segments[0]["speaker"] = "SPEAKER_01"
            return segments

        audio_files = self.split_audio_by_segments(audio_path, segments)

        try:
            result = [segments[0].copy()]
            result[0]["speaker"] = "SPEAKER_01"
            result[0]["similarity"] = None

            for i in range(1, len(segments)):
                similarity = self.compute_similarity(audio_files[0], audio_files[i])
                current_speaker = result[-1]["speaker"]

                if similarity > similarity_threshold:
                    result[-1]["end"] = segments[i]["end"]
                    result[-1]["similarity"] = similarity
                else:
                    speaker_num = int(current_speaker.split("_")[1]) + 1
                    result.append({
                        "start": segments[i]["start"],
                        "end": segments[i]["end"],
                        "speaker": f"SPEAKER_{speaker_num:02d}",
                        "similarity": similarity
                    })

            for f in audio_files:
                os.unlink(f)

        except Exception as e:
            logger.error(f"Wespeaker verification failed: {e}")
            for f in audio_files:
                try:
                    os.unlink(f)
                except:
                    pass
            return segments

        return result


speaker_verify_service = SpeakerVerifyService()
speaker_verify_service.load()