from pydantic import BaseModel, ConfigDict
from os.path import dirname
import tempfile
import os
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from report_generator import (
    generate_interview_data_multi_stage_async,
    fill_docx_template,
)
from state_mgr import SimpleStateManager
import base64
from typing import Literal, Any, Union
from doc2md import llm_process, llm_process_stream, pandoc_process

ssm = SimpleStateManager("./reports")
app = FastAPI()
app.mount("/static", StaticFiles(directory=dirname(__file__)), name="static")


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
    template_docx_b64: str = base64.b64encode(
        open(dirname(__file__) + "/template.docx", "rb").read()
    ).decode()
    template_md: str = open(dirname(__file__) + "/template.md", encoding="utf-8").read()
    resume_text: str = open(dirname(__file__)+"/example_contents/resume.md",encoding="utf-8").read()
    transcript_text: str = open(dirname(__file__)+"/example_contents/transcript.md",encoding="utf-8").read()
    job_description: str = open(dirname(__file__)+"/example_contents/jd.md",encoding="utf-8").read()
    openai_api_key: str = json.load(open(dirname(__file__) + "/config.json"))["api_key"]
    openai_base_url: str = json.load(open(dirname(__file__) + "/config.json"))[
        "base_url"
    ]
    openai_model: str = json.load(open(dirname(__file__) + "/config.json"))["model"]
    request_type: Literal["json", "docx"] = "docx"


class Doc2MDRequest(BaseModel):
    template_docx_b64: str = base64.b64encode(
        open(dirname(__file__) + "/template.docx", "rb").read()
    ).decode()
    openai_api_key: str = json.load(open(dirname(__file__) + "/config.json"))["api_key"]
    openai_base_url: str = json.load(open(dirname(__file__) + "/config.json"))[
        "base_url"
    ]
    openai_model: str = json.load(open(dirname(__file__) + "/config.json"))["model"]


class GenerateJSONResponse(BaseModel):
    idx: int
    data: dict[str, Any]


@app.post("/doc2md")
async def doc2md_(request_content: Doc2MDRequest):
    try:
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        open(path, "wb").write(base64.b64decode(request_content.template_docx_b64))
        pan_md = pandoc_process(path)
        return Response(
            llm_process(
                pan_md,
                config={
                    "api_key": request_content.openai_api_key,
                    "base_url": request_content.openai_base_url,
                    "model": request_content.openai_model,
                },
                progress=False,
            ),
            media_type="text/markdown",
        )
    finally:
        os.remove(path)


@app.post("/doc2md/stream")
async def doc2md_stream(request_content: Doc2MDRequest):

    async def event_generator():
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)

        with open(path, "wb") as f:
            f.write(base64.b64decode(request_content.template_docx_b64))

        try:
            pan_md = pandoc_process(path)

            async for chunk in llm_process_stream(
                pan_md,
                config={
                    "api_key": request_content.openai_api_key,
                    "base_url": request_content.openai_base_url,
                    "model": request_content.openai_model,
                },
            ):
                yield f"data: {chunk}\n\n"

            yield "event: end\ndata: [DONE]\n\n"

        finally:
            os.remove(path)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@app.get("/state/list")
def state_list():
    return JSONResponse(ssm.list_files())

@app.get("/state/{idx}")
def state_info(idx:int):
    return JSONResponse(ssm.state_container[idx])

@app.post(
    "/generate",
    response_model=Union[GenerateJSONResponse, None],
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "idx": 1,
                        "data": BaseInfo().model_dump(),
                    }
                },
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "schema": {"type": "string", "format": "binary"}
                },
            },
            "description": "返回 JSON 或 DOCX 文件",
        }
    },
)
async def generate_docx(request_content: RequestContent):
    data = request_content.base_info.model_dump()
    info = await generate_interview_data_multi_stage_async(
        request_content.openai_api_key,
        request_content.openai_base_url,
        request_content.openai_model,
        request_content.template_md,
        request_content.resume_text,
        request_content.transcript_text,
        data,
        ssm,
    )
    template_docx_file_path = (
        tempfile.gettempdir() + "/" + info.filename(".template.docx")
    )
    open(template_docx_file_path, "wb").write(
        base64.b64decode(request_content.template_docx_b64)
    )
    fill_docx_template(
        template_docx_file_path, ssm.report_path + "/" + info.filename(), data
    )
    if request_content.request_type == "docx":
        return FileResponse(
            path=ssm.report_path + "/" + info.filename(),
            filename=info.filename(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    elif request_content.request_type == "json":
        return GenerateJSONResponse(idx=info.idx, data=data)
