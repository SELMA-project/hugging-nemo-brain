from time import time

import icdiff
import pytest

from ctc_asr_chunked_inference.hfwav2vec2_asr_decode_inferencer import (
    HFASRDecodeInferencer,
)
from ml4audio.audio_utils.audio_io import load_and_resample_16bit_PCM
from ml4audio.text_processing.asr_metrics import calc_cer


@pytest.mark.parametrize(
    "asr_decode_inferencer,max_CER",
    [
        (16_000, 0.0),  # WTF! this model reaches 0% CER! overfitted?
        (8_000, 0.0033),
        (4_000, 0.091),
    ],
    indirect=["asr_decode_inferencer"],
)
def test_HFASRDecodeInferencer(
    asr_decode_inferencer: HFASRDecodeInferencer,
    librispeech_audio_file,
    librispeech_raw_ref,
    max_CER,
):
    """
    TODO: how much sense do these tests that depend on external data make?
        -> model gets downloaded from hf-hub
    """

    expected_sample_rate = asr_decode_inferencer.input_sample_rate
    audio_array = load_and_resample_16bit_PCM(
        librispeech_audio_file, expected_sample_rate
    )
    # timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # soundfile.write(f"audio-{timestamp}.wav", audio_array, 16000)
    # logits=wav2vec2_base_greedy.logits_inferencer.resample_calc_logits(audio_array.squeeze())
    # logits_file = f"logits.npy"
    # np.save(logits_file, logits)
    # target_dictionary = wav2vec2_base_greedy.logits_inferencer.vocab
    # write_lines("vocab.txt",target_dictionary)

    start_time = time()
    transcript = asr_decode_inferencer.transcribe_audio_array(audio_array.squeeze())
    inference_duration = time() - start_time
    hyp = transcript.letters
    cd = icdiff.ConsoleDiff(cols=120)
    diff_line = "\n".join(
        cd.make_table(
            [librispeech_raw_ref],
            [hyp],
            "ref",
            "hyp",
        )
    )
    print(diff_line)
    cer = calc_cer([(hyp, librispeech_raw_ref)])
    print(f"CER: {cer}, inference took: {inference_duration} seconds")
    assert cer <= max_CER
