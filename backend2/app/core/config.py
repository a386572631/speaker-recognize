import os
import torch
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_root: Path = Path(__file__).parent.parent.parent
    models_dir: Path = project_root / "models"
    pyannote_model_path: Path = models_dir / "pyannote" / "speaker-diarization-community-1"
    pyannote_segmentation_model_path: Path = models_dir / "pyannote" / "pyannote-segmentation-zho-001"
    wespeaker_model_path: Path = models_dir / "wespeaker"

    paraformer_model_path: Path = models_dir / "speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_model_path: Path = models_dir / "fsmn-vad"
    punc_model_path: Path = models_dir / "ct-punc"
    campplus_model_path: Path = models_dir / "campplus"

    model: str = "fun-asr-nano-2512"
    fun_asr_model: str = "./models/Fun-ASR-Nano-2512"
    qwen_asr_model: str = "./models/Qwen/Qwen3-ASR-1.7B"
    forced_aligner_path: str = "./models/Qwen/Qwen3-ForcedAligner-0.6B"
    device: str = ""
    pyannote_token: str = ""
    openai_api_key: str = ""

    tts_model: str = "edge-tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"

    hotword_api_url: str = ""
    wespeaker_enabled: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.device:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.models_dir.mkdir(exist_ok=True)


settings = Settings()