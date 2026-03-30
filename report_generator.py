# report_generator.py
import os
import json
import concurrent.futures
from openai import OpenAI
from prompts import PROMPT_SYSTEM, ATTENTION_PROMPT
from doc2md import get_splited_md
from dotenv import load_dotenv
from docx import Document
import re

load_dotenv()


def get_grade(score):
    if score >= 90:
        return "优秀"
    elif score >= 80:
        return "良好"
    elif score >= 70:
        return "合格"
    else:
        return "不合格"


def score_postprocess(all_data: dict[str, str | float]):
    score_dim = dict[str, float]()
    level_dim = dict[str, str]()
    for key, value in all_data.items():
        if key.startswith("Score_AI_"):
            value = float(value)
            dim_name = key.replace("Score_AI_", "")
            score_dim[dim_name] = value
            level_dim[dim_name] = get_grade(value)
            all_data["Score_Level_" + dim_name] = level_dim[dim_name]
    all_data["Score_TotalAvg"] = round(sum(score_dim.values()) / len(score_dim), 1)
    all_data["Score_Comparision"] = (
        "高于" if all_data["Score_TotalAvg"] > 70 else "低于"
    )


def generate_interview_data_multi_stage(
    api_key, base_url, model, resume_text, transcript_text
):
    """
    并行调用 LLM 生成面试数据，基于不同的 Prompt 模板。
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    all_data = {}

    # 需要并行生成的模板列表
    templates = get_splited_md()

    def fetch_data_from_llm(idx, template_content):
        # 使用 replace 替换占位符，避免 format 带来的 {{}} 转义问题
        prompt = (
            PROMPT_SYSTEM.replace("{TEMPLATE}", template_content)
            .replace("{RESUME}", resume_text)
            .replace("{VOICE2TEXT}", transcript_text)
            .replace("{ATTENTION}", ATTENTION_PROMPT)
        )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"{idx} 生成失败: {str(e)}")

    # 使用线程池并行执行
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_template = {
            executor.submit(fetch_data_from_llm, idx, content): idx
            for idx, content in enumerate(templates)
        }

        for future in concurrent.futures.as_completed(future_to_template):
            idx = future_to_template[future]
            try:
                data = future.result()
                all_data.update(data)
            except Exception as e:
                raise Exception(f"并行生成中出错 ({idx}): {str(e)}")
    score_postprocess(all_data)

    return all_data


def fill_docx_template(template_path, output_path, data: dict[str, str | float]):
    doc = Document(template_path)

    def replace_in_paragraph(paragraph):
        text = paragraph.text
        if not text:
            return

        # 快速判断是否可能包含占位符
        if "{{" not in text and "[[" not in text:
            return

        # 遍历每个 key
        for key, value in data.items():
            if str(value).endswith("。"):
                value = str(value)[:-1]
            pattern = re.compile(
                r"\{\{"
                + re.escape(key)
                + r"(?:\:.*?)?\}\}|\[\["
                + re.escape(key)
                + r"(?:\:.*?)?\]\]"
            )
            if not pattern.search(paragraph.text):
                continue

            runs = list(paragraph.runs)
            if not runs:
                continue

            # 构建全文 + run 映射
            full_text = ""
            run_info = []

            for run in runs:
                start_idx = len(full_text)
                full_text += run.text
                end_idx = len(full_text)
                run_info.append((start_idx, end_idx, run))

            # 循环处理该 key 的所有匹配（可能多个）
            while True:
                match = pattern.search(full_text)
                if not match:
                    break

                placeholder_pos = match.start()
                placeholder_end = match.end()

                # 找到涉及的 runs
                affected_runs = []
                for start_idx, end_idx, run in run_info:
                    if (
                        start_idx <= placeholder_pos < end_idx
                        or start_idx < placeholder_end <= end_idx
                        or placeholder_pos <= start_idx < placeholder_end
                    ):
                        affected_runs.append((start_idx, end_idx, run))

                if not affected_runs:
                    break

                # ===== 情况1：单 Run =====
                if len(affected_runs) == 1:
                    start_idx, end_idx, run = affected_runs[0]

                    run_local_start = placeholder_pos - start_idx
                    run_local_end = placeholder_end - start_idx

                    # 保存格式
                    is_bold = run.bold
                    font_size = run.font.size
                    font_name = run.font.name
                    font_color = (
                        run.font.color.rgb
                        if run.font.color and run.font.color.rgb
                        else None
                    )

                    # 替换
                    run_text = run.text
                    new_run_text = (
                        run_text[:run_local_start]
                        + str(value)
                        + run_text[run_local_end:]
                    )
                    run.text = new_run_text

                    # 恢复格式
                    if is_bold is not None:
                        run.bold = is_bold
                    if font_size:
                        run.font.size = font_size
                    if font_name:
                        run.font.name = font_name
                    if font_color:
                        run.font.color.rgb = font_color

                # ===== 情况2：跨 Run =====
                else:
                    first_start, first_end, first_run = affected_runs[0]
                    last_start, last_end, last_run = affected_runs[-1]

                    first_run_local_start = placeholder_pos - first_start
                    last_run_local_end = placeholder_end - last_start

                    # 保存格式（用第一个 run）
                    is_bold = first_run.bold
                    font_size = first_run.font.size
                    font_name = first_run.font.name
                    font_color = (
                        first_run.font.color.rgb
                        if first_run.font.color and first_run.font.color.rgb
                        else None
                    )

                    first_text = first_run.text
                    last_text = last_run.text

                    new_text = (
                        first_text[:first_run_local_start]
                        + str(value)
                        + last_text[last_run_local_end:]
                    )

                    # 清空所有 run
                    for _, _, run in affected_runs:
                        run.text = ""

                    # 写回第一个 run
                    first_run.text = new_text

                    if is_bold is not None:
                        first_run.bold = is_bold
                    if font_size:
                        first_run.font.size = font_size
                    if font_name:
                        first_run.font.name = font_name
                    if font_color:
                        first_run.font.color.rgb = font_color

                # 重新构建 full_text（因为内容变了）
                full_text = ""
                run_info = []
                for run in runs:
                    start_idx = len(full_text)
                    full_text += run.text
                    end_idx = len(full_text)
                    run_info.append((start_idx, end_idx, run))

    # ===== 处理正文 =====
    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph)

    # ===== 处理表格 =====
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph)

    doc.save(output_path)
    return output_path
