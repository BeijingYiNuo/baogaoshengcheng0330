# app.py
import streamlit as st
import os
from report_generator import generate_interview_data_multi_stage, fill_docx_template
from voice2text import transcribe_audio_generator
from docx import Document
from io import BytesIO
import pypdf
import json
import datetime
import tempfile

CONFIG_FILE = "config.json"
DEFAULT_TEMPLATE = "processed_template.docx"
REPORTS_DIR = "reports"
TEMP_DIR = "temp_audio"

if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# 检查默认模板是否存在
if not os.path.exists(DEFAULT_TEMPLATE):
    # 如果处理后的模板不存在，尝试从 my_template.docx.docx 重新生成或使用默认的
    if os.path.exists("my_template.docx.docx"):
        st.warning("⚠️ 正在尝试基于您的 my_template.docx.docx 适配系统...")
    else:
        # 自动创建一个简单的基础模板
        doc = Document()
        doc.add_heading('面试评估报告', 0)
        doc.add_paragraph('姓名: {{CandidateName}}')
        doc.add_paragraph('职位: {{TargetPosition}}')
        doc.add_paragraph('结论: {{FinalDecision}}')
        doc.save(DEFAULT_TEMPLATE)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config_dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_dict, f)

# 初始化配置
if 'config' not in st.session_state:
    st.session_state.config = load_config()

if 'last_report' not in st.session_state:
    st.session_state.last_report = None

if 'transcription_text' not in st.session_state:
    st.session_state.transcription_text = ""

if 'last_audio_file' not in st.session_state:
    st.session_state.last_audio_file = None

if 'resume_text_cached' not in st.session_state:
    st.session_state.resume_text_cached = ""

if 'last_resume_file' not in st.session_state:
    st.session_state.last_resume_file = None

if 'transcript_text_cached' not in st.session_state:
    st.session_state.transcript_text_cached = ""

if 'last_transcript_file' not in st.session_state:
    st.session_state.last_transcript_file = None

def extract_text_from_pdf(file):
    pdf_reader = pypdf.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    doc = Document(file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# 设置页面配置
st.set_page_config(page_title="面试报告生成器", layout="wide")

# 侧边栏配置 API
with st.sidebar:
    st.title("⚙️ 配置")
    
    # 获取默认值
    saved_api_key = st.session_state.config.get("api_key", "")
    saved_base_url = st.session_state.config.get("base_url", "https://api.openai.com/v1")
    saved_model = st.session_state.config.get("model", "gpt-4o")
    
    # 输入组件
    api_key = st.text_input("API Key", value=saved_api_key, type="password", placeholder="输入您的 API Key")
    base_url = st.text_input("Base URL", value=saved_base_url)
    
    model_list = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "deepseek-chat", "claude-3-5-sonnet-20240620"]
    try:
        model_index = model_list.index(saved_model)
    except ValueError:
        model_index = 0
    model_name = st.selectbox("选择模型", model_list, index=model_index)
    
    # 保存配置按钮
    if st.button("💾 保存配置 (持久化)"):
        new_config = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model_name
        }
        save_config(new_config)
        st.session_state.config = new_config
        st.success("✅ 配置已保存到本地文件，下次刷新页面不会丢失！")
    
    st.info("💡 提示：保存后配置将存储在本地 config.json 文件中。")
    
    st.divider()
    st.subheader("📁 报告模板")
    custom_template = st.file_uploader("上传自定义 Word 模板 (.docx)", type=["docx"])
    if custom_template:
        with open("custom_template.docx", "wb") as f:
            f.write(custom_template.read())
        st.success("✅ 已切换到自定义模板")
        current_template = "custom_template.docx"
    else:
        current_template = DEFAULT_TEMPLATE
        st.info(f"当前使用: {DEFAULT_TEMPLATE}")

    st.divider()
    st.subheader("📚 历史文档")
    history_files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith(".docx")], reverse=True)
    if history_files:
        for f in history_files:
            # 获取文件修改时间并格式化
            file_path = os.path.join(REPORTS_DIR, f)
            mtime = os.path.getmtime(file_path)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            
            # UI 展示：文件名 + 时间
            col_f, col_d = st.columns([4, 1])
            with col_f:
                st.write(f"**{f}**")
                st.caption(f"🕒 生成时间: {dt_str}")
            with col_d:
                with open(file_path, "rb") as file:
                    st.download_button(
                        label="⬇️",
                        data=file.read(),
                        file_name=f,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"download_{f}"
                    )
            st.divider()
    else:
        st.write("暂无历史文档")

# 主界面
st.title("📝 面试报告自动填充系统")
st.markdown("输入面试全过程语音转换的文字和面试者简历，按照模板自动生成一份完整的面试报告。")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 面试者简历")
    
    # 文件上传逻辑
    uploaded_resume = st.file_uploader("上传简历 (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    
    # 尝试从上传的文件中提取文本
    extracted_text = ""
    if uploaded_resume:
        # 如果是新上传的文件，重新解析
        if st.session_state.last_resume_file != uploaded_resume.name:
            try:
                if uploaded_resume.type == "application/pdf":
                    st.session_state.resume_text_cached = extract_text_from_pdf(uploaded_resume)
                elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    st.session_state.resume_text_cached = extract_text_from_docx(uploaded_resume)
                else: # txt
                    st.session_state.resume_text_cached = uploaded_resume.read().decode("utf-8")
                st.session_state.last_resume_file = uploaded_resume.name
                st.success("✅ 文件解析成功！")
            except Exception as e:
                st.error(f"❌ 文件解析失败: {str(e)}")
        
        extracted_text = st.session_state.resume_text_cached

    # 文本框，如果解析成功则填充，否则允许手动输入
    resume_text = st.text_area(
        "简历内容", 
        value=extracted_text if extracted_text else "", 
        height=300, 
        placeholder="解析后的内容将显示在这里，或者手动粘贴简历内容..."
    )

with col2:
    st.subheader("🎤 面试记录")
    
    # 面试记录文件上传
    uploaded_transcript = st.file_uploader("上传面试记录 (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
    
    # 语音文件上传 (新增)
    uploaded_audio = st.file_uploader("上传面试录音 (MP3/WAV/M4A)", type=["mp3", "wav", "m4a", "flac"])
    
    # 尝试从上传的文件中提取文本
    extracted_transcript = ""
    if uploaded_transcript:
        # 如果是新上传的文件，重新解析
        if st.session_state.last_transcript_file != uploaded_transcript.name:
            try:
                if uploaded_transcript.type == "application/pdf":
                    st.session_state.transcript_text_cached = extract_text_from_pdf(uploaded_transcript)
                elif uploaded_transcript.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    st.session_state.transcript_text_cached = extract_text_from_docx(uploaded_transcript)
                else: # txt
                    st.session_state.transcript_text_cached = uploaded_transcript.read().decode("utf-8")
                st.session_state.last_transcript_file = uploaded_transcript.name
                st.success("✅ 面试记录解析成功！")
            except Exception as e:
                st.error(f"❌ 面试记录解析失败: {str(e)}")
        
        extracted_transcript = st.session_state.transcript_text_cached

    # 语音转文字逻辑 (新增)
    if uploaded_audio:
        # 如果是新上传的文件，清除之前的识别内容
        if st.session_state.last_audio_file != uploaded_audio.name:
            st.session_state.transcription_text = ""
            st.session_state.last_audio_file = uploaded_audio.name

        # 仅当没有识别过，或者用户点击“重新识别”按钮时才运行
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            start_transcribe = st.button("🎙️ 开始语音转文字", type="secondary", use_container_width=True)
        with col_btn2:
            re_transcribe = st.button("🔄 重新识别", type="secondary", use_container_width=True)

        if start_transcribe or (re_transcribe and uploaded_audio):
            with st.status("🎧 正在解析语音并转换为文字...", expanded=True) as status:
                try:
                    # 将上传的文件保存为临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_audio.name.split('.')[-1]}", dir=TEMP_DIR) as tmp_file:
                        # 使用 getvalue() 获取全部内容，避免 read() 指标偏移问题
                        tmp_file.write(uploaded_audio.getvalue())
                        temp_audio_path = tmp_file.name
                    
                    # 创建进度条
                    progress_bar = st.progress(0, text="准备识别...")
                    
                    # 调用转文字生成器
                    all_text_container = st.empty() # 用于动态展示识别出的文字
                    
                    for progress, partial_text in transcribe_audio_generator(temp_audio_path):
                        progress_bar.progress(progress, text=f"识别中: {int(progress*100)}%")
                        # 实时展示完整识别出的文字
                        all_text_container.info(f"🗨️ 已识别文字内容：\n\n{partial_text}")
                        st.session_state.transcription_text = partial_text
                    
                    # 删除临时文件
                    os.unlink(temp_audio_path)
                    status.update(label="✅ 语音转文字成功！", state="complete", expanded=False)
                except Exception as e:
                    status.update(label=f"❌ 语音转文字失败: {str(e)}", state="error")
                    st.error(f"❌ 语音转文字失败: {str(e)}")
        
        # 如果已经有识别结果，将其填充到提取的文本中
        if st.session_state.transcription_text:
            extracted_transcript = st.session_state.transcription_text

    transcript_text = st.text_area(
        "面试记录内容", 
        value=extracted_transcript if extracted_transcript else "", 
        height=300, 
        placeholder="解析后的面试记录将显示在这里，或者手动粘贴面试过程记录..."
    )

# 生成按钮
if st.button("🚀 开始生成报告", type="primary"):
    # 清除上一次的报告状态，避免干扰本次生成
    st.session_state.last_report = None
    
    if not api_key:
        st.error("❌ 请在侧边栏配置 API Key")
    elif not resume_text or not transcript_text:
        st.warning("⚠️ 请输入简历和面试记录内容")
    else:
        with st.spinner("正在进行深度分析并填充模板 (共3个阶段)..."):
            try:
                # 1. 调用 LLM 分阶段生成结构化数据
                interview_data = generate_interview_data_multi_stage(
                    api_key=api_key,
                    base_url=base_url,
                    model=model_name,
                    resume_text=resume_text,
                    transcript_text=transcript_text
                )
                
                # 2. 填充到 Word 模板
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                candidate_name = interview_data.get("CandidateName", "未知候选人")
                output_filename = f"面试报告_{candidate_name}_{timestamp}.docx"
                output_docx_path = os.path.join(REPORTS_DIR, output_filename)
                
                fill_docx_template(current_template, output_docx_path, interview_data)
                
                # 保存到 session_state
                st.session_state.last_report = {
                    "filename": output_filename,
                    "path": output_docx_path
                }
                
                # 强制刷新侧边栏历史列表
                st.rerun()
                    
            except Exception as e:
                st.error(f"❌ 生成报告失败: {str(e)}")

# 显示最新生成的报告下载按钮（如果存在）
if st.session_state.last_report:
    st.divider()
    st.success(f"✅ 深度报告生成成功！已保存至历史文档：{st.session_state.last_report['filename']}")
    
    st.subheader("💾 导出选项")
    with open(st.session_state.last_report['path'], "rb") as f:
        st.download_button(
            label="下载本次生成的 Word 报告",
            data=f.read(),
            file_name=st.session_state.last_report['filename'],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="main_download_btn"
        )

# 页脚
st.divider()
st.caption("© 2026 面试评估系统 - 基于 LLM 构建")
