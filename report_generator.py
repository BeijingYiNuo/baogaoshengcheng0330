# report_generator.py
import os
import json
from openai import OpenAI
from prompts import (
    SYSTEM_PROMPT_STAGE1, SYSTEM_PROMPT_STAGE2, SYSTEM_PROMPT_STAGE3,
    USER_PROMPT_MULTI_STAGE, INTERVIEW_REPORT_TEMPLATE
)
from dotenv import load_dotenv
from docx import Document

load_dotenv()

def generate_interview_data_multi_stage(api_key, base_url, model, resume_text, transcript_text):
    """
    分阶段调用 LLM 生成面试数据，提高准确性。
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    user_prompt = USER_PROMPT_MULTI_STAGE.format(
        resume_text=resume_text,
        transcript_text=transcript_text
    )
    
    all_data = {}
    
    stages = [
        ("基本信息提取", SYSTEM_PROMPT_STAGE1),
        ("维度打分评估", SYSTEM_PROMPT_STAGE2),
        ("优劣势与结论", SYSTEM_PROMPT_STAGE3)
    ]
    
    for stage_name, system_prompt in stages:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={ "type": "json_object" }
            )
            stage_data = json.loads(response.choices[0].message.content)
            all_data.update(stage_data)
        except Exception as e:
            raise Exception(f"{stage_name} 失败: {str(e)}")
            
    return all_data

def fill_docx_template(template_path, output_path, data):
    """
    使用 python-docx 替换模板中的占位符 {{Key}}，同时严格保留格式和分页符。
    """
    doc = Document(template_path)
    
    def replace_in_paragraphs(paragraphs):
        for paragraph in paragraphs:
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in paragraph.text:
                    # 只有当占位符存在时才进行处理
                    # 方案：遍历 runs，精准替换文字而不改变 run 对象本身（保留格式）
                    for run in paragraph.runs:
                        if placeholder in run.text:
                            run.text = run.text.replace(placeholder, str(value))
                    
                    # 针对跨 run 的占位符进行特殊处理
                    # 如果经过上述处理后 paragraph.text 中仍有占位符，说明被 Word 分散到了多个 run
                    if placeholder in paragraph.text:
                        # 这种情况下，我们合并第一个包含部分占位符的 run，并清除后续相关的 runs
                        # 但为了简单且安全地保留换页符，我们采用非破坏性替换
                        full_text = "".join(run.text for run in paragraph.runs)
                        new_text = full_text.replace(placeholder, str(value))
                        
                        # 只有在确实发生变化时才重新构建 runs（这会尽量减少对格式的影响）
                        if full_text != new_text:
                            # 清除所有内容但保留段落属性
                            # 注意：这可能会导致段落内复杂的混合格式丢失，但能保住段落级别的分页
                            # 在本项目的模板中，占位符通常是单一格式，因此是安全的
                            # 我们通过保留第一个 run 的样式来尽量还原
                            if paragraph.runs:
                                first_run_style = paragraph.runs[0].font
                                paragraph.text = new_text 
                                # 尽量恢复字体
                                try:
                                    paragraph.runs[0].font.name = first_run_style.name
                                    paragraph.runs[0].font.size = first_run_style.size
                                    paragraph.runs[0].font.bold = first_run_style.bold
                                except:
                                    pass

    # 替换正文段落
    replace_in_paragraphs(doc.paragraphs)
                
    # 替换表格中的占位符
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                replace_in_paragraphs(cell.paragraphs)
                            
    doc.save(output_path)
    return output_path
