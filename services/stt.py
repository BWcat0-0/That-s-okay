"""
语音转文字（STT）服务 — P0 阶段为占位模块
后续接入 OpenAI Whisper API 或国内语音识别方案。

使用方式（后续实现）：
    from services.stt import speech_to_text
    text = speech_to_text("path/to/audio.wav")
"""


def speech_to_text(audio_file_path: str) -> str:
    """
    将音频文件转换为文字。

    参数:
        audio_file_path: 音频文件路径（支持 wav/mp3/m4a 等格式）

    返回:
        str: 识别出的文字内容

    注意:
        当前为 P0 占位，后续接入 STT 服务。
    """
    # TODO: 接入 OpenAI Whisper API 或国内兼容方案
    # 示例实现（需要时取消注释）:
    # from utils.config import get_llm_client
    # client = get_llm_client()
    # with open(audio_file_path, "rb") as f:
    #     transcript = client.audio.transcriptions.create(
    #         model="whisper-1",
    #         file=f,
    #     )
    # return transcript.text

    raise NotImplementedError(
        "语音转文字功能尚未实现。P0阶段请使用文字输入。\n"
        "后续可按需接入 OpenAI Whisper API 或国内方案。"
    )
