---
title: 面试报告自动生成工具
emoji: 📑
app_file: asgi.py
pinned: false
---

# 面试报告自动生成工具

本项目通过上传简历和音频，结合 OpenAI LLM 和语音识别，生成面试评估报告（Word `.docx`）。

## 目录结构

- `app.py`：Streamlit Web 界面入口
- `doc2md.py`：把 `template.docx` 转 `template.md`，再用 LLM 修复 Markdown，生成 `template.json`
- `report_generator.py`：将 LLM 结果填充进 Word 模板
- `voice2text.py`：语音转文本 (Whisper + transformers)
- `config.json`：API 和模型配置
- `template.docx`：报告模板（可自行修改）
- `template.md` / `template.json`：生成流程中间结果

## 环境依赖

建议新建虚拟环境后安装：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### requirements.txt 关键依赖

- `streamlit`：Web UI
- `openai`：调用 OpenAI API
- `python-docx`：读写 Word 模板
- `pypandoc` + `tqdm`：doc2md 文件转换与进度显示
- `pypdf`：PDF 文本抽取
- `transformers`, `torch`, `librosa`, `static_ffmpeg`：语音转文本
- `python-dotenv`：可选，从 `.env` 读取 API Key

## 配置 OpenAI

```json
{
  "api_key": "YOUR_API_KEY",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o"
}
```

1. 请在 `config.json` 中填写 `api_key`。
2. 如果使用备用地址，请修改 `base_url`。
3. 生产环境推荐使用 `gpt-4o` / `gpt-3.5-turbo`。

## 如何通过 `doc2md.py` 更新模板

1. 编辑 `template.docx`：添加/修改占位标签，格式为 `{{Key}}` 或 `{{Key:说明}}`。
2. 运行：

```bash
python doc2md.py
```

3. 该脚本会执行：
- `pandoc_process` 将 `template.docx` 转为 `template.md`
- `llm_process` 利用 OpenAI 将 Markdown 规范化
- `split_md` 生成 `template.json` 内容块

4. 结果文件：
- `template.md`
- `template.json`

## 运行服务

执行：

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

### 流程说明

1. 左侧输入 API Key / Base URL / 模型，点击「保存配置」。
2. 上传简历（DOC/DOCX/PDF）与面试音频。
3. 语音转文本并调用 `generate_interview_data_multi_stage` 产生结构化候选人数据。
4. `fill_docx_template` 将数据填入 `template.docx`，导出 `reports/` 下 Word 报告。

## 注意事项

- 依赖 `ffmpeg`，若未安装，请参照 `static_ffmpeg` 或本地安装 `ffmpeg`。
- 模型调用有计费，请设置合理 `max_tokens` 及输入长度。
- `template.docx` 结构若变更，可能需要调整 `report_generator.py` 中占位符替换逻辑。

## 常见问题

- `pypandoc` 运行失败：需要安装 Pandoc 运行时，可从 https://pandoc.org/ 下载。
- 语音识别慢或显存不足：可改为 CPU 模式或使用更小模型。

---

谢谢使用！