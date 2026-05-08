import logging
import torchaudio
import io
import asyncio
import re
from pathlib import Path
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Remove special characters like * and replace with space."""
    text = re.sub(r'[*#@$%^&+=]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


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

    async def synthesize_edge_stream(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural"):
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
                await asyncio.sleep(0)

    # def synthesize(self, text: str, voice: str = "") -> bytes:
    #     text = clean_text(text)
    #     if not voice:
    #         voice = settings.tts_voice

    #     tts_model = settings.tts_model.lower()

    #     if tts_model == "cosyvoice3" or tts_model == "cosyvoice":
    #         return self.synthesize_cosyvoice(text, voice)
    #     elif tts_model == "qwen-tts" or tts_model == "qwen":
    #         return self.synthesize_qwen(text, voice)
    #     else:
    #         import asyncio
    #         return asyncio.run(self.synthesize_edge(text, voice))

    async def synthesize_async(self, text: str, voice: str = "") -> bytes:
        text = clean_text(text)
        if not voice:
            voice = settings.tts_voice

        tts_model = settings.tts_model.lower()

        if tts_model == "cosyvoice3" or tts_model == "cosyvoice":
            return self.synthesize_cosyvoice(text, voice)
        elif tts_model == "qwen-tts" or tts_model == "qwen":
            return self.synthesize_qwen(text, voice)
        else:
            return await self.synthesize_edge(text, voice)

    # def synthesize_stream(self, text: str, voice: str = ""):
    #     text = clean_text(text)
    #     if not voice:
    #         voice = settings.tts_voice

    #     tts_model = settings.tts_model.lower()

    #     if tts_model == "cosyvoice3" or tts_model == "cosyvoice":
    #         return self.synthesize_cosyvoice_stream(text, voice)
    #     else:
    #         import asyncio
    #         loop = asyncio.new_event_loop()
    #         asyncio.set_event_loop(loop)
    #         try:
    #             return loop.run_until_complete(self.synthesize_stream_async(text, voice))
    #         finally:
    #             loop.close()

    async def synthesize_stream_async(self, text: str, voice: str = ""):
        text = clean_text(text)
        if not voice:
            voice = settings.tts_voice

        tts_model = settings.tts_model.lower()

        if tts_model == "cosyvoice3" or tts_model == "cosyvoice":
            async for chunk in self.synthesize_cosyvoice_stream(text, voice):
                yield chunk
        else:
            async for chunk in self.synthesize_edge_stream(text, voice):
                yield chunk

    def get_prompt_wav(self, voice: str = "") -> str:
        if not voice:
            voice = settings.tts_voice

        voice_map = {
            "default": "app/tts_wav/zero_shot_prompt.wav",
            "jjl": "app/tts_wav/jjl.wav",
            "demo": "app/tts_wav/demo.wav",
        }
        return voice_map.get(voice, "app/tts_wav/zero_shot_prompt.wav")

    def synthesize_cosyvoice(self, text: str, voice: str = "default", instruction: str = "") -> bytes:
        prompt_wav = self.get_prompt_wav(voice)
        logger.info(f"复刻音频：{prompt_wav}")

        #stream = self._cosyvoice_model.inference_instruct2(
        #    tts_text=f"{instruction}<|endofprompt|>{text}",
        #    instruct_text="",
        #    prompt_wav=prompt_wav,
        #    stream=False
        #)
        #stream = self._cosyvoice_model.inference_instruct2(
        #        text,
        #        'You are a helpful assistant. 请用尽可能快地语速说一句话。<|endofprompt|>',
        #        prompt_wav,
        #        stream=False
        #)
        stream = self._cosyvoice_model.inference_zero_shot(text,
                            'You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。',
                            prompt_wav, 
                            stream=False)
        
        buffer = io.BytesIO()
        for result in stream:
            audio_tensor = result["tts_speech"]
            wav_tensor = audio_tensor.cpu().detach()
            torchaudio.save(buffer, wav_tensor, self._cosyvoice_model.sample_rate, format="wav")
            break

        buffer.seek(0)
        return buffer.read()

    async def synthesize_cosyvoice_stream(self, text: str, voice: str = "default"):
        prompt_wav = self.get_prompt_wav(voice)
        stream = self._cosyvoice_model.inference_zero_shot(
            text,
            'You are a helpful assistant.<|endofprompt|>希望你以后能够做的比我还好呦。',
            prompt_wav,
            stream=True
        )

        original_sr = self._cosyvoice_model.sample_rate
        target_sr = 44100
        if original_sr != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=original_sr, new_freq=target_sr)

        for result in stream:
            audio_tensor = result["tts_speech"]
            wav_tensor = audio_tensor.cpu().detach()

            if original_sr != target_sr:
                wav_tensor = resampler(wav_tensor)

            pcm_data = (wav_tensor.clamp(-1.0, 1.0) * 32767).short().numpy().tobytes()
            yield pcm_data
            await asyncio.sleep(0)

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
