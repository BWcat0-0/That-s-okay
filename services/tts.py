"""
文字转语音（TTS）服务 — P0 阶段为占位模块
后续接入 Edge-TTS（免费）或 OpenAI TTS。

使用方式（后续实现）：
    from services.tts import text_to_speech
    audio_path = text_to_speech("我就吸一根，很快就完了。")
"""


def text_to_speech(text: str, output_path: str = None) -> str:
    """
    将文字转换为语音文件。

    参数:
        text: 要转换的文字内容
        output_path: 输出音频文件路径（可选，默认为临时文件）

    返回:
        str: 生成的音频文件路径

    注意:
        当前为 P0 占位，后续接入 TTS 服务。
        推荐方案：Edge-TTS（免费，无需 API Key）或 OpenAI TTS。
    """
    # TODO: 接入 TTS 服务
    # 方案1 — Edge-TTS（免费，推荐优先尝试）:
    #   import edge_tts
    #   communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    #   await communicate.save(output_path)
    #
    # 方案2 — OpenAI TTS:
    #   from utils.config import get_llm_client
    #   client = get_llm_client()
    #   response = client.audio.speech.create(
    #       model="tts-1",
    #       voice="alloy",
    #       input=text,
    #   )
    #   response.stream_to_file(output_path)

    raise NotImplementedError(
        "文字转语音功能尚未实现。P0阶段请直接显示文字。\n"
        "后续可按需接入 Edge-TTS（免费）或 OpenAI TTS。"
    )
