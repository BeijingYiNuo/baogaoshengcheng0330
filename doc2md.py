import pypandoc
from openai import OpenAI, AsyncOpenAI
from typing import AsyncGenerator
import re
from tqdm import tqdm


def pandoc_process(doc_file_path: str = "template.docx") -> str:
    return pypandoc.convert_file(doc_file_path, "md")


PROCESS_PROMPT = """
你是一个文档格式修复助手。

请你：
1. 修复 Markdown 格式（标题、列表、表格等）
2. 保持原始内容不丢失
3. 提高可读性
4. 不要添加额外解释
5. 对于`{{A:B}}`形式的内容，B部分不要丢掉

原始内容：
{raw_md}
"""


def llm_process(doc_md: str, config: dict[str, str], progress: bool = True) -> str:
    """
    同步接口，但内部使用流式拼接
    """

    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    stream = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "你是一个专业的Markdown整理助手"},
            {"role": "user", "content": PROCESS_PROMPT.format(raw_md=doc_md)},
        ],
        temperature=0.3,
        stream=True,
    )

    result = []
    total_estimate = int(len(doc_md) * 0.6)  # 用输入长度估算

    pbar = tqdm(total=total_estimate, disable=not progress, desc="LLM Processing",leave=False)

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            result.append(text)
            tqdm.write(text, end="")
            
            # 用输出长度推进（粗略估计）
            pbar.update(len(text))

    pbar.close()

    return "".join(result)


async def llm_process_stream(
    doc_md: str, config: dict[str, str], progress: bool = False
) -> AsyncGenerator[str, None]:
    """
    真正的流式接口（可选带进度）
    """

    client = AsyncOpenAI(api_key=config["api_key"], base_url=config["base_url"])

    stream = await client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": "你是一个专业的Markdown整理助手"},
            {
                "role": "user",
                "content": PROCESS_PROMPT.format(raw_md=doc_md),
            },
        ],
        temperature=0.3,
        stream=True,
    )

    total_estimate = len(doc_md)
    pbar = tqdm(total=total_estimate, disable=not progress, desc="Streaming")

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content

            if progress:
                pbar.update(len(text))

            yield text

    if progress:
        pbar.close()


def split_md(md: str) -> list[str]:

    matches = list(re.finditer(r"^## .+", md, flags=re.MULTILINE))

    if not matches:
        return [md]

    result = []

    first_start = matches[0].start()
    if first_start > 0:
        result.append(md[:first_start].strip())

    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        result.append(md[start:end].strip())

    return result


def get_splited_md(path: str = "template.md") -> list[str]:
    with open(path, encoding="utf-8") as f:
        return split_md(f.read())


if __name__ == "__main__":
    import json

    open("template.md", "w", encoding="utf-8").write(
        llm_process(pandoc_process(), json.load(open("config.json")))
    )
    json.dump(
        split_md(open("template.md", "r", encoding="utf-8").read()),
        open("template.json", "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=4,
    )
