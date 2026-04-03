import os
from pydub import AudioSegment
import torch
from qwen_asr import Qwen3ASRModel

MAX_NEW_TOKENS = 1024


# =========================
# 1. 音频切分
# =========================
def split_m4a(
    input_file,
    output_dir="chunks",
    max_new_tokens=MAX_NEW_TOKENS,
    tokens_per_minute=300,
    safety_ratio=0.4,
    overlap_ms=3000,
    min_chunk_ms=60 * 1000,  # ⭐关键：最小1分钟
):
    os.makedirs(output_dir, exist_ok=True)

    # 理论时长
    max_minutes = (max_new_tokens / tokens_per_minute) * safety_ratio
    chunk_ms = int(max_minutes * 60 * 1000)

    # ⭐加下限保护
    if chunk_ms < min_chunk_ms:
        print(f"[WARN] chunk 太小，已提升到最小值 {min_chunk_ms/1000}s")
        chunk_ms = min_chunk_ms

    print(f"[INFO] 每段时长 ≈ {chunk_ms/1000:.1f} 秒")

    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000).set_channels(1)

    total_ms = len(audio)

    chunks = []
    idx = 0
    start = 0

    prev_start = -1

    while start < total_ms:
        end = min(start + chunk_ms, total_ms)

        # 防止死循环
        if end <= start:
            print("[ERROR] end <= start，强制退出")
            break

        chunk = audio[start:end]

        output_path = os.path.join(output_dir, f"chunk_{idx}.wav")
        chunk.export(output_path, format="wav")

        chunks.append(output_path)
        print(f"[INFO] 生成: {output_path}")

        idx += 1

        # 下一段
        next_start = end - overlap_ms

        # ⭐关键1：禁止倒退
        if next_start <= start:
            next_start = start + chunk_ms

        # ⭐关键2：禁止卡住
        if next_start == prev_start:
            print("[ERROR] start 未推进，强制跳出")
            break

        prev_start = start
        start = next_start

    return chunks


# =========================
# 2. ASR 推理
# =========================
def transcribe_chunks(model, chunk_files, output_file="v2t.md"):
    results_all = []

    # 以追加模式打开，并开启行缓冲
    with open(output_file, "w", encoding="utf-8", buffering=1) as f:
        for i, chunk in enumerate(chunk_files):
            print(f"[INFO] 识别中: {chunk}")

            results = model.transcribe(audio=chunk)
            text = results[0].text.strip()

            results_all.append(text)

            # ===== 实时写入 =====
            f.write(text + "\n")
            f.flush()  # 强制写入磁盘
            os.fsync(f.fileno())  # ⭐更强：防止系统缓存（可选但建议）

    return results_all


# =========================
# 3. 去重拼接（处理 overlap 重复）
# =========================
def merge_texts(texts):
    """
    简单去重拼接（处理 overlap 造成的重复）
    """
    final_text = ""

    for text in texts:
        if not final_text:
            final_text = text
            continue

        # 找重叠部分
        overlap_len = min(len(final_text), len(text))
        merged = False

        for i in range(overlap_len, 20, -1):  # 至少匹配20字符
            if final_text.endswith(text[:i]):
                final_text += text[i:]
                merged = True
                break

        if not merged:
            final_text += "\n" + text

    return final_text


# =========================
# 4. 主流程
# =========================
def main():
    input_audio = "temp_audio/田宇航.m4a"

    # -------- 切分 --------
    chunks = split_m4a(
        input_audio,
        max_new_tokens=MAX_NEW_TOKENS,  # 建议降低
        tokens_per_minute=300,
        safety_ratio=0.4,
        overlap_ms=3000,
    )

    # -------- 加载模型 --------
    print("[INFO] 加载模型...")

    model = Qwen3ASRModel.from_pretrained(
        "Qwen/Qwen3-ASR-0.6B",
        dtype=torch.float16,  # 更省显存
        device_map="cuda:1",
        max_inference_batch_size=1,  # 防止OOM
        max_new_tokens=MAX_NEW_TOKENS,
    )

    texts = transcribe_chunks(model, chunks, output_file="v2t.md")

    # 如果还想最终做一次去重优化
    final_text = merge_texts(texts)

    with open("v2t.md", "w", encoding="utf-8") as f:
        f.write(final_text)

    print("[INFO] 完成，输出 v2t.md")


if __name__ == "__main__":
    main()
