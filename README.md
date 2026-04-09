# Speaker Recognition System

语音识别系统，支持实时语音转写和说话人识别。

## 项目结构

```
speaker-recognize/
├── backend/           # 后端 (FastAPI)
│   ├── app/          # 应用代码
│   ├── main.py       # 入口文件
│   ├── pyproject.toml
│   └── .env          # 环境配置
├── frontend/         # 前端 (Vue3 + AntDesign)
│   └── src/
│       └── App.vue
├── Qwen/            # Qwen ASR模型
└── pyannote/        # PyAnnote说话人分割模型
```

## 环境要求

- Python 3.10+
- Node.js 18+
- CUDA (可选，无GPU时自动使用CPU)

## 后端启动

```bash
cd backend

# 使用uv安装依赖
uv sync

# 启动服务
uv run python main.py
```

服务启动后：
- HTTP API: http://localhost:5062
- WebSocket: ws://localhost:5062/ws

## 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## API接口

### WebSocket - 语音识别

连接: `ws://localhost:5062/ws`

认证: 发送 `Authorization: Bearer <API_KEY>`

发送消息:
```json
{
  "type": "transcribe",
  "audio": "<base64音频数据>"
}
```

### HTTP - 说话人识别

POST `/v1/audio/transcriptions`

Headers: `Authorization: Bearer <API_KEY>`

支持 `multipart/form-data` 上传文件或 JSON body 传 base64 音频。

## 配置 (.env)

```bash
API_KEY=your_api_key
MODEL_NAME=Qwen3-ASR-1.7B  # 或 Qwen3-ASR-0.6B
PYANNOTE_TOKEN=your_huggingface_token
```

## 功能特性

- VAD自动检测语音结束
- 实时语音转写
- 说话人区分
- 深色主题界面
- 音频下载