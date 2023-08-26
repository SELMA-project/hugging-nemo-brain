from abc import abstractmethod
from dataclasses import dataclass
from typing import Union, Annotated, ClassVar

import torch
from beartype import beartype
from beartype.vale import IsAttr, IsEqual
from misc_utils.beartypes import (
    NumpyFloat1DArray,
    NeList,
    NeStr,
    TorchTensor2D,
)
from misc_utils.buildable import Buildable
from misc_utils.dataclass_utils import (
    UNDEFINED,
)
from numpy import floating, int16
from numpy.typing import NDArray
from transformers import (
    set_seed,
)

from ml4audio.text_processing.asr_text_normalization import Casing

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NumpyFloatORInt16_1DArray = Annotated[
    Union[NDArray[floating], NDArray[int16]], IsAttr["ndim", IsEqual[1]]
]

set_seed(42)


def determine_casing(vocab: list[str]) -> Casing:
    more_than_half_is_upper = (
        sum([1 if c.upper() == c else 0 for c in vocab]) > len(vocab) / 2
    )
    casing = Casing.upper if more_than_half_is_upper else Casing.lower
    return casing


@dataclass
class ASRLogitsInferencer(Buildable):
    """
        Asr Connectionis temporal classification (CTC) Logits Inference

    ──────────────────────────────────────────────
    ──────│─────│───────│─────│───────│────────│──
    ──────│─────│───────│─────│───────│────────│──
    ──────│──┌───┬────┬───┐──┌┐───────│┌┐──────│──
    ──────│──│┌─┐│┌┐┌┐│┌─┐│──││───────┌┘└┐─────│──
    ──────│──││─└┴┘││└┤││└┘──││┌──┬──┬┼┐┌┼──┐──│──
    ──────│──││─┌┐─││─│││┌┬──┤││┌┐│┌┐├┤│││──┤──│──
    ──────│──│└─┘│─││─│└─┘├──┤└┤└┘│└┘│││└┼──│──│──
    ──────│──└───┘─└┘─└───┘──└─┴──┴─┐├┘└─┴──┘──│──
    ──────│─────│───────│─────│───┌─┘││────────│──
    ──────│─────│───────│─────│───└──┘│────────│──
    ──────│─────│───────│─────│───────│────────│──
    ──────│─────│───────│─────│───────│────────│──

    """

    asr_model_sample_rate: ClassVar[int] = 16000

    @property
    @beartype
    def name(self) -> NeStr:
        raise NotImplementedError

    @property
    @abstractmethod
    def vocab(self) -> NeList[str]:
        raise NotImplementedError

    @abstractmethod
    @beartype
    def calc_logits(self, audio: NumpyFloat1DArray) -> TorchTensor2D:
        raise NotImplementedError
