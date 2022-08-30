# pylint: skip-file
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional, Dict

import uvicorn
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.params import File

from data_io.readwrite_files import read_json
from misc_utils.dataclass_utils import (
    decode_dataclass,
    encode_dataclass,
)
from misc_utils.prefix_suffix import BASE_PATHES, PrefixSuffix
from misc_utils.processing_utils import exec_command

from ml4audio.asr_inference.hf_asr_pipeline import (
    HfAsrPipelineFromLogitsInferencerDecoder,
)
from ml4audio.audio_utils.torchaudio_utils import (
    torchaudio_load,
    load_resample_with_torch,
)

DEBUG = os.environ.get("DEBUG", "False").lower() != "false"
if DEBUG:
    print("DEBUGGING MODE")

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.addHandler(logging.StreamHandler())

app = FastAPI(debug=DEBUG)

inferencer: Optional[HfAsrPipelineFromLogitsInferencerDecoder] = None

# if DEBUG:
#     shutil.rmtree("debug_wavs", ignore_errors=True)
#     os.makedirs("debug_wavs")


def userfriendly_inferencer_dict(inferencer):
    return encode_dataclass(
        inferencer,
        skip_keys=[
            "_id_",
            "_target_",
            "finetune_master",
            "cache_base",
            "cache_dir",
            "lm_data",
        ],
    )


@app.post("/transcribe")
async def upload_and_process_audio_file(file: UploadFile):
    global inferencer

    if not file:
        raise HTTPException(status_code=400, detail="Audio bytes expected")

    def save_file(filename, data):
        with open(filename, "wb") as f:
            f.write(data)

    with NamedTemporaryFile(suffix=".wav", delete=True) as tmp_wav, NamedTemporaryFile(
        delete=True
    ) as tmp_original:
        save_file(tmp_original.name, await file.read())

        cmd = f"ffmpeg -i {tmp_original.name} -ar 16000 {tmp_wav.name} -y"
        o, e = exec_command(cmd)

        audio = load_resample_with_torch(
            data_source=tmp_wav.name,
            target_sample_rate=16000,
        )
    prediction = inferencer.predict(audio.numpy())
    return {"filename": file.filename} | prediction


@app.get("/get_inferencer_dataclass")
def get_inferencer_dataclass() -> Dict[str, Any]:
    global inferencer
    if inferencer is not None:
        d = encode_dataclass(inferencer)
    else:
        d = {"response": "no model loaded yet!"}
    return d


@app.get("/model_config")
def get_model_config() -> Dict[str, Any]:
    global inferencer
    if inferencer is not None:
        d = encode_dataclass(
            inferencer,
            skip_keys=[
                "_id_",
                "_target_",
                "finetune_master",
                "cache_base",
                "cache_dir",
                "prefix",
                "use_hash_suffix",
                "lm_data",
            ],
        )
    else:
        d = {"response": "no model loaded yet!"}
    return d


@app.get("/inferencer_config")
def get_model_config() -> Dict[str, Any]:
    global inferencer
    if inferencer is not None:
        d = encode_dataclass(
            inferencer,
            skip_keys=[
                "_id_",
                "_target_",
                # "finetune_master",
                "cache_base",
                "cache_dir",
                "prefix",
                "use_hash_suffix",
                # "lm_data",
            ],
        )
    else:
        d = {"response": "no model loaded yet!"}
    return d


@app.on_event("startup")
async def startup_event():
    global inferencer
    cache_root_in_container = "/model"
    cache_root = os.environ.get("cache_root", cache_root_in_container)
    BASE_PATHES["base_path"] = "/"
    BASE_PATHES["cache_root"] = cache_root
    BASE_PATHES["asr_inference"] = PrefixSuffix("cache_root", "ASR_INFERENCE")
    BASE_PATHES["am_models"] = PrefixSuffix("cache_root", "AM_MODELS")

    p = next(Path(cache_root).rglob("HfAsrPipeline*/dataclass.json"))

    jzon = read_json(str(p))
    inferencer = decode_dataclass(jzon)
    inferencer.build()


if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=2700,
        reload=True if DEBUG else False
        # log_level="debug"
    )
