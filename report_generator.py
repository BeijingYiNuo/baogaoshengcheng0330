# report_generator.py
import os
import json
import concurrent.futures
from openai import OpenAI
from prompts import (
    PROMPT_SYSTEM, PROMPT_COVER, PROMPT_BASIC_INFO, 
    PROMPT_CORE_SCORE, PROMPT_CORE_BILITY, 
    PROMPT_COMPREHENSIVE_ANALYSIS, PROMPT_CONCLUSION
)
from dotenv import load_dotenv
from docx import Document

load_dotenv()

def generate_interview_data_multi_stage(api_key, base_url, model, resume_text, transcript_text):
    """
    并行调用 LLM 生成面试数据，基于不同的 Prompt 模板。
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    all_data = {}
    
    # 需要并行生成的模板列表
    templates = [
        ("封面信息", PROMPT_COVER),
        ("基本信息", PROMPT_BASIC_INFO),
        ("核心打分", PROMPT_CORE_SCORE),
        ("核心能力", PROMPT_CORE_BILITY),
        ("综合分析", PROMPT_COMPREHENSIVE_ANALYSIS),
        ("面试结论", PROMPT_CONCLUSION)
    ]
    
    def fetch_data_from_llm(template_name, template_content):
        # 使用 replace 替换占位符，避免 format 带来的 {{}} 转义问题
        prompt = PROMPT_SYSTEM.replace("{TEMPLATE}", template_content)\
                              .replace("{RESUME}", resume_text)\
                              .replace("{VOICE2TEXT}", transcript_text)
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={ "type": "json_object" }
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise Exception(f"{template_name} 生成失败: {str(e)}")

    # 使用线程池并行执行
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_template = {
            executor.submit(fetch_data_from_llm, name, content): name 
            for name, content in templates
        }
        
        for future in concurrent.futures.as_completed(future_to_template):
            name = future_to_template[future]
            try:
                data = future.result()
                all_data.update(data)
            except Exception as e:
                raise Exception(f"并行生成中出错 ({name}): {str(e)}")
    
    # 后处理计算平均分和等级
    dimensions = ["Putonghua", "Liuchang", "Luoji", "Sales", "Stress", "Comm", "Stability"]
    met_count = 0
    unmet_count = 0
    basic_comm_met_count = 0
    
    for dim in dimensions:
        s1 = all_data.get(f"Score_{dim}_Interviewer", 0)
        s2 = all_data.get(f"Score_{dim}_AI", 0)
        
        # 确保分数为数值
        try:
            s1 = float(s1)
            s2 = float(s2)
        except:
            s1, s2 = 0.0, 0.0
            
        avg = round((s1 + s2) / 2, 1)
        all_data[f"Score_{dim}_Avg"] = avg
        
        # 判定达标情况 (基准线 70)
        if avg >= 70:
            met_count += 1
            if dim in ["Putonghua", "Liuchang", "Luoji"]:
                basic_comm_met_count += 1
            grade = "合格" if avg < 80 else ("良好" if avg < 90 else "优秀")
        else:
            unmet_count += 1
            grade = "不合格"
            
        all_data[f"Grade_{dim}"] = grade

    # 强制修正达标统计数据，确保逻辑严密
    all_data["MetCount"] = met_count
    all_data["UnmetCount"] = unmet_count
    all_data["BasicCommStatus"] = f"{basic_comm_met_count}个维度均达标" if basic_comm_met_count == 3 else f"仅{basic_comm_met_count}个维度达标"
            
    return all_data

def fill_docx_template(template_path, output_path, data):
    """
    使用 python-docx 替换模板中的占位符 {{Key}}。
    鲁棒的替换函数，支持跨Run占位符且保留格式。
    """
    doc = Document(template_path)
    
    def replace_in_paragraph(paragraph):
        """
        在段落中精确替换占位符，保留格式。
        处理占位符可能被拆分到多个Run中的情况。
        """
        # 检查段落中是否有需要替换的占位符
        has_placeholder = False
        for key in data.keys():
            if f"{{{{{key}}}}}" in paragraph.text:
                has_placeholder = True
                break
        
        if not has_placeholder:
            return
        
        # 对于每个占位符，进行精确替换
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            
            # 如果占位符不在段落中，跳过
            if placeholder not in paragraph.text:
                continue
            
            # 获取段落的所有Run
            runs = list(paragraph.runs)
            if not runs:
                continue
            
            # 构建段落完整文本和Run的映射
            full_text = ""
            run_info = []  # 每个Run的(start_idx, end_idx, run_object)
            
            for run in runs:
                start_idx = len(full_text)
                full_text += run.text
                end_idx = len(full_text)
                run_info.append((start_idx, end_idx, run))
            
            # 在完整文本中查找占位符
            placeholder_pos = full_text.find(placeholder)
            if placeholder_pos == -1:
                continue
            
            placeholder_end = placeholder_pos + len(placeholder)
            
            # 找到占位符覆盖的Run
            affected_runs = []
            for start_idx, end_idx, run in run_info:
                # 检查Run是否与占位符有重叠
                if (start_idx <= placeholder_pos < end_idx or 
                    start_idx < placeholder_end <= end_idx or
                    placeholder_pos <= start_idx < placeholder_end):
                    affected_runs.append((start_idx, end_idx, run))
            
            if not affected_runs:
                continue
            
            # 情况1：占位符完全在一个Run中
            if len(affected_runs) == 1:
                start_idx, end_idx, run = affected_runs[0]
                # 计算在Run内的相对位置
                run_local_start = placeholder_pos - start_idx
                run_local_end = run_local_start + len(placeholder)
                
                # 保存Run的格式
                is_bold = run.bold
                font_size = run.font.size
                font_name = run.font.name
                font_color = run.font.color.rgb if run.font.color and run.font.color.rgb else None
                
                # 替换Run中的占位符部分
                run_text = run.text
                new_run_text = run_text[:run_local_start] + str(value) + run_text[run_local_end:]
                run.text = new_run_text
                
                # 恢复Run的格式
                if is_bold is not None:
                    run.bold = is_bold
                if font_size:
                    run.font.size = font_size
                if font_name:
                    run.font.name = font_name
                if font_color:
                    run.font.color.rgb = font_color
            
            # 情况2：占位符跨多个Run
            else:
                # 找到第一个和最后一个受影响的Run
                first_start, first_end, first_run = affected_runs[0]
                last_start, last_end, last_run = affected_runs[-1]
                
                # 计算在第一个Run中的起始位置
                first_run_local_start = placeholder_pos - first_start
                
                # 计算在最后一个Run中的结束位置
                last_run_local_end = placeholder_end - last_start
                
                # 保存第一个Run的格式（用于新文本）
                is_bold = first_run.bold
                font_size = first_run.font.size
                font_name = first_run.font.name
                font_color = first_run.font.color.rgb if first_run.font.color and run.font.color.rgb else None
                
                # 构建新文本：第一个Run中占位符前的部分 + 替换值 + 最后一个Run中占位符后的部分
                first_run_text = first_run.text
                last_run_text = last_run.text
                
                new_text = first_run_text[:first_run_local_start] + str(value) + last_run_text[last_run_local_end:]
                
                # 清空所有受影响的Run
                for _, _, run in affected_runs:
                    run.text = ""
                
                # 将新文本放入第一个Run，并恢复格式
                first_run.text = new_text
                if is_bold is not None:
                    first_run.bold = is_bold
                if font_size:
                    first_run.font.size = font_size
                if font_name:
                    first_run.font.name = font_name
                if font_color:
                    first_run.font.color.rgb = font_color
    
    # 替换正文段落
    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph)
                
    # 替换表格中的占位符
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph)
                            
    doc.save(output_path)
    return output_path
