import logging
import io
from pathlib import Path
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self._model_loaded = False
        self._qwen_tts_model: Optional[object] = None

    def load(self):
        logger.info("默认使用 edge-tts 服务")

    async def synthesize_edge(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()

    def synthesize(self, text: str, voice: str = "") -> bytes:
        if not voice:
            voice = settings.tts_voice
        import asyncio
        return asyncio.run(self.synthesize_edge(text, voice))

    def _get_qwen_tts_model_path(self) -> str:
        local_path = settings.models_dir / "Qwen" / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
        if local_path.exists():
            return str(local_path)
        return "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

    def synthesize_qwen(self, text: str, voice: str = "Chengu") -> bytes:
        from qwen_tts import Qwen3TTSModel
        import torch

        model_path = self._get_qwen_tts_model_path()
        logger.info(f"加载 Qwen-TTS 模型: {model_path}")

        self._qwen_tts_model = Qwen3TTSModel.from_pretrained(
            model_path,
            device_map=settings.device if "cuda" in settings.device else "cpu",
            dtype=torch.bfloat16 if "cuda" in settings.device else torch.float32,
        )

        wavs, sr = self._qwen_tts_model.generate_custom_voice(
            text=text,
            language="auto",
            speaker=f"speaker_{voice}",
        )

        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, wavs[0], sr, format="WAV")
        return buffer.getvalue()


tts_service = TTSService()
tts_service.load()