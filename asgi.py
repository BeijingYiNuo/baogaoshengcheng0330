from pydantic import BaseModel, ConfigDict
from os.path import dirname
import json
from fastapi import FastAPI
from report_generator import generate_interview_data_multi_stage_async

app = FastAPI()


class BaseInfo(BaseModel):
    InterviewTime: str = "0000年00月00日 00:00"
    InterviewFormat: str = "线上"
    InterviewerInfo: str = "面试官姓名"
    ReportCreator: str = "报告编制人"
    ReportCreateDate: str = "0000年00月00日 00:00"
    AppliedPosition: str = "应聘岗位"

    model_config = ConfigDict(extra="allow")


class RequestContent(BaseModel):
    base_info: BaseInfo = BaseInfo()
    template_md: str = open(dirname(__file__) + "/template.md", encoding="utf-8")
    resume_text: str = "Resume Content"
    transcript_text: str = "Transcript Text"
    job_description: str = "Job Description"
    openai_api_key: str = json.load(open(dirname(__file__) + "config.json"))["api_key"]
    openai_base_url: str = json.load(open(dirname(__file__) + "config.json"))[
        "base_url"
    ]
    openai_model: str = json.load(open(dirname(__file__) + "config.json"))[
        "deepseek-chat"
    ]


@app.post("/generate")
async def generate(request_content: RequestContent):
    data = request_content.base_info.model_dump()
    data = await generate_interview_data_multi_stage_async(
        request_content.openai_api_key,
        request_content.openai_base_url,
        request_content.openai_model,
        request_content.template_md,
        request_content.resume_text,
        request_content.transcript_text,
        data,
    )
    
