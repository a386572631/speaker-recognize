import logging
import os
import requests
from pathlib import Path
from typing import Optional, List
from funasr import AutoModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class ASRService:
    def __init__(self):
        self._fun_asr_model: Optional[AutoModel] = None
        self._qwen_asr_model: Optional[object] = None
        self._model_loaded = False
        self._hotwords: List[str] = []
        self._load_hotwords()

    def _load_hotwords(self):
        if not settings.hotword_api_url:
            logger.info("未配置热词接口，跳过热词加载")
            return

        try:
            response = requests.get(settings.hotword_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("hasError") == -1:
                logger.warning(f"热词接口返回错误: {data.get('errorMessage')}")
                return

            words = data.get("data", []) or []
            self._hotwords = [w.strip() for w in words if w.strip()]
            logger.info(f"成功加载 {len(self._hotwords)} 个热词: {self._hotwords[:10]}...")
        except Exception as e:
            logger.warning(f"加载热词失败: {e}")
            self._hotwords = []

    def get_hotwords_text(self) -> str:
        return " ".join(self._hotwords)

    def _get_model_path(self, model_name: str) -> str:
        local_path = settings.models_dir / "Fun-ASR-Nano-2512"
        if local_path.exists():
            return str(local_path)
        return model_name

    def load_fun_asr(self, model_name: Optional[str] = None):
        import funasr
        model_dir = self._get_model_path(model_name or "FunAudioLLM/Fun-ASR-Nano-2512")
        model_py_path = Path(funasr.__file__).parent / "models" / "fun_asr_nano" / "model.py"

        logger.info(f"加载 Fun-ASR 模型：{model_dir}")
        kwargs = {
            "model": model_dir,
            "device": settings.device,
            "disable_update": True,
            "trust_remote_code": True,
            "remote_code": str(model_py_path),
        }
        self._fun_asr_model = AutoModel(**kwargs)
        self._model_loaded = True
        logger.info(f"Fun-ASR 模型加载设备：{settings.device}")
        return self._fun_asr_model

    def load_qwen_asr(self, model_name: Optional[str] = None):
        from qwen_asr import Qwen3ASRModel
        import torch
        model_dir = model_name or settings.qwen_asr_model
        local_path = settings.models_dir / "Qwen" / "Qwen3-ASR-1.7B"
        if not local_path.exists():
            local_path = settings.models_dir / "Qwen"
        if not local_path.exists():
            local_path = model_dir

        logger.info(f"加载 Qwen-ASR 模型：{local_path}")
        dtype = torch.bfloat16 if "cuda" in settings.device else torch.float32
        self._qwen_asr_model = Qwen3ASRModel.from_pretrained(
            str(local_path),
            dtype=dtype,
            device_map=settings.device,
            max_inference_batch_size=32,
            max_new_tokens=256,
            forced_aligner=str(settings.forced_aligner_path),
            forced_aligner_kwargs=dict(
                dtype=torch.bfloat16,
                device_map=settings.device,
            )
        )
        logger.info(f"Qwen-ASR 模型加载设备：{settings.device}")
        return self._qwen_asr_model

    def preload(self):
        model_name = settings.model.lower()
        logger.info(f"预加载 ASR 模型：{model_name}")

        if "fun-asr" in model_name or "funasr" in model_name:
            self.load_fun_asr()
        elif "qwen" in model_name:
            self.load_qwen_asr()
        else:
            logger.warning(f"未知 ASR 模型：{model_name}, 默认加载 Fun-ASR")
            self.load_fun_asr()

    @property
    def fun_asr(self):
        if not self._model_loaded:
            self.load_fun_asr()
        return self._fun_asr_model

    @property
    def qwen_asr(self):
        if self._qwen_asr_model is None:
            self.load_qwen_asr()
        return self._qwen_asr_model

    def transcribe_fun_asr(self, audio_data, language: Optional[str] = None):
        hotword = self.get_hotwords_text()
        result = self.fun_asr.generate(
            input=[audio_data],
            language=language if language else "auto",
            itn=True,
            hotword=hotword if hotword else "",
        )
        return result[0]["text"] if result else ""

    def transcribe_qwen_asr(self, audio_data):
        hotwords = self._hotwords
        result = self.qwen_asr.transcribe(audio_data, hotwords=hotwords)
        return result[0].text if result else ""


asr_service = ASRService()
asr_service.preload()