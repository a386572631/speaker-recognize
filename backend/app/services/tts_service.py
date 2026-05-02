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
        self._cosyvoice_model: Optional[object] = None

    def load(self):
        logger.info(f"TTS服务配置: {settings.tts_model}")
        if "cosyvoice" in settings.tts_model.lower():
            self.load_cosyvoice_model()

    def load_cosyvoice_model(self):
        local_path = settings.cosyvoice_model_path
        if not Path(local_path).exists():
            logger.info(f"模型不存在：{local_path}")
            return str(local_path)
        from cosyvoice.cli.cosyvoice import AutoModel
        import torchaudio
        import sys
        sys.path.append('third_party/Matcha-TTS')
        logger.info(f"加载 CosyVoice3 模型: {local_path}")
        self._cosyvoice_model = AutoModel(model_dir=local_path)

    def _get_qwen_tts_model_path(self) -> str:
        local_path = settings.models_dir / "Qwen" / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
        if local_path.exists():
            return str(local_path)
        return "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

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

        tts_model = settings.tts_model.lower()

        if tts_model == "cosyvoice3" or tts_model == "cosyvoice":
            return self.synthesize_cosyvoice(text, voice)
        elif tts_model == "qwen-tts" or tts_model == "qwen":
            return self.synthesize_qwen(text, voice)
        else:
            import asyncio
            return asyncio.run(self.synthesize_edge(text, voice))

    def get_prompt_wav(self, voice: str = "") -> str:
        if not voice:
            voice = settings.tts_voice

        voice_map = {
            "default": "app/tts_wav/zero_shot_prompt.wav",
        }
        return voice_map.get(voice, "app/tts_wav/zero_shot_prompt.wav")

    def synthesize_cosyvoice(self, text: str, voice: str = "default", instruction: str = "用开心的语气说") -> bytes:
        prompt_wav = self.get_prompt_wav(voice)

        stream = self._cosyvoice_model.inference_instruct2(
            tts_text=f"{instruction}<|endofprompt|>{text}",
            instruct_text="",
            prompt_wav=prompt_wav,
            stream=False
        )

        buffer = io.BytesIO()
        for result in stream:
            audio_tensor = result["tts_speech"]
            wav_tensor = audio_tensor.cpu().detach()
            torchaudio.save(buffer, wav_tensor, self._cosyvoice_model.sample_rate, format="wav")
            break

        buffer.seek(0)
        return buffer.read()

    def synthesize_cosyvoice_stream(self, text: str, voice: str = "default", instruction: str = "用开心的语气说"):
        prompt_wav = self.get_prompt_wav(voice)

        stream = self._cosyvoice_model.inference_instruct2(
            tts_text=f"{instruction}<|endofprompt|>{text}",
            instruct_text="",
            prompt_wav=prompt_wav,
            stream=True
        )

        buffer = io.BytesIO()
        for result in stream:
            audio_tensor = result["tts_speech"]
            wav_tensor = audio_tensor.cpu().detach()
            buffer = io.BytesIO()
            torchaudio.save(buffer, wav_tensor, self._cosyvoice_model.sample_rate, format="wav")
            buffer.seek(0)
            yield buffer.read()
            buffer.seek(0)
            buffer.truncate(0)

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