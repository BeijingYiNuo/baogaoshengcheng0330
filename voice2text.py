# voice2text.py
import torch
from transformers import pipeline
import librosa
import os
import static_ffmpeg

# 自动安装并配置 ffmpeg 环境
try:
    static_ffmpeg.add_paths()
except Exception as e:
    print(f"Warning: ffmpeg configuration failed: {e}")
    print("Tip: Please try manual installation of ffmpeg or run as Administrator.")

# 配置模型
# 使用 OpenAI 较新的 Whisper Large V3 Turbo 模型，速度更快且准确率极高
MODEL_NAME = "openai/whisper-large-v3-turbo"

def transcribe_audio_generator(audio_path, language="zh"):
    """
    使用 Hugging Face 的 Whisper 模型，以生成器形式流式返回识别结果。
    
    Yields:
    - (progress, partial_text)
    """
    # 自动选择设备: 优先 CUDA，其次 CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Whisper Large V3 Turbo 建议使用 float16 以节省显存并加速
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    # 1. 预处理音频
    print(f"正在读取并预处理音频文件: {audio_path}...")
    audio_array, sampling_rate = librosa.load(audio_path, sr=16000)
    total_duration = len(audio_array) / 16000
    
    # 2. 初始化 ASR 管道
    # 为了流式进度，我们分段处理音频
    pipe = pipeline(
        "automatic-speech-recognition",
        model=MODEL_NAME,
        torch_dtype=torch_dtype,
        device=device,
        chunk_length_s=30,
        batch_size=8
    )

    # 我们将音频切成 30 秒一段，手动模拟进度
    # 实际上 Whisper pipeline 的 chunk_length_s 已经在内部切片了，
    # 但为了在 Streamlit 看到进度条，我们手动进行大块分段
    chunk_size_s = 60 # 每 60 秒处理一次并返回结果
    chunk_samples = chunk_size_s * 16000
    
    all_text = ""
    # 引导提示词：强制模型输出标点符号并设定正式语境
    initial_prompt = "这是一段正式的面试录音记录。请确保输出包含完整的标点符号，如逗号、句号、问号等，并保持语言流利。"
    
    for i in range(0, len(audio_array), chunk_samples):
        # 计算进度
        progress = min(i / len(audio_array), 1.0)
        yield progress, all_text
        
        # 获取当前片段
        chunk = audio_array[i : i + chunk_samples]
        
        # 执行识别
        # prompt 参数能极大地引导模型生成标点符号和特定的语气
        result = pipe(
            chunk,
            generate_kwargs={
                "language": language, 
                "task": "transcribe",
                # "prompt": initial_prompt
            }
        )
        
        chunk_text = result["text"].strip()
        all_text += chunk_text + " "
        
        # 释放显存
        if device == "cuda":
            torch.cuda.empty_cache()
            
    yield 1.0, all_text

def transcribe_audio(audio_path, language="zh"):
    """
    兼容旧版的同步接口，内部调用生成器。
    """
    generator = transcribe_audio_generator(audio_path, language)
    final_text = ""
    for _, text in generator:
        final_text = text
    return final_text

# 示例用法
if __name__ == "__main__":
    # 这是一个简单的本地测试
    test_file = "test.m4a"
    if os.path.exists(test_file):
        text = transcribe_audio(test_file)
        print("识别结果:", text)
    else:
        print(f"未找到测试文件: {test_file}")
