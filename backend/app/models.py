import torch
from pathlib import Path
from typing import Optional, Any

from qwen_asr import Qwen3ASRModel
from pyannote.audio import Pipeline
from funasr import AutoModel

from .config import get_settings


class ASRModel:
    _instance: Optional["ASRModel"] = None
    _model: Optional[Any] = None
    _qwen_model: Optional[Qwen3ASRModel] = None
    _funasr_model: Optional[AutoModel] = None
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
            self._funasr_model = AutoModel(
                model="FunAudioLLM/Fun-ASR-Nano-2512",
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": 30000},
                device=device_str,
            )
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
    def qwen_model(self) -> Optional[Qwen3ASRModel]:
        if self._qwen_model is None:
            self.init()
        return self._qwen_model

    @property
    def pipeline(self) -> Pipeline:
        if self._pipeline is None:
            self.init()
        return self._pipeline


asr_model = ASRModel()


def get_asr_model() -> ASRModel:
    return asr_model
