from dataclasses import dataclass
from enum import Enum, auto
from typing import Union, Optional, Annotated

import regex
from beartype import beartype
from beartype.vale import Is

from misc_utils.beartypes import NeList
from misc_utils.dataclass_utils import (
    UNDEFINED,
)
from ml4audio.text_processing.character_mappings.text_cleaning import (
    TextCleaner,
    CHARACTER_MAPPINGS,
    TEXT_CLEANERS,
)

# TODO: validate mappings?
# name: str
# character_mapping: dict[str, str]
#
#
# @validator("character_mapping")
# def character_mapping_key_len_one(cls, mapping: dict[str, str]):
#     bad_keys = [k for k in mapping.keys() if len(k) != 1]
#     if not all(bad_keys):
#         raise ValueError(f"{bad_keys} do not have len of 1!")
#     return mapping

SILENCE_SYMBOL = "|"
# PUNCTUATION.replace(SILENCE_SYMBOL, "") # how to handle explicit silence? with space or silence-symbol?


class Casing(str, Enum):
    lower = auto()
    upper = auto()
    original = auto()

    def _to_dict(self, skip_keys: Optional[list[str]] = None) -> dict:
        obj = self
        module = obj.__class__.__module__
        _target_ = f"{module}.{obj.__class__.__name__}"
        # TODO: WTF? why _target_ and _id_ stuff here?
        d = {"_target_": _target_, "value": self.value, "_id_": str(id(self))}
        skip_keys = skip_keys if skip_keys is not None else []
        return {k: v for k, v in d.items() if k not in skip_keys}

    def apply(self, s: str) -> str:
        if self is Casing.upper:
            return s.upper()
        elif self is Casing.lower:
            return s.lower()
        elif self is Casing.original:
            return s
        else:
            raise AssertionError("unknown Casing")

    @staticmethod
    def create(value: Union[str, int]):
        """
        # TODO: this is only necessary if someone else mis-interprets "1" as an integer! pythons json lib does it correctly -> somewhere in jina??
        """
        return Casing(str(value))


Letters = Annotated[
    NeList[str], Is[lambda letters: all((len(l) == 1) for l in letters)]
]


@beartype
def clean_and_filter_text(
    text: str,
    vocab_letters: Letters,
    text_cleaner: Union[str, TextCleaner],
    casing: Casing,
) -> str:
    if isinstance(text_cleaner, str):
        text_cleaner = TEXT_CLEANERS[text_cleaner]
    text = clean_upper_lower_text(text, text_cleaner, casing)
    text = regex.sub("\s+", " ", text)
    return filter_by_lettervocab(text, vocab_letters)


@beartype
def clean_upper_lower_text(
    text, text_cleaner: TextCleaner, casing: Casing = Casing.original
):
    text = text_cleaner(text).strip(" ")
    text = casing.apply(text)
    return text


@beartype
def upper_lower_text(text, casing: Casing = Casing.original):
    # first upper than check if in vocab actually makes sense for ß, cause "ß".upper()==SS
    text = casing.apply(text)
    return text


@beartype
def filter_by_lettervocab(text: str, vocab_letters: list[str]) -> str:
    return "".join([c for c in text if c in vocab_letters or c == " "]).strip(" ")


# @beartype
# def casing_vocab_filtering(
#     text: str, vocab_letters: list[str], casing: Casing = Casing.original
# ) -> str:
#     return filter_by_lettervocab(casing.apply(text), vocab_letters)


@dataclass
class VocabCasingAwareTextCleaner(TextCleaner):

    casing: Union[str, Casing] = UNDEFINED
    text_cleaner_name: str = UNDEFINED
    letter_vocab: Letters = UNDEFINED

    def __post_init__(self):
        if isinstance(self.casing, str):
            self.casing = Casing(self.casing)

    def __call__(self, text: str) -> str:
        return clean_and_filter_text(
            text, self.letter_vocab, TEXT_CLEANERS[self.text_cleaner_name], self.casing
        )


# if __name__ == "__main__":
#     # processor = Wav2Vec2Processor.from_pretrained("jonatasgrosman/wav2vec2-large-xlsr-53-spanish")
#     # target_dictionary = list(processor.tokenizer.get_vocab().keys())
#     # print(target_dictionary)
#     # ['<pad>', '<s>', '</s>', '<unk>', '|', "'", '-', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'Á', 'É', 'Í', 'Ñ', 'Ó', 'Ö', 'Ú', 'Ü']
#     samesame_but_different = {
#         "ä": "ä",
#         "ü": "ü",
#         "ö": "ö",
#         "Ä": "Ä",
#         "Ü": "Ü",
#         "Ö": "Ö",
#     }
#     print(
#         [
#             (k.encode("utf-8"), v.encode("utf-8"))
#             for k, v in samesame_but_different.items()
#         ]
#     )
#     print("Ö".lower().encode("utf8"))


if __name__ == "__main__":
    s = "Jon-Do–e's"
    print(s)
    print(CHARACTER_MAPPINGS["de"](s))
