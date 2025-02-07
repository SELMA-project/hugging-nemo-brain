import os
import shutil

import kenlm
import numpy as np
import pytest
from pyctcdecode import BeamSearchDecoderCTC, Alphabet, LanguageModel
from pyctcdecode.constants import (
    DEFAULT_BEAM_WIDTH,
    DEFAULT_PRUNE_LOGP,
    DEFAULT_MIN_TOKEN_LOGP,
    DEFAULT_PRUNE_BEAMS,
    DEFAULT_HOTWORD_WEIGHT,
)
from pyctcdecode.language_model import HotwordScorer

from conftest import (
    TEST_RESOURCES,
    load_hfwav2vec2_base_tokenizer,
)
from ctc_decoding.huggingface_ctc_decoding import VocabFromHFTokenizer
from ctc_decoding.lm_model_for_pyctcdecode import (
    GzippedArpaAndUnigramsForPyCTCDecode,
    KenLMBinaryUnigramsFromArpa,
)
from ctc_decoding.pyctc_decoder import PyCTCKenLMDecoder, OutputBeamDc
from data_io.readwrite_files import read_lines
from misc_utils.buildable import BuildableList
from misc_utils.prefix_suffix import PrefixSuffix
from ml4audio.audio_utils.test_utils import get_test_vocab
from ml4audio.text_processing.asr_metrics import calc_cer
from ml4audio.text_processing.asr_text_cleaning import (
    Casing,
    VocabCasingAwareTextCleaner,
)
from ml4audio.text_processing.kenlm_arpa import ArpaBuilder, ArpaArgs, AnArpaFile
from ml4audio.text_processing.word_based_text_corpus import (
    WordBasedLMCorpus,
    RglobRawCorpus,
)

TARGET_SAMPLE_RATE = 16000

# TODO: this is very ugly
cache_base = PrefixSuffix("pwd", "test_cache")
shutil.rmtree(str(cache_base), ignore_errors=True)
os.makedirs(str(cache_base))

tn = VocabCasingAwareTextCleaner(
    casing=Casing.upper, text_cleaner_name="en", letter_vocab=get_test_vocab()
)


def _get_test_arpa_unigrams():
    return GzippedArpaAndUnigramsForPyCTCDecode(
        cache_base=cache_base,
        raw_arpa=AnArpaFile(arpa_filepath=f"{TEST_RESOURCES}/lm.arpa"),
        transcript_cleaner=tn,
    )


@pytest.mark.parametrize(
    "ngram_lm_model,max_cer",
    [
        (
            KenLMBinaryUnigramsFromArpa(
                cache_base=cache_base,
                arpa_unigrams=_get_test_arpa_unigrams(),
            ),
            0.0053,
        ),
        (
            _get_test_arpa_unigrams(),
            0.0053,
        ),
        (
            GzippedArpaAndUnigramsForPyCTCDecode(
                cache_base=cache_base,
                transcript_cleaner=tn,
                raw_arpa=ArpaBuilder(
                    cache_base=cache_base,
                    arpa_args=ArpaArgs(
                        order=5,
                        prune="|".join(str(k) for k in [0, 8, 16]),
                    ),
                    corpus=WordBasedLMCorpus(
                        name="test-corpus",
                        cache_base=cache_base,
                        raw_corpora=BuildableList[RglobRawCorpus](
                            [
                                RglobRawCorpus(
                                    cache_base=cache_base,
                                    corpus_dir=TEST_RESOURCES,
                                    file_pattern="test_corpus.txt",
                                )
                            ]
                        ),
                        transcript_cleaner=tn,
                    ),
                ),
            ),
            0.0027,
        ),
    ],
)
def test_PyCTCKenLMDecoder(
    hfwav2vec2_base_tokenizer,
    ngram_lm_model: GzippedArpaAndUnigramsForPyCTCDecode,
    max_cer: float,
    librispeech_logtis_file,
    librispeech_ref,
):

    logits = np.load(librispeech_logtis_file, allow_pickle=True)

    decoder = PyCTCKenLMDecoder(
        vocab=VocabFromHFTokenizer("facebook/wav2vec2-base-960h"),
        lm_weight=1.0,
        beta=0.5,
        ngram_lm_model=ngram_lm_model,
    )
    decoder.build()
    transcript = decoder.ctc_decode(logits.squeeze())[0]
    cer = calc_cer([librispeech_ref], [transcript.text])
    print(f"{ngram_lm_model.name}\t{cer=}")
    assert cer < max_cer


lm_data = _get_test_arpa_unigrams().build()
unigrams = list(read_lines(lm_data.unigrams_filepath))


@pytest.mark.parametrize(
    "decoder",
    [
        (
            BeamSearchDecoderCTC(
                Alphabet.build_alphabet(
                    list(load_hfwav2vec2_base_tokenizer().get_vocab().keys())
                ),
                language_model=LanguageModel(
                    kenlm_model=kenlm.Model(lm_data.ngramlm_filepath),
                    unigrams=unigrams,
                    alpha=1.0,
                    beta=0.5,
                    # unk_score_offset=unk_score_offset,
                    # score_boundary=lm_score_boundary,
                ),
            )
        ),
    ],
)
def test_beams_search_decoders(
    decoder: BeamSearchDecoderCTC,
    librispeech_logtis_file,
    librispeech_ref,
):
    max_cer = 0.007

    logits = np.load(librispeech_logtis_file, allow_pickle=True)
    beams = decoder._decode_logits(
        logits=logits.squeeze(),
        beam_width=DEFAULT_BEAM_WIDTH,
        beam_prune_logp=DEFAULT_PRUNE_LOGP,
        token_min_logp=DEFAULT_MIN_TOKEN_LOGP,
        prune_history=DEFAULT_PRUNE_BEAMS,
        hotword_scorer=HotwordScorer.build_scorer(
            hotwords=None, weight=DEFAULT_HOTWORD_WEIGHT
        ),
        lm_start_state=None,
    )
    beams = [OutputBeamDc(*b) for b in beams]

    ref = librispeech_ref
    hyp = beams[0].text
    # print(smithwaterman_aligned_icdiff(ref, hyp))
    cer = calc_cer([ref], [hyp])
    print(f"BeamSearchDecoderCTC\t{cer=}")
    assert cer < max_cer
