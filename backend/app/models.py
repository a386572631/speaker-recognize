import sys
import torch
from pathlib import Path
from typing import Optional, Any

from qwen_asr import Qwen3ASRModel
from pyannote.audio import Pipeline
from funasr import AutoModel

from .config import get_settings

FUNASR_NANO_PATH = (
    Path(__file__).parent.parent / "models" / "Fun-ASR-Nano-2512" / "tmp_funassr"
)
if FUNASR_NANO_PATH.exists() and str(FUNASR_NANO_PATH) not in sys.path:
    sys.path.insert(0, str(FUNASR_NANO_PATH))

from .funasr.model import FunASRNano


class ASRModel:
    _instance: Optional["ASRModel"] = None
    _model: Optional[Any] = None
    _qwen_model: Optional[Qwen3ASRModel] = None
    _funasr_model: Optional[AutoModel] = None
    _funasr_nano_model: Optional[Any] = None
    _funasr_nano_kwargs: Optional[dict] = None
    _funasr_spk_model: Optional[AutoModel] = None
    _pipeline: Optional[Pipeline] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self):
        if self._model is not None:
            return

        settings = get_settings()
        device_str = str(settings.device)

        if settings.model_name == "Fun-ASR-Nano-2512":
            self._funasr_nano_model, self._funasr_nano_kwargs = (
                FunASRNano.from_pretrained(
                    model=str(settings.model_path),
                    device=device_str,
                )
            )
            self._funasr_nano_model.eval()
        else:
            self._qwen_model = Qwen3ASRModel.from_pretrained(
                str(settings.model_path),
                dtype=torch.bfloat16,
                device_map=device_str,
                max_inference_batch_size=32,
                max_new_tokens=256,
                forced_aligner=str(settings.forced_aligner_path),
                forced_aligner_kwargs=dict(
                    dtype=torch.bfloat16,
                    device_map=device_str,
                ),
            )

        self._pipeline = Pipeline.from_pretrained(
            str(settings.pyannote_model_path),
            token=settings.pyannote_token,
        )
        self._pipeline.to(settings.device)

        print(f"模型加载成功: {settings.model_name}, 设备: {settings.device}")

    @property
    def model(self) -> Any:
        if self._model is None:
            self.init()
        return self._model

    @property
    def funasr_model(self) -> Optional[AutoModel]:
        if self._funasr_model is None:
            self.init()
        return self._funasr_model

    @property
    def funasr_nano_model(self) -> Optional[Any]:
        if self._funasr_nano_model is None:
            self.init()
        return self._funasr_nano_model

    @property
    def funasr_nano_kwargs(self) -> Optional[dict]:
        if self._funasr_nano_kwargs is None:
            self.init()
        return self._funasr_nano_kwargs

    @property
    def qwen_model(self) -> Optional[Qwen3ASRModel]:
        if self._qwen_model is None:
            self.init()
        return self._qwen_model

    @property
    def pipeline(self) -> Pipeline:
        if self._pipeline is None:
            self.init()
        return self._pipeline

    @property
    def funasr_spk_model(self) -> Optional[AutoModel]:
        if self._funasr_spk_model is None:
            settings = get_settings()
            device_str = str(settings.device)
            self._funasr_spk_model = AutoModel(
                model=str(settings.paraformer_model_path),
                vad_model=str(settings.vad_model_path),
                punc_model=str(settings.punc_model_path),
                spk_model=str(settings.spk_model_path),
                device=device_str,
                trust_remote_code=True
            )
        return self._funasr_spk_model


asr_model = ASRModel()


def get_asr_model() -> ASRModel:
    return asr_model


class TTSModel:
    _instance: Optional["TTSModel"] = None
    _model: Optional[Any] = None
    _tts_type: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self):
        if self._model is not None:
            return

        settings = get_settings()

        if settings.tts_model == "Qwen3-TTS-12Hz-1.7B-CustomVoice":
            self._tts_type = "qwen"
            from qwen_tts import Qwen3TTSModel

            device_str = str(settings.device)

            self._model = Qwen3TTSModel.from_pretrained(
                str(settings.tts_model_path),
                device_map=device_str,
                dtype=torch.bfloat16,
                attn_implementation="flash_attention_2",
            )
            print(
                f"Qwen TTS模型加载成功: {settings.tts_model}, 设备: {settings.device}"
            )
        else:
            self._tts_type = "edge"
            import edge_tts

            self._model = edge_tts.Communicate
            print(f"Edge TTS初始化成功")

    @property
    def model(self) -> Any:
        if self._model is None:
            self.init()
        return self._model

    @property
    def tts_type(self) -> str:
        if self._model is None:
            self.init()
        return self._tts_type

    def generate_custom_voice(
        self,
        text: str,
        language: str = "Chinese",
        speaker: str = "Vivian",
        instruct: str = "",
        voice: str = None,
        speed: float = 1.0,
    ):
        if self._tts_type == "qwen":
            return self.model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruct,
            )
        else:
            raise NotImplementedError("Use generate_custom_voice_async for edge-tts")

    async def generate_custom_voice_async(
        self,
        text: str,
        voice: str = "Vivian",
        speed: float = 1.0,
    ):
        import asyncio
        import numpy as np
        from io import BytesIO
        import soundfile as sf

        VOICE_MAP = {
            "alloy": "en-US-AlexNeural",
            "echo": "en-US-GuyNeural",
            "fable": "en-US-SaraNeural",
            "onyx": "en-US-JasonNeural",
            "nova": "en-US-AriaNeural",
            "shimmer": "en-US-JennyNeural",
        }

        voice = VOICE_MAP.get(voice, voice)
        if not voice.endswith("Neural"):
            voice = f"{voice}-Neural"

        communicate = self._model(text, voice, rate=f"+{int((speed - 1) * 100)}%")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        buffer = BytesIO(audio_data)
        data, samplerate = sf.read(buffer)
        if data.ndim > 1:
            data = data.mean(axis=1)
        return [data.astype(np.float32)], samplerate


tts_model = TTSModel()


def get_tts_model() -> TTSModel:
    return tts_model
