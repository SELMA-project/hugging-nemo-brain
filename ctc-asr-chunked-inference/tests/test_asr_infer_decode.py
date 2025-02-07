from time import time

import pytest

from ctc_asr_chunked_inference.asr_infer_decode import ASRInferDecoder
from ml4audio.audio_utils.torchaudio_utils import load_resample_with_torch
from ml4audio.text_processing.asr_metrics import calc_cer
from tests.conftest import TestParams


@pytest.mark.parametrize(
    "asr_infer_decoder,max_CER",
    [
        (TestParams(), 0.0),  # WTF! this model reaches 0% CER! overfitted?
        (TestParams(4_000), 0.079),
        (TestParams(4_000, decoder_name="beamsearch"), 0.021),
        (
            TestParams(
                input_sample_rate=4000,
                inferencer_name="nemo-conformer",
                decoder_name="beamsearch",
                lm_weight=0.0,
            ),
            0.029,
        ),
    ],
    indirect=["asr_infer_decoder"],
)
def test_ASRInferDecoder(
    asr_infer_decoder: ASRInferDecoder,
    librispeech_audio_file,
    librispeech_ref,
    max_CER,
):

    expected_sample_rate = asr_infer_decoder.input_sample_rate
    print(f"{asr_infer_decoder.logits_inferencer.letter_vocab=}")
    audio_array = load_resample_with_torch(
        librispeech_audio_file, target_sample_rate=expected_sample_rate
    ).numpy()

    start_time = time()
    transcript = asr_infer_decoder.transcribe_audio_array(audio_array.squeeze())
    inference_duration = time() - start_time
    hyp = transcript.letters.upper()
    # print(smithwaterman_aligned_icdiff(librispeech_ref, hyp))

    cer = calc_cer([librispeech_ref], [hyp])
    decoder_name = asr_infer_decoder.decoder.__class__.__name__
    print(
        f"{asr_infer_decoder.logits_inferencer.name},{decoder_name}\t{cer=}, inference took: {inference_duration} seconds"
    )
    assert cer <= max_CER
