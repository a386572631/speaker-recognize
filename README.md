# Speaker Recognition System

语音识别系统，支持实时语音转写和说话人识别。

## 项目结构

```
speaker-recognize/
├── backend/           # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/        # API路由
│   │   │   ├── audio.py        # 音频转录/TTS接口
│   │   │   ├── transcribe.py  # 转录+说话人分离接口
│   │   │   └── websocket.py   # WebSocket实时转写
│   │   ├── core/       # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   └── auth.py       # 认证
│   │   ├── services/   # 业务服务
│   │   │   ├── asr_service.py         # ASR服务
│   │   │   ├── diarization_service.py # 说话人分离服务
│   │   │   ├── speaker_verify_service.py # 说话人验证服务
│   │   │   └── tts_service.py       # TTS服务
│   │   └── main.py     # 应用入口
│   ├── models/        # 预训练模型
│   ├── pyproject.toml
│   ├── .env          # 环境配置
│   └── uv.lock
│
├── realtime/         # 前端 (Vue3 + AntDesign)
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── composables/  # 组合式API
│   │   ├── assets/     # 静态资源
│   │   ├── App.vue
│   │   └── main.js
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
```

## 环境要求

- Python 3.10
- Node.js 18+
- pnpm (前端包管理)
- CUDA (可选，无GPU时自动使用CPU)

## 下载模型

后端依赖的模型需要手动下载：

```bash
cd backend

# Fun-ASR 模型
hf download FunAudioLLM/Fun-ASR-Nano-2512 --local_dir ./models/Fun-ASR-Nano-2512

modelscope download --model iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch --local_dir ./models/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch
modelscope download --model iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn --local_dir ./models/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn

# VAD模型
modelscope download --model iic/speech_fsmn-vad --local_dir ./models/fsmn-vad

# 标点
hf download funasr/ct-punc --local_dir ./models/ct-punc

# 说话人日志 CAM++
hf download funasr/campplus --local-dir ./models/campplus

# Qwen ASR 模型 (ModelScope)
modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ./models/Qwen/Qwen3-ASR-1.7B
modelscope download --model Qwen/Qwen3-ASR-0.6B --local_dir ./models/Qwen/Qwen3-ASR-0.6B
modelscope download --model Qwen/Qwen3-ForcedAligner-0.6B --local_dir ./models/Qwen/Qwen3-ForcedAligner-0.6B

# TTS 模型
# CosyVoice3
hf download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local-dir ./backend/models/Fun-CosyVoice3-0.5B-2512

# 安装Cosyvoice3 https://github.com/FunAudioLLM/CosyVoice
# 先注释掉`openai-whisper==20231117`
uv pip install -r ../CosyVoice/requirements.txt
pip install "setuptools==81.0.0" -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com
pip install openai-whisper==20231117 --no-build-isolation -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com


# 标点模型 (HuggingFace)
# 需手动下载: https://huggingface.co/funasr/ct-punc

# Camp++ 说话人模型 (HuggingFace)
# 需手动下载: https://huggingface.co/funasr/campplus

# PyAnnote 说话人分离模型
# 首次使用自动下载，需设置 PYANNOTE_TOKEN 环境变量

# 还需访问：https://github.com/wenet-e2e/wespeaker 和 https://github.com/huggingface/diarizers 
# 分别安装依赖 uv pip install -e .
```

## 启动后端

```bash
cd backend

# 安装依赖
  # 安装pyproject.toml
  uv sync

  # 安装 diarizers 依赖
  uv pip install -e ~/Documents/Tools/diarizers-main

  # 安装 wespeaker 依赖
  uv pip install -e ../wespeaker

  # 安装cosyvoice3
  uv pip install -r ../CosyVoice/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com

# 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 10030
```

服务启动后：
- API文档: http://localhost:10030/docs
- 健康检查: http://localhost:10030/health

## 启动前端

```bash
cd realtime

# 安装依赖
pnpm install

# 启动开发服务器
npm run dev
```

前端默认运行在 http://localhost:5173

## API接口

### WebSocket - 实时语音转写

连接: `ws://localhost:10030/ws/transcribe`

认证: 发送 `Authorization: Bearer <API_KEY>`

发送消息:
```json
{
  "type": "transcribe",
  "audio": "<base64音频数据>"
}
```

### HTTP - 批量转录+说话人分离

POST `/transcribe`

Headers: `Authorization: Bearer <API_KEY>`

参数:
- file: 音频文件 (multipart/form-data)
- model: 模型名称 (可选，默认qwen)
- language: 语言 (默认auto)
- num_speakers: 说话人数量 (可选)

### HTTP - 音频转录

POST `/v1/audio/transcriptions`

Headers: `Authorization: Bearer <API_KEY>`

### HTTP - 语音合成

POST `/v1/audio/speech`

Headers: `Authorization: Bearer <API_KEY>`

Body:
```json
{
  "input": "要合成的内容",
  "model": "tts-1",
  "voice": "zh-CN-XiaoxiaoNeural"
}
```

### Health Check

GET `/health`

## 配置 (.env)

```bash
# 模型选择: fun-asr-nano-2512 / qwen
MODEL=funasr

# Fun-ASR模型路径
FUN_ASR_MODEL=./models/Fun-ASR-Nano-2512
QWEN_ASR_MODEL=./models/Qwen/Qwen3-ASR-1.7B

# PyAnnote HuggingFace Token
PYANNOTE_TOKEN=your_huggingface_token

# API认证密钥
OPENAI_API_KEY=your_api_key

# TTS配置 (edge-tts / qwen-tts)
TTS_MODEL=edge-tts
TTS_VOICE=zh-CN-XiaoxiaoNeural

# 热词API (可选)
HOTWORD_API_URL=https://example.com/api

# WeSpeaker说话人验证 (可选)
WESPEAKER_ENABLED=True
```

## 功能特性

- VAD自动检测语音结束
- 实时语音转写
- 说话人区分 (PyAnnote + Cam++)
- 说话人验证 (WeSpeaker)
- 标点插入
- TTS语音合成
- 深色主题界面