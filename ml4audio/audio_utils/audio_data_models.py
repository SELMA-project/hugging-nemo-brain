from abc import abstractmethod
from dataclasses import dataclass, field, InitVar
from typing import (
    Iterable,
    Iterator,
    Any,
    Union,
    Optional,
    TypeVar,
    Generic,
)

from beartype.door import die_if_unbearable

from misc_utils.beartypes import (
    NeNpFloatDim1,
    NeStr,
    NumpyInt16Dim1,
)
from misc_utils.buildable import Buildable
from misc_utils.dataclass_utils import FillUndefined, _UNDEFINED, UNDEFINED
from misc_utils.prefix_suffix import PrefixSuffix, BASE_PATHES
from misc_utils.utils import Singleton
from ml4audio.audio_utils.audio_segmentation_utils import StartEnd

ArrayText = tuple[NeNpFloatDim1, NeStr]


IdArray = tuple[NeStr, NeNpFloatDim1]
IdArrayText = tuple[NeStr, NeNpFloatDim1, NeStr]
IdInt16Array = tuple[NeStr, NumpyInt16Dim1]

IdText = tuple[NeStr, NeStr]


@dataclass
class FileLikeAudioDatum:
    id: str
    audio_source: Any  # BytesIO, ExFileObject
    format: str


@dataclass
class AudioFile(FileLikeAudioDatum):
    # TODO: where is this used?

    format: Optional[str] = field(init=False, repr=False)

    def __post_init__(self):
        self.format = self.audio_source.split(".")[-1]


@dataclass
class TranscriptAnnotation:
    segment_id: str  # rename to utterance_id ?
    text: str


@dataclass
class _UNKNOWN_START_END(metaclass=Singleton):
    pass


UNKNOWN_START_END = _UNKNOWN_START_END()


@dataclass
class AlignmentSpan:
    start_a: Union[int, float, _UNKNOWN_START_END]
    end_a: Union[int, float, _UNKNOWN_START_END]
    start_b: Union[int, float, _UNKNOWN_START_END]
    end_b: Union[int, float, _UNKNOWN_START_END]


@dataclass
class AlignmentSpanAnnotation(AlignmentSpan):
    confidence: float


# @dataclass # TODO: removeme
# class StandAloneAlignmentSpanAnnotation(AlignmentSpanAnnotation):
#     id_seq_a: str
#     id_seq_b: str


@dataclass
class SegmentAnnotation:
    # TODO: remove this, use AudioSegment
    id: str
    audio_id: str  # this should actually be a parent_id! cause we can also sub-segment segments!
    start: float = 0.0  # in sec
    end: Optional[float] = None  # TODO!!!

    @property
    def duration(self) -> Optional[float]:
        """
        in seconds
        """
        if self.end is not None:
            return self.end - self.start
        else:
            return None


Seconds = float
AudioSourceId = NeStr
SegmentId = NeStr

Id = NeStr


@dataclass
class StartEndSegment:

    parent_id: SegmentId = UNDEFINED
    id_suffix: Optional[NeStr] = None

    start: Optional[Seconds] = None  # should be absolut!
    end: Optional[Seconds] = None

    def __post_init__(self):
        if self.start is not None and self.end is not None:
            die_if_unbearable((self.start, self.end), StartEnd)

    @property
    def id(self) -> SegmentId:
        suffix = self.id_suffix
        return f"{self.parent_id}-{suffix}" if suffix else self.parent_id


@dataclass  # TODO: make frozen?
class AudioFileSegment(Buildable, StartEndSegment):
    """
    it really needs to keep two references:
     * one to the (parent)-segment that is getting segmented
     * one to the audio_source
    start,end should always be "absolut", there is no offset!

    being Buildable just because of PrefixSuffix!
    """

    audio_file: PrefixSuffix = UNDEFINED


@dataclass
class GotAudioSegments:
    audio_segments: Optional[Iterable[AudioFileSegment]] = field(
        init=False, default=None
    )

    @staticmethod
    def from_obj(audio_segments: Iterable[AudioFileSegment]):
        o = GotAudioSegments()
        o.audio_segments = audio_segments
        return o


@dataclass
class GotTranscripts:
    transcripts: Iterable[TranscriptAnnotation] = field(init=False, default=None)

    @classmethod
    def from_obj(cls, obj: Iterable[TranscriptAnnotation]):
        o = cls()
        o.transcripts = obj
        return o


@dataclass
class GotOverallDuration:
    overall_duration: float


@dataclass
class GotSegmentsTranscripts(GotAudioSegments, GotTranscripts):
    """
    SegTra==SegmentsTranscripts
    """

    pass


@dataclass
class AudioFileCorpus(Iterable[AudioFile], FillUndefined):
    id: Union[_UNDEFINED, NeStr] = UNDEFINED

    @abstractmethod
    def __iter__(self) -> Iterator[AudioFile]:
        raise NotImplementedError


@dataclass
class SegmentCorpus(Iterable[SegmentAnnotation], FillUndefined):
    id: Union[_UNDEFINED, NeStr] = UNDEFINED
    audiocorpus_id: Union[_UNDEFINED, NeStr] = UNDEFINED

    @abstractmethod
    def __iter__(self) -> Iterator[SegmentAnnotation]:
        raise NotImplementedError


@dataclass
class TranscriptCorpus(Iterable[TranscriptAnnotation], FillUndefined):
    """
    this serves as Interface
    id: ... of this Corpus of Annotations (here Transcripts)
    segmentcorpus_id: ... of what is being annotated
    """

    id: Union[_UNDEFINED, NeStr] = UNDEFINED
    segmentcorpus_id: Union[_UNDEFINED, NeStr] = UNDEFINED

    def __post_init__(self):
        assert self.id != self.segmentcorpus_id, f"you cannot annotate yourself!"

    @abstractmethod
    def __iter__(self) -> Iterator[TranscriptAnnotation]:
        raise NotImplementedError


@dataclass
class AudioData(Iterable[IdArray], FillUndefined):
    # TODO: remove!
    sample_rate: int = UNDEFINED

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @abstractmethod
    def __iter__(self) -> Iterator[IdArray]:
        raise NotImplementedError


@dataclass
class AudioTextData(Iterable[ArrayText]):
    """
    naming: Auteda == Audio Text Data
    """

    sample_rate: int = UNDEFINED

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __iter__(self) -> Iterator[ArrayText]:
        raise NotImplementedError


@dataclass
class IdAudioTextData(Iterable[IdArrayText]):
    """
    naming: Auteda == Audio Text Data
    """

    sample_rate: int = UNDEFINED

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __iter__(self) -> Iterator[IdArrayText]:
        raise NotImplementedError


@dataclass
class FileLikeAudioCorpus(Iterable[FileLikeAudioDatum], FillUndefined):
    # TODO: why is this not buildable?
    id: Union[_UNDEFINED, NeStr] = UNDEFINED

    @abstractmethod
    def __iter__(self) -> Iterator[FileLikeAudioDatum]:
        raise NotImplementedError


TIn = TypeVar("Input")
TOut = TypeVar("Output")


@dataclass
class IterableInferencer(Buildable, Generic[TIn, TOut]):
    @abstractmethod
    def infer(self, inputs: Iterable[TIn]) -> Iterator[TOut]:
        raise NotImplemented
