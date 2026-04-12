import os
import torch
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    api_key: str = Field(default="", alias="API_KEY")
    model_name: str = Field(default="Fun-ASR-Nano-2512", alias="MODEL_NAME")
    pyannote_token: str = Field(default="", alias="PYANNOTE_TOKEN")
    tts_model: str = Field(default="Qwen3-TTS-12Hz-1.7B-CustomVoice", alias="TTS_MODEL")
    tts_voice: str = Field(default="Vivian", alias="TTS_VOICE")
    use_funasr_diarization: bool = Field(default=False, alias="USE_FUNASR_DIARIZATION")

    @property
    def device(self) -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    @property
    def model_path(self) -> Path:
        if self.model_name == "Fun-ASR-Nano-2512":
            return BASE_DIR / "models" / "Fun-ASR-Nano-2512"
        elif self.model_name == "Qwen3-ASR-1.7B":
            return BASE_DIR / "models" / "Qwen" / "Qwen3-ASR-1.7B"
        return BASE_DIR / "models" / "Qwen" / "Qwen3-ASR-0.6B"

    @property
    def forced_aligner_path(self) -> Path:
        return BASE_DIR / "models" / "Qwen" / "Qwen3-ForcedAligner-0.6B"

    @property
    def pyannote_model_path(self) -> Path:
        return BASE_DIR / "models" / "pyannote" / "speaker-diarization-community-1"

    @property
    def vad_model_path(self) -> Path:
        return BASE_DIR / "models" / "speech_fsmn_vad_zh-cn-16k-common-pytorch"

    @property
    def spk_model_path(self) -> Path:
        return BASE_DIR / "models" / "speech_campplus_sv_zh-cn_16k-common"

    @property
    def paraformer_model_path(self) -> Path:
        return (
            BASE_DIR
            / "models"
            / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
        )

    @property
    def punc_model_path(self) -> Path:
        return (
            BASE_DIR / "models" / "punc_ct-transformer_cn-en-common-vocab471067-large"
        )

    @property
    def tts_model_path(self) -> Path:
        return BASE_DIR / "models" / "Qwen" / self.tts_model

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
